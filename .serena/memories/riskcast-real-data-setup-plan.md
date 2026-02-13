# RiskCast V2 — Real Data Setup Plan

## Goal
Run RiskCast with 100% real data, no frontend mock fallbacks, realistic SME logistics company data.

## Current State
- **Database**: SQLite (`sqlite+aiosqlite:///./riskcast_dev.db`)
- **OMEN**: Configured at `http://localhost:8000` 
- **Twilio**: Keys configured in `.env` (TWILIO_ACCOUNT_SID, AUTH_TOKEN, API_KEY_SID, API_KEY_SECRET, WhatsApp number)
- **Anthropic**: API key configured in `.env`
- **Discord webhook**: Configured
- **Frontend**: Running at `http://localhost:5175/` (Vite)
- **Backend**: Running at port 8001 (V2 API)

## Architecture
```
OMEN (signals) → Oracle (correlate + reality data) → RiskCast (decisions) → Frontend
```

- OMEN provides SIGNALS (predictions with evidence)
- Oracle provides REALITY DATA (AIS, freight, port) — all support mock_mode
- Oracle correlates OMEN signals with reality data → CorrelatedIntelligence
- RiskCast generates decisions from CorrelatedIntelligence + CustomerContext

## API Keys Available
- Twilio (WhatsApp): ✅ Configured but user says "chưa setup" (WhatsApp Business not activated on Twilio side)
- Anthropic/Claude: ✅ Configured
- Discord Webhook: ✅ Configured
- AIS/MarineTraffic: ❌ Not needed — Oracle mock mode generates realistic data
- Polymarket: ❌ Not needed — OMEN handles this  
- NewsAPI: ❌ Not needed — OMEN handles this
- Freight APIs: ❌ Not needed — Oracle mock mode
- Port APIs: ❌ Not needed — Oracle mock mode

## Progress (Updated 2026-02-12)

### COMPLETED:
1. **Docker Desktop installed** via `winget install Docker.DockerDesktop`
2. **WSL2 being installed** — requires system restart
3. **.env updated** — DATABASE_URL switched to `postgresql+asyncpg://riskcast:riskcast@localhost:5432/riskcast`
4. **CORS updated** — added `http://localhost:5175` to allowed origins
5. **init_db() fixed** — `riskcast/db/engine.py` now creates all V2 tables from ORM models in dev mode (not just SQLite)
6. **Frontend mock disabled** — Added `VITE_DISABLE_MOCK=true` flag in `frontend/.env.local` and updated `withMockFallback()` in `frontend/src/lib/api.ts`
7. **Seed script enhanced** — `riskcast/scripts/seed.py` now creates:
   - 1 company (Vietlog Logistics)
   - 5 users (admin, test, analyst, manager, executive)
   - 10 Vietnamese customers
   - 5 routes (Vietnam ↔ major ports)
   - 30 orders
   - 50 payments
   - 10 incidents
   - **20 risk signals** (NEW)
   - **5 OMEN ingest signals** (NEW)
   - **4 alert rules** (NEW)
   - **15 outcomes** (NEW)
   - 1 risk appetite profile

### V2 Migration/Model Mismatch (KNOWN ISSUE):
- Migration `20260207_000001_v2_foundation_schema.py` creates tables WITHOUT `v2_` prefix
- Models in `riskcast/db/models.py` use `v2_` prefix (e.g., `v2_companies`)
- **Solution**: Skip Alembic for V2, use `init_db()` with `create_all()` instead
- V2 tables created directly from ORM models at startup

### REMAINING AFTER RESTART:
1. Restart computer (WSL2 requires this)
2. Start Docker Desktop (should auto-start after restart)
3. Run `docker compose up -d postgres redis` to start only PostgreSQL + Redis
4. Start backend: `python -m uvicorn riskcast.main:app --host 0.0.0.0 --port 8001 --reload`
   - Backend startup calls `init_db()` which creates all V2 tables
5. Run seed: `python -m riskcast.scripts.seed`
6. Start frontend: `cd frontend && npm run dev`
7. Test login: `admin@vietlog.vn / vietlog2026` or `hoangpro268@gmail.com / Hoang2672004`

### Key Files Modified:
- `.env` — DATABASE_URL → PostgreSQL, CORS → added port 5175
- `riskcast/db/engine.py` — `init_db()` creates tables for PostgreSQL in dev
- `riskcast/scripts/seed.py` — Enhanced with signals, OMEN, alerts, outcomes
- `frontend/src/lib/api.ts` — Added `VITE_DISABLE_MOCK` flag support
- `frontend/.env.local` — Created with `VITE_DISABLE_MOCK=true`

## Tasks Required (Original Plan)