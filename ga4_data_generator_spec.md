# GA4 Synthetic Data Generator — Technical Specification

## 1. Project Overview

A Python CLI program that generates realistic synthetic ecommerce user journeys and sends
them to a GA4 property via the Measurement Protocol. The output is used to populate a
demo GA4 property and its linked BigQuery export with analysis-ready data for tutorials.

**Goals:**
- Produce data that looks realistic in both the GA4 UI and BigQuery
- Cover the full ecommerce event funnel with correct parameter schemas
- Populate all BQ schema fields that GA4 UI tutorials and BQ queries depend on
- Be fully configurable so the dataset can be regenerated or extended

**Two run modes:**
- `daily` — triggered by GitHub Actions on a cron schedule; generates one day's worth of
  traffic for today with randomised volume, then sends it (timestamps are always within
  the 72h MP window)
- `historical` — one-time backfill run that generates a full date range; used to seed
  the property from scratch (note: events beyond 72h will not appear in GA4 UI reports
  but land correctly in BQ with accurate `event_timestamp` values)

---

## 2. Tech Stack

- **Language:** Python 3.11+
- **HTTP client:** `httpx` (async, with rate limiting)
- **Data generation:** `faker`, `random`, `numpy` (for distributions)
- **Config:** `.env` file via `python-dotenv` + a `config.yaml` for simulation parameters
- **Logging:** `loguru` — structured logs with per-batch success/failure counts
- **CLI:** `typer`

---

## 3. Configuration

### 3.1 `.env` (secrets, never committed)

```
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=xxxxxxxxxxxxxxxxxxxx
```

### 3.2 `config.yaml` (simulation parameters)

```yaml
simulation:
  currency: "EUR"
  new_to_returning_ratio: 0.75   # 75% new users, 25% returning

  # --- Daily mode (used by GitHub Actions cron) ---
  daily:
    # User count per day is drawn from a normal distribution truncated to [min, max].
    # This ensures every run has naturally different traffic volume.
    users_per_day_mean: 85
    users_per_day_std: 18
    users_per_day_min: 40
    users_per_day_max: 160
    # Weekday multiplier applied after sampling (Mon=0 to Sun=6).
    # Encodes the pattern: weekdays busier than weekends.
    weekday_multipliers: [1.10, 1.15, 1.10, 1.05, 1.00, 0.80, 0.70]

  # --- Historical mode (one-time backfill) ---
  historical:
    start: "2025-01-01"
    end: "2025-03-31"
    # Each calendar day is simulated independently using the daily distribution above

store:
  name: "DemoShop"
  categories:
    - name: "Electronics"
      weight: 0.35
      price_range: [29.99, 499.99]
    - name: "Clothing"
      weight: 0.30
      price_range: [9.99, 149.99]
    - name: "Home & Living"
      weight: 0.20
      price_range: [14.99, 299.99]
    - name: "Books"
      weight: 0.15
      price_range: [7.99, 39.99]

funnel:
  page_view_to_view_item: 0.55
  view_item_to_add_to_cart: 0.28
  add_to_cart_to_begin_checkout: 0.55
  begin_checkout_to_purchase: 0.60
  # Implied overall CVR: ~5%

  # Secondary behaviours
  view_item_list_probability: 0.65   # chance user sees a list page before view_item
  search_probability: 0.30           # chance user performs a search
  multi_item_basket_probability: 0.25  # chance basket has >1 item
  refund_rate: 0.02                   # % of purchases that get a refund event

traffic_sources:
  - medium: organic
    source: google
    weight: 0.35
  - medium: organic
    source: bing
    weight: 0.05
  - medium: cpc
    source: google
    campaign: "brand_search"
    weight: 0.15
  - medium: cpc
    source: google
    campaign: "category_shopping"
    weight: 0.10
  - medium: email
    source: newsletter
    campaign: "weekly_digest"
    weight: 0.10
  - medium: social
    source: instagram
    weight: 0.08
  - medium: social
    source: facebook
    weight: 0.07
  - medium: "(none)"
    source: "(direct)"
    weight: 0.10

device_mix:
  - category: mobile
    os: Android
    browser: Chrome
    weight: 0.38
  - category: mobile
    os: iOS
    browser: Safari
    weight: 0.25
  - category: desktop
    os: Windows
    browser: Chrome
    weight: 0.20
  - category: desktop
    os: macOS
    browser: Safari
    weight: 0.10
  - category: desktop
    os: Windows
    browser: Edge
    weight: 0.04
  - category: tablet
    os: iOS
    browser: Safari
    weight: 0.03

geo_mix:
  - country: Germany
    country_code: DE
    regions: [Berlin, Bavaria, Hamburg, North Rhine-Westphalia, Baden-Württemberg]
    weight: 0.55
  - country: Austria
    country_code: AT
    regions: [Vienna, Styria, Upper Austria]
    weight: 0.20
  - country: Switzerland
    country_code: CH
    regions: [Zurich, Geneva, Bern]
    weight: 0.15
  - country: Netherlands
    country_code: NL
    regions: [North Holland, South Holland, Utrecht]
    weight: 0.10

sending:
  batch_size: 20          # events per HTTP request (MP supports up to 25)
  requests_per_second: 5  # rate limit to avoid 429s
  dry_run: false          # if true, validate payloads but do not send
  use_debug_endpoint: false  # if true, sends to /debug/mp/collect instead
```

