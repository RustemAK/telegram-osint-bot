# Telegram OSINT Bot

A lightweight, production-ready Telegram bot for **legal open-source intelligence**.
It aggregates public information about IPs, domains, emails, usernames and
companies from official APIs and open sources — **no leaked or stolen databases
are ever used**.

Designed to run comfortably on a constrained VPS (e.g. Oracle Cloud Free Tier:
1 vCPU / 1 GB RAM, Ubuntu 24.04, Python 3.12+).

## Features

- **Auto-detecting search** — send an IP, domain, email, URL, hash, ASN,
  username or company name and the bot figures out what to do.
- **Concurrent multi-source lookups** with a global concurrency limit to
  protect a low-RAM box.
- **In-memory TTL + LRU cache** (no Redis required) for fast, repeat queries.
- **History & favorites** with pagination and one-tap re-run.
- **Export** any report to **JSON** or **PDF**.
- **Per-user settings** (page size, cache opt-out, export format).
- **Role-based admin panel** — user management, blocking, promotion, error log.
- **Rate limiting & anti-flood** throttling.
- **Structured JSON logging** (structlog).
- Clean architecture: `handlers → services → api/sources → repositories → models`.

## OSINT sources

Free/keyless sources work out of the box; others activate automatically when
you supply the matching API key in `.env`.

| Category | Sources |
| --- | --- |
| IP | ip-api, IPInfo, Reverse DNS, RDAP, AbuseIPDB\*, GreyNoise\*, Shodan\*, VirusTotal\*, Censys\* |
| Domain | DNS, RDAP, WHOIS, crt.sh (Certificate Transparency), VirusTotal\*, SecurityTrails\*, Wikipedia |
| Email | Have I Been Pwned\* (own address), GitHub code search\* |
| Username | GitHub, GitLab, Reddit |
| Company | Wikipedia, News\*, Hacker News, GitHub, Reddit |
| Hash / URL | VirusTotal\* |

\* requires an API key (optional).

## Project layout

```
bot/
  api/            # OSINT source clients + shared HTTP client
  config/         # pydantic-settings configuration
  database/       # async engine, session, declarative base
  models/         # SQLAlchemy models (user, query, favorite)
  repositories/   # data-access layer
  services/       # OSINT orchestration + result store
  middlewares/    # DB session, user context, throttling, logging
  filters/        # role-based access control
  keyboards/      # inline keyboards + typed callbacks
  handlers/       # command & callback handlers
  utils/          # cache, validators, formatting, export, logging
  main.py         # entry point
migrations/       # Alembic
deploy/           # systemd unit
tests/            # pytest suite
```

## Quick start

### 1. Prerequisites

- Python 3.12+ (3.13 supported)
- A bot token from [@BotFather](https://t.me/BotFather)

### 2. Install

```bash
git clone <your-repo> osint-bot && cd osint-bot
make install          # creates .venv and installs requirements
cp .env.example .env  # then edit .env
```

### 3. Configure

Edit `.env` and set at least:

```dotenv
BOT_TOKEN=123456:your-token-here
ADMIN_IDS=11111111,22222222      # your Telegram numeric id(s)
```

All API keys are optional — the bot degrades gracefully without them.

### 4. Run

```bash
make run       # python -m bot.main
```

For SQLite (default) the schema is created automatically on first run.

## Deployment (systemd)

```bash
sudo useradd -r -m -d /opt/osint-bot osint
sudo rsync -a --exclude .venv ./ /opt/osint-bot/
sudo -u osint python3 -m venv /opt/osint-bot/.venv
sudo -u osint /opt/osint-bot/.venv/bin/pip install -r /opt/osint-bot/requirements.txt
sudo cp deploy/osint-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now osint-bot
sudo systemctl status osint-bot
journalctl -u osint-bot -f      # follow logs
```

The unit is hardened and capped at `MemoryMax=400M` / `CPUQuota=80%` for a 1 GB box.

## PostgreSQL (optional)

Switch the database by setting `DATABASE_URL` in `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/osint
```

Then run migrations:

```bash
make migrate                     # alembic upgrade head
# or create a new revision after model changes:
make revision m="add table"
```

## Commands

| Command | Description |
| --- | --- |
| `/start` | Main menu |
| `/search <value>` | Auto-detect & investigate |
| `/ip <address>` | Investigate an IP |
| `/domain <domain>` | Investigate a domain |
| `/email <email>` | Breach check (own address) |
| `/company <name>` | Company / org lookup |
| `/history` | Recent queries (paginated) |
| `/favorite` | Saved queries |
| `/settings` | Preferences |
| `/profile` | Your profile |
| `/stats` | Global statistics |
| `/admin` | Admin panel (admins only) |

## Testing

```bash
make test      # pytest
```

## Legal & ethical use

This tool queries only **public, legal** data sources and official APIs. It does
**not** access leaked credential dumps or any illegally obtained data. The email
breach check is intended for checking **your own** addresses. You are responsible
for complying with the terms of service of each data source and with all
applicable laws in your jurisdiction.
