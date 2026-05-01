from __future__ import annotations
from pathlib import Path
from datetime import date as date_type, datetime, timedelta, timezone
import csv
import json
import os
import typer
import asyncio
from logger import setup_logger
from config import load_config

app = typer.Typer(help="GA4 Synthetic Data Generator CLI")


def _output_dir() -> Path:
    path = Path("output")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_summary(summary: dict, stamp: str) -> Path:
    path = _output_dir() / f"run_summary_{stamp}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _write_events_csv(rows: list[dict], stamp: str) -> Path:
    path = _output_dir() / f"events_{stamp}.csv"
    fieldnames = ["client_id", "session_id", "event_name", "timestamp_micros", "event_date", "traffic_source", "device_category", "geo_country", "transaction_id", "revenue", "items"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # serialize items as JSON if present
            out = {key: row.get(key, "") for key in fieldnames}
            if "items" in row and row.get("items"):
                try:
                    out["items"] = json.dumps(row.get("items"), ensure_ascii=False)
                except Exception:
                    out["items"] = str(row.get("items"))
            writer.writerow(out)
    return path


def _resolve_target_date(date_value: str | None) -> date_type:
    if date_value:
        return datetime.fromisoformat(date_value).date()
    return datetime.utcnow().date()


@app.command()
def validate_config(config: str = "config.yaml"):
    """Validate config.yaml and required environment variables."""
    logger = setup_logger()
    try:
        cfg = load_config(config)
    except Exception as e:
        logger.error("Config validation failed: {}", e)
        raise typer.Exit(code=1)

    logger.info("Config loaded successfully")
    logger.info("Measurement ID: {}", cfg.env.measurement_id)
    logger.info("Dry-run setting: {}", cfg.raw.get("sending", {}).get("dry_run", False))


@app.command()
def preview(count: int = 3):
    """Print a small preview of generated user journeys (stub)."""
    logger = setup_logger()
    logger.info("Previewing {} synthetic user journeys", count)
    # load config if available (non-fatal)
    try:
        cfg = load_config()
    except Exception:
        cfg = None

    from generator.products import build_catalog
    from payload.builder import build_event_payload, make_page_view_event
    import random

    catalog = build_catalog(cfg.raw if cfg else None, seed=42, n=20)

    for i in range(count):
        client_id = f"{random.randint(1000000000,9999999999)}.{random.randint(1000000000,9999999999)}"
        sample_product = catalog[i % len(catalog)]
        params = {
            "session_id": int(random.randint(1_700_000_000, 1_700_100_000)),
            "session_number": 1,
            "engagement_time_msec": 1200,
            "language": "de-de",
            "screen_resolution": "390x844",
            "page_location": f"https://demoshop.example.com/product/{sample_product['item_id']}",
            "page_title": sample_product["item_name"],
        }
        ev = make_page_view_event(params)
        payload = build_event_payload(client_id=client_id, events=[ev])
        print(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command()
def daily(date: str | None = None, dry_run: bool = True):
    """Generate & send a single day's synthetic traffic (stub)."""
    logger = setup_logger()
    target_date = _resolve_target_date(date)
    logger.info("Starting daily run for date={} dry_run={}", str(target_date), dry_run)
    try:
        cfg = load_config()
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        raise typer.Exit(code=1)

    from generator.products import build_catalog
    from generator.population import generate_users
    from generator.session import make_session_for_user
    from generator.journey import build_simple_journey
    from payload.builder import build_event_payload
    from sender.mp_client import MPClient
    import asyncio
    import random

    catalog = build_catalog(cfg.raw, seed=123, n=50)

    # sample user count (simple gaussian clipped)
    mean = cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_mean", 85)
    std = cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_std", 18)
    users_n = int(max(cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_min", 40), min(cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_max", 160), int(random.gauss(mean, std)))))

    users = generate_users(users_n, cfg.raw, seed=456)

    async def run_send():
        client = MPClient(cfg.env.measurement_id, cfg.env.api_secret, rps=cfg.raw.get("sending", {}).get("requests_per_second", 5), use_debug=cfg.raw.get("sending", {}).get("use_debug_endpoint", False))
        sent = 0
        rows: list[dict] = []
        payloads: list[dict] = []
        for i, u in enumerate(users):
            sess = make_session_for_user(1, seed=hash(u.client_id) % 100000)
            events = build_simple_journey(sess, catalog, cfg.raw, seed=hash(u.client_id) % 100000 + i)
            if not events:
                continue
            evs = []
            for e in events:
                evs.append({"name": e.name, "params": e.params})
            payload = build_event_payload(client_id=u.client_id, user_id=u.user_id, events=evs, timestamp_micros=events[0].timestamp_micros)
            payloads.append(payload)
            for e in events:
                # derive traffic source string from user's acquisition_source if available
                tsrc = ""
                if getattr(u, "acquisition_source", None):
                    ac = u.acquisition_source
                    tsrc = f"{ac.medium} / {ac.source}"
                    if ac.campaign:
                        tsrc = f"{tsrc} (campaign: {ac.campaign})"
                else:
                    tsrc = "organic / google"

                rows.append({
                    "client_id": u.client_id,
                    "session_id": sess.session_id,
                    "event_name": e.name,
                    "timestamp_micros": e.timestamp_micros,
                    "event_date": target_date.isoformat(),
                    "traffic_source": tsrc,
                    "device_category": u.device.category,
                    "geo_country": u.geo.country_code,
                    "transaction_id": e.params.get("transaction_id", ""),
                    "revenue": e.params.get("value", 0),
                    "items": e.params.get("items", []),
                })
            if dry_run or cfg.raw.get("sending", {}).get("dry_run", True):
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                resp = await client.send(payload)
                print(f"sent: {resp.status_code}")
            sent += 1
        await client.close()
        stamp = _run_stamp()
        summary = {
            "run_id": stamp,
            "mode": "daily",
            "date": target_date.isoformat(),
            "stats": {
                "users_generated": len(users),
                "events_sent": sum(len(p.get("events", [])) for p in payloads),
                "payloads": sent,
            },
        }
        _write_summary(summary, stamp)
        _write_events_csv(rows, stamp)
        logger.info("Completed sending {} payloads (sample)", sent)

    asyncio.run(run_send())