---

## 4. Architecture

```
main.py  (CLI entry point via typer)
│
├── generator/
│   ├── population.py     # generates User objects
│   ├── session.py        # generates Session objects for a user
│   ├── journey.py        # probabilistic funnel walk, returns ordered Event list
│   └── products.py       # product catalogue and item param builder
│
├── payload/
│   ├── builder.py        # assembles MP-compliant JSON payloads
│   └── schemas.py        # TypedDicts for each event type
│
├── sender/
│   └── mp_client.py      # async httpx client, batching, rate limiting, retries
│
├── config.py             # loads .env + config.yaml, exposes typed Config object
└── logger.py             # loguru setup
```

---

## 5. Data Model

### 5.1 User

Generated once per synthetic user. Attributes are assigned at creation and held constant
across all their sessions.

```python
@dataclass
class User:
    client_id: str          # format: "XXXXXXXXXX.XXXXXXXXXX" (10digit.10digit) — mirrors _ga cookie format
    user_id: str | None     # assigned to ~60% of users (logged-in), format: "user_XXXXX"
    device: DeviceProfile
    geo: GeoProfile
    language: str           # e.g. "de-de", "en-gb" — derived from geo
    is_returning: bool
    total_sessions: int     # 1 for new, 2-6 for returning (right-skewed distribution)
    acquisition_source: TrafficSource  # the *first* session source; subsequent may vary
```

### 5.2 Session

One user can have multiple sessions. Sessions are spaced realistically across the date range.

```python
@dataclass
class Session:
    session_id: int         # Unix timestamp (seconds) of session start
    session_number: int     # 1-indexed, increments per user
    start_timestamp_us: int # microseconds, used as base for event timestamps
    traffic_source: TrafficSource  # may differ from acquisition for returning users
    engagement_time_msec: int  # total session engagement time; distribute across events
    events: list[Event]
```

**Session timing rules:**
- Sessions for a user are spaced at least 30 minutes apart
- Gap between sessions for returning users: right-skewed, median ~7 days, max ~60 days
- Session start times follow an intraday distribution: peak at 09:00–11:00 and 19:00–22:00 local time, trough at 02:00–06:00
- Day-of-week: weekdays slightly higher than weekends

### 5.3 Event

```python
@dataclass
class Event:
    name: str
    timestamp_micros: int   # absolute microsecond timestamp
    params: dict            # event-specific params per MP schema
    engagement_time_msec: int  # portion of session engagement allocated to this event
```

**Timestamp construction:**
- Events within a session are spaced 5–120 seconds apart (uniform random)
- `timestamp_micros` = session `start_timestamp_us` + cumulative offset per event
- The MP `timestamp_micros` field will be set on each event; do not rely on server receipt time

**Timestamp and 72h window:**
- In `daily` mode, all events are timestamped to today → always within the 72h MP window
  → appear correctly in GA4 realtime and standard reports
