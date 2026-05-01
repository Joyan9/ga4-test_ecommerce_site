# GA4 Synthetic Data Generator

This repository now includes a Python 3.11-based synthetic data generator for GA4 Measurement Protocol tutorials. It creates sample ecommerce journeys, builds GA4 payloads, and can preview or send them with a CLI.

## What is implemented

- `main.py`: Typer CLI with `validate-config`, `preview`, `daily`, and `historical`
- `config.py`: loads `.env` secrets and `config.yaml`
- `generator/`: seeded product catalog, user, session, and journey generators
- `payload/`: GA4 payload builder and minimal schemas
- `sender/mp_client.py`: async `httpx` sender with rate limiting and retry/backoff
- `output/`: run summaries and CSV exports created at runtime

## Setup

1. Copy `.env.example` to `.env` and fill in your GA4 credentials.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Validate configuration:

```bash
python main.py validate-config
```

## Commands

```bash
python main.py preview
python main.py daily --dry-run
python main.py daily --date 2025-04-30 --dry-run
python main.py historical --start 2025-01-01 --end 2025-01-03 --dry-run
```

## Notes

- The current implementation is intentionally conservative: it prints sample payloads in dry-run mode and writes summary/CSV artifacts to `output/`.
- Historical mode is meant for backfills. Events with timestamps older than the GA4 72-hour Measurement Protocol window may still land in BigQuery but not standard GA4 UI reports.
- Do not commit `.env` or API secrets.

## Verification

Run the built-in tests with:

```bash
python -m unittest discover -s tests
```
