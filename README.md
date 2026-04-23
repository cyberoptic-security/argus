# Argus

Subdomain and attack surface discovery platform. Runs passive enumeration against multiple OSINT sources and active DNS brute force in parallel, storing results in PostgreSQL with a Next.js frontend.

## Requirements

- Docker & Docker Compose

## Quick Start

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and any API keys you want
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Sources

**Free (no key required):** crt.sh, HackerTarget, AlienVault OTX, BufferOver TLS, AnubisDB, ThreatCrowd, urlscan.io

**Requires API key:** VirusTotal, Shodan, Censys (ID + secret), SecurityTrails, Chaos, Netlas, LeakIX, FullHunt

Add API keys via the Configuration page in the UI.

## DNS Brute Force

Upload a wordlist via the Configuration page, or use the built-in default (~500 entries). Concurrency and resolvers are configurable per scan.

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `NEXT_PUBLIC_API_URL` | Backend URL seen by the browser |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |

`NEXT_PUBLIC_API_URL` is baked into the frontend at build time — rebuild the frontend image if you change it.

## Development

```bash
# Backend only (needs a running Postgres)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```

Database migrations run automatically on backend startup via Alembic.