- In `historical` mode, the generator sends each day's events immediately after generating
  them. Since historical dates are in the past, their `timestamp_micros` will be outside
  the 72h window. GA4 will still ingest the events and BQ will record the correct
  `event_timestamp`, but they will not appear in GA4 UI date-filtered reports. This is
  acceptable for the primary use case (BQ-based tutorial analysis). Document this clearly
  in the README.

---

## 6. Product Catalogue

Generate a static catalogue of ~80 products at startup (seeded for reproducibility).

```python
@dataclass
class Product:
    item_id: str            # "PROD-XXXX"
    item_name: str          # realistic product name
    item_category: str      # top-level category from config
    item_category2: str     # sub-category (e.g. "Smartphones" under "Electronics")
    item_brand: str         # plausible brand name
    price: float            # from category price range in config
    item_variant: str | None  # e.g. "Blue / XL" for clothing
    item_list_name: str     # e.g. "Electronics - Bestsellers"
    item_list_id: str       # e.g. "cat_electronics"
```

---

## 7. Event Taxonomy

All events must use exact GA4 recommended event names and parameter schemas.
Reference: https://developers.google.com/analytics/devguides/collection/protocol/ga4/reference/events

### 7.1 Required on every event (top-level payload fields)

```json
{
  "client_id": "...",
  "user_id": "...",          // omit if null
  "timestamp_micros": 0,
  "user_properties": {
    "user_type": { "value": "new_user" | "returning_user" }
  },
  "events": [
    {
      "name": "...",
      "params": {
        "session_id": "...",
        "session_number": 1,
        "engagement_time_msec": 0,
        "language": "de-de",
        "screen_resolution": "...",   // e.g. "390x844"
        "page_location": "https://demoshop.example.com/...",
        "page_title": "...",
        ...event-specific params
      }
    }
  ]
}
```

### 7.2 Geo override (include on first event of each session)

```json
"geo": {
  "country": "DE",
  "region": "Berlin",
  "city": "Berlin"
}
```

### 7.3 Device info override (include on first event of each session)

```json
"device": {
  "category": "mobile",
  "mobile_brand_name": "Samsung",
  "mobile_model_name": "Galaxy S23",
  "operating_system": "Android",
  "operating_system_version": "14",
  "language": "de-de",
  "browser": "Chrome",
  "browser_version": "120.0.0"
}
```

### 7.4 Event sequence per session

A complete possible journey (not all events fire for every session — see funnel rates in config):

| Step | Event Name | Always? |
|------|-----------|---------|
| 1 | `page_view` (homepage) | Yes |
| 2 | `view_item_list` | 65% of sessions |
| 3 | `select_item` | If view_item_list fired |
| 4 | `view_item` | 55% of page_view sessions |
| 5 | `add_to_cart` | 28% of view_item sessions |
| 6 | `view_cart` | If add_to_cart fired |
| 7 | `begin_checkout` | 55% of add_to_cart sessions |
| 8 | `add_payment_info` | 80% of begin_checkout sessions |
| 9 | `add_shipping_info` | 80% of begin_checkout sessions (order with payment varies) |
| 10 | `purchase` | 60% of begin_checkout sessions |
| 11 | `refund` | 2% of purchase events (separate session, later date) |

Additional non-funnel events:
- `search` — 30% of sessions; params: `search_term` (pick from a realistic list of ~30 terms)
- `page_view` — fired for each distinct page in the session (homepage, category, PDP, cart, checkout, confirmation)

### 7.5 Key ecommerce event param schemas

**`view_item_list`**
```json
{
  "item_list_id": "cat_electronics",
  "item_list_name": "Electronics - Bestsellers",
  "items": [ { ...item fields, "index": 1 } ]
}
```

**`view_item`**
```json
{
  "currency": "EUR",
  "value": 99.99,
  "items": [ { ...item fields } ]
}
```

**`add_to_cart`**
```json
{
  "currency": "EUR",
  "value": 99.99,
  "items": [ { ...item fields, "quantity": 1 } ]
}
```

**`begin_checkout`**
```json
{
  "currency": "EUR",
  "value": 99.99,
  "coupon": "SAVE10",   // present on ~15% of checkouts
  "items": [ { ...item fields, "quantity": 1 } ]
}
```