@app.command()
def historical(start: str | None = None, end: str | None = None, dry_run: bool = True):
    """Backfill historical range (stub)."""
    logger = setup_logger()
    try:
        cfg = load_config()
    except Exception as e:
        logger.error("Failed to load config: {}", e)
        raise typer.Exit(code=1)

    start_date = datetime.fromisoformat(start or cfg.raw.get("simulation", {}).get("historical", {}).get("start", "2025-01-01")).date()
    end_date = datetime.fromisoformat(end or cfg.raw.get("simulation", {}).get("historical", {}).get("end", "2025-01-01")).date()
    logger.info("Starting historical run start={} end={} dry_run={}", str(start_date), str(end_date), dry_run)

    from generator.products import build_catalog
    from generator.population import generate_users
    from generator.session import make_session_for_user
    from generator.journey import build_simple_journey
    from payload.builder import build_event_payload
    from sender.mp_client import MPClient
    import random

    catalog = build_catalog(cfg.raw, seed=123, n=50)
    rows: list[dict] = []
    stamp = _run_stamp()
    async def run_send():
        client = MPClient(cfg.env.measurement_id, cfg.env.api_secret, rps=cfg.raw.get("sending", {}).get("requests_per_second", 5), use_debug=cfg.raw.get("sending", {}).get("use_debug_endpoint", False))
        sent = 0
        current = start_date
        while current <= end_date:
            mean = cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_mean", 85)
            std = cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_std", 18)
            users_n = int(max(cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_min", 40), min(cfg.raw.get("simulation", {}).get("daily", {}).get("users_per_day_max", 160), int(random.gauss(mean, std)))))
            users = generate_users(users_n, cfg.raw, seed=int(current.strftime("%Y%m%d")))
            for i, u in enumerate(users):
                sess = make_session_for_user(1, base_ts_s=int(datetime.combine(current, datetime.min.time()).timestamp()), seed=hash(u.client_id) % 100000)
                events = build_simple_journey(sess, catalog, cfg.raw, seed=hash(u.client_id) % 100000 + i)
                if not events:
                    continue
                payload = build_event_payload(client_id=u.client_id, user_id=u.user_id, events=[{"name": e.name, "params": e.params} for e in events], timestamp_micros=events[0].timestamp_micros)
                if dry_run or cfg.raw.get("sending", {}).get("dry_run", True):
                    pass
                else:
                    await client.send(payload)
                for e in events:
                    rows.append({
                        "client_id": u.client_id,
                        "session_id": sess.session_id,
                        "event_name": e.name,
                        "timestamp_micros": e.timestamp_micros,
                        "event_date": current.isoformat(),
                        "traffic_source": "organic / google",
                        "device_category": u.device.category,
                        "geo_country": u.geo.country_code,
                        "transaction_id": e.params.get("transaction_id", ""),
                        "revenue": e.params.get("value", 0),
                    })
                sent += 1
            current += timedelta(days=1)
        await client.close()
        _write_summary({"run_id": stamp, "mode": "historical", "range": [start_date.isoformat(), end_date.isoformat()], "stats": {"payloads": sent, "events": len(rows)}}, stamp)
        _write_events_csv(rows, stamp)
        logger.info("Completed historical generation: {} payloads", sent)

    asyncio.run(run_send())


def main():
    app()


if __name__ == "__main__":
    main()
