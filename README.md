# Multi-Tenant Enterprise Analytics

**Tenant-isolated sales analytics** with JWT RBAC, PostgreSQL row-level security, analytical SQL, a React dashboard, and Apache Superset — runnable with one Docker Compose command.

---

## Highlights

| Area | What you get |
|------|----------------|
| **Security** | JWT roles + PostgreSQL RLS on every tenant-scoped table |
| **Analytics** | Materialized view + window functions (`LAG`, running totals, `RANK`) |
| **API** | FastAPI + SQLAlchemy with OpenAPI docs |
| **UI** | React (Vite) dashboard with Recharts |
| **BI** | Apache Superset on a read-only Postgres role |
| **Ops** | Full stack via Docker Compose; Azure deploy notes included |

---

## Architecture

```text
Browser → React (nginx) → FastAPI → PostgreSQL (RLS)
                ↘                ↗
                 Apache Superset (read-only role)
```

1. Sign-in issues a JWT carrying `tenant_id`, `role`, and `is_platform_admin`
2. Each API request sets session GUCs (`app.current_tenant`, `app.current_role`, …) with `SET LOCAL`
3. RLS policies isolate `tenants`, `users`, and `sales` — even if application checks regress
4. Reporting reads `mv_daily_sales` with window functions for trends and rankings

---

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic, JWT (python-jose), bcrypt
- **Database:** PostgreSQL 16 — RLS policies, `SECURITY DEFINER` login lookup, materialized views
- **Frontend:** React 18, Vite, Recharts
- **BI:** Apache Superset 4 + Redis
- **Infra:** Docker Compose (API, UI, Postgres, Redis, Superset)

---

## Quick start

```bash
git clone https://github.com/ApolloMANIA/multi-tenant-analytics.git
cd multi-tenant-analytics
docker compose up --build
```

> **Docker permission denied?** Add yourself to the `docker` group, then sign out/in:
> `sudo usermod -aG docker $USER`
> Or run Compose with `sudo` for a one-off session.

| Service | URL |
|---------|-----|
| App UI | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Superset | http://localhost:8088 |
| Postgres | `localhost:5432` |

First boot applies SQL under `db/init/` (schema, RLS, seed data). To reset the database:

```bash
docker compose down -v && docker compose up --build
```

---

## Demo accounts

Password for every user: **`password123`**

| Email | Role | Access |
|-------|------|--------|
| `admin@platform.local` | Platform admin | Cross-tenant comparison |
| `admin@acme.local` | Acme admin | Acme only |
| `editor@acme.local` | Acme editor | Acme read + write |
| `viewer@acme.local` | Acme viewer | Acme read-only |
| `admin@globex.local` | Globex admin | Globex only |
| `viewer@globex.local` | Globex viewer | Globex read-only |

**Try isolation yourself:** sign in as `viewer@acme.local`, note products/revenue, then switch to `viewer@globex.local` — datasets do not overlap. Create a sale as a viewer → API returns `403` and RLS blocks the write.

---

## API overview

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/api/auth/login` | Issue JWT |
| `GET` | `/api/auth/me` | Current user |
| `GET` | `/api/sales` | Tenant-scoped via RLS |
| `POST` | `/api/sales` | Admin / editor only |
| `GET` | `/api/analytics/daily-revenue` | `LAG` + running total |
| `GET` | `/api/analytics/product-ranks` | `RANK()` within tenant |
| `GET` | `/api/analytics/tenant-comparison` | Platform admin only |
| `POST` | `/api/analytics/refresh-materialized-view` | Rebuild `mv_daily_sales` |

Interactive docs: http://localhost:8000/docs

---

## Superset (optional BI)

1. Open http://localhost:8088 — login `admin` / `admin`
2. **Settings → Database connections → + Database**
3. SQLAlchemy URI (from inside Compose):

```text
postgresql+psycopg2://superset_reader:superset_reader_secret@db:5432/analytics
```

From the host machine, use `localhost` instead of `db`.

4. Chart `mv_daily_sales` and `sales` (revenue over time, top products). Platform operators can compare tenants.

---

## Project layout

```text
backend/           FastAPI + SQLAlchemy + JWT/RLS session context
frontend/          React (Vite) + Recharts dashboard
db/init/           Schema, RLS policies, seed tenants/users/sales
superset/          Config + container entrypoint
docker-compose.yml Full local stack
```

---

## Local development (optional)

With Compose Postgres already running:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://app_user:app_user_secret@localhost:5432/analytics
export JWT_SECRET=dev
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Copy `.env.example` for optional overrides.

---

## Azure deploy (outline)

1. **Azure Database for PostgreSQL Flexible Server** — apply `db/init/*.sql`; allow Container Apps / App Service egress.
2. **Azure Container Apps** (or App Service) — build `api` / `frontend` images to ACR; set `DATABASE_URL`, `JWT_SECRET` (Key Vault), `CORS_ORIGINS`.
3. **Superset** — separate app + Redis (Azure Cache); keep metadata DB separate from analytics data; use `superset_reader`.
4. **Secrets & network** — no passwords in images; prefer private endpoints; expose only UI + Superset publicly.

```bash
az group create -n rg-tenant-analytics -l eastus
az acr create -g rg-tenant-analytics -n tenantanalyticsacr --sku Basic
az acr build -r tenantanalyticsacr -t tenant-api:latest ./backend
az acr build -r tenantanalyticsacr -t tenant-web:latest ./frontend
# then Flexible Server + Container Apps linked to ACR
```