**`purchase`**
```json
{
  "transaction_id": "TXN-XXXXXXXXXX",  // unique, never reused
  "value": 89.99,
  "tax": 14.36,
  "shipping": 4.99,
  "currency": "EUR",
  "coupon": "SAVE10",   // if applied at checkout
  "items": [ { ...item fields, "quantity": 1, "discount": 10.00 } ]
}
```

**`refund`**
```json
{
  "transaction_id": "TXN-XXXXXXXXXX",  // must match original purchase
  "value": 89.99,
  "currency": "EUR",
  "items": [ { ...item fields } ]  // partial refunds allowed (subset of items)
}
```

**Standard item fields (used in all ecommerce events):**
```json
{
  "item_id": "PROD-0042",
  "item_name": "Wireless Headphones Pro",
  "item_brand": "AudioMax",
  "item_category": "Electronics",
  "item_category2": "Audio",
  "item_variant": null,
  "price": 99.99,
  "quantity": 1,
  "index": 1,
  "item_list_id": "cat_electronics",
  "item_list_name": "Electronics - Bestsellers",
  "discount": 0.00
}
```

### 7.6 Traffic source params (on first event of session)

Pass as event params — these map to `traffic_source` columns in BQ:

```json
{
  "campaign_source": "google",
  "campaign_medium": "cpc",
  "campaign_name": "brand_search",
  "campaign_content": null,
  "campaign_term": null
}
```

For direct/none sessions, omit these entirely (do not pass empty strings).

---

## 8. Measurement Protocol Sending

### 8.1 Endpoint

```
POST https://www.google-analytics.com/mp/collect
  ?measurement_id=G-XXXXXXXXXX
  &api_secret=xxxxxxxxxxxxxxxxxxxx
```

Debug/validation endpoint (when `use_debug_endpoint: true`):
```
POST https://www.google-analytics.com/debug/mp/collect
  ?measurement_id=...&api_secret=...
```

### 8.2 Batching

- MP accepts up to **25 events per request**
- Each request body: `{ "client_id": "...", "timestamp_micros": ..., "events": [...] }`
- Group events by `client_id` when batching — do not mix multiple users in one request
- If a user session has more than 25 events, split across multiple requests

### 8.3 Rate limiting and retries

- Default: 5 requests/second (configurable)
- On HTTP 429 or 503: exponential backoff, max 3 retries
- Log final failures but do not crash — continue with remaining users

### 8.4 Dry run mode

When `dry_run: true`:
- Build all payloads as normal
- Print a sample of 5 payloads to stdout as formatted JSON
- Send to the **validation endpoint** (`/debug/mp/collect`) and log the response
- Do not send to the live endpoint

---

## 9. CLI Interface

```
# Daily mode — generates today's traffic (used by GitHub Actions)
python main.py daily
python main.py daily --dry-run
python main.py daily --date 2025-04-30   # override date (for testing yesterday)

# Historical mode — one-time backfill
python main.py historical
python main.py historical --start 2025-01-01 --end 2025-03-31
python main.py historical --dry-run

# Utilities
python main.py validate-config   # checks config.yaml + .env, prints resolved values
python main.py preview           # prints 3 sample user journeys as JSON without sending
```

In `daily` mode the `--date` flag defaults to today (UTC). The script derives the weekday
from the date and applies the correct `weekday_multiplier` before sampling user count.

---

## 10. Logging and Output

### Console output (via loguru)

Daily mode:
```
[08:02:11] INFO  Mode: daily | Date: 2025-05-01 (Wednesday)
[08:02:11] INFO  Product catalogue: 80 items across 4 categories
[08:02:11] INFO  Users today: 97 (sampled: 88, weekday multiplier: 1.10x)
[08:02:11] INFO  Sessions: 112 | Events: ~2,240 (estimated)
[08:02:12] INFO  Sending... [████████░░] 74% | 83/112 sessions | 5.0 req/s
[08:02:26] INFO  Complete: 112 sessions sent, 0 failed
[08:02:26] INFO  Purchases: 5 | Revenue: €437.82 | Refunds: 0
```

Historical mode:
```
[12:34:01] INFO  Mode: historical | Range: 2025-01-01 to 2025-03-31 (90 days)
[12:34:01] INFO  Product catalogue: 80 items across 4 categories
[12:34:02] INFO  Day 2025-01-01 (Wednesday): 94 users | 108 sessions
           ...
[12:41:05] INFO  Complete: 7,840 sessions sent, 3 failed
[12:41:05] INFO  Purchases: 412 | Revenue: €38,204.17 | Refunds: 9
```

### Run summary JSON (`output/run_summary_{timestamp}.json`)

```json
{
  "run_id": "2025-05-01T08:02:11",
  "mode": "daily",
  "date": "2025-05-01",
  "config_snapshot": { "..." : "..." },
  "stats": {
    "users_sampled_raw": 88,
    "weekday_multiplier": 1.10,
    "users_generated": 97,
    "sessions_generated": 112,
    "events_sent": 2237,
    "events_failed": 0,
    "purchases": 5,
    "total_revenue": 437.82,
    "refunds": 0,
    "duration_seconds": 15
  }
}
```

### Event log CSV (`output/events_{timestamp}.csv`)

One row per event — useful for verifying distributions and for independent BQ uploads
if needed. Columns: `client_id`, `session_id`, `event_name`, `timestamp_micros`,
`event_date`, `traffic_source`, `device_category`, `geo_country`, `transaction_id`,
`revenue`.

---

## 11. Reproducibility

- Accept an optional `--seed INTEGER` CLI flag
- Pass to `random.seed()` and `numpy.random.seed()` at startup
- Same seed + same config = identical dataset
- Document the default seed in README

---

## 12. Project Structure

```
ga4-synthetic-generator/
├── main.py
├── config.yaml
├── .env.example
├── requirements.txt
├── README.md
├── generator/
│   ├── __init__.py
│   ├── population.py
│   ├── session.py
│   ├── journey.py
│   └── products.py
├── payload/
│   ├── __init__.py
│   ├── builder.py
│   └── schemas.py
├── sender/
│   ├── __init__.py
│   └── mp_client.py
├── config.py
├── logger.py
└── output/               # gitignored
```

---

## 13. GitHub Actions Workflow

File: `.github/workflows/daily_send.yml`

```yaml
name: Daily GA4 Synthetic Data

on:
  schedule:
    - cron: '0 8 * * *'   # 08:00 UTC daily
  workflow_dispatch:        # allow manual trigger from GitHub UI

jobs:
  send:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily send
        env:
          GA4_MEASUREMENT_ID: ${{ secrets.GA4_MEASUREMENT_ID }}
          GA4_API_SECRET: ${{ secrets.GA4_API_SECRET }}
        run: python main.py daily

      - name: Upload run summary
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: run-summary-${{ github.run_id }}
          path: output/run_summary_*.json
          retention-days: 30
```

**Required GitHub secrets** (set under repo Settings → Secrets → Actions):
- `GA4_MEASUREMENT_ID`
- `GA4_API_SECRET`

**Notes:**
- `workflow_dispatch` lets you manually trigger a run from the GitHub Actions UI,
  useful for testing or re-running a missed day with `--date`
- The run summary artifact preserves each day's stats for debugging without needing
  to check GA4 or BQ
- If the job fails, GitHub sends an email notification automatically

---

## 14. Key Constraints and Edge Cases to Handle

- `transaction_id` must be globally unique across the entire run; track in a set
- `session_id` must be unique per user (not globally) — reuse is fine across different users
- Refund events must reference a real `transaction_id` from the same run; generate refunds
  after all purchases are decided, not inline
- `timestamp_micros` must be > 0 and within 72 hours of send time for events to appear
  in GA4 realtime/standard reports; beyond that they still land in BQ correctly
- Do not send `page_view` with ecommerce params — it is a separate event
- `engagement_time_msec` must be a positive integer on every event; distribute the
  session's total engagement time proportionally across events
- `value` in ecommerce events must equal the sum of `(price - discount) * quantity`
  across all items; validate this before sending
- For multi-item baskets, all downstream events (`view_cart`, `begin_checkout`, `purchase`)
  must carry the same item array with consistent quantities
- Never reuse a `client_id` across different users in the same run