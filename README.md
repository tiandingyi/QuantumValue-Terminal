# QuantumValue Terminal

QuantumValue Terminal is a documentation-first monorepo for a long-horizon fundamental analysis platform built on SEC EDGAR data.

## Runtime Baseline

- Node.js 22
- pnpm 10
- Go 1.25
- Python 3.12
- Tailwind CSS 4

## Project Context

The main planning and agent context lives in `memory-bank/`:
- `memory-bank/PRD.md` for product and architecture
- `memory-bank/tech-stack.md` for approved technologies
- `memory-bank/implementation-plan.md` for current execution steps
- `memory-bank/progress.md` for milestone tracking

## Working Conventions

- Repository-specific agent instructions live in `AGENTS.md`.
- Raw frontend template files should be stored in `design/frontend-template/`.
- Future production code should be organized under `apps/`, `services/`, and `db/`.

## Workspace Bootstrap

This repository now includes the initial `pnpm` workspace and Turborepo wiring for Sprint 1.

- Install dependencies: `pnpm install`
- Start the frontend from the workspace root: `pnpm dev`
- Start only the web app: `pnpm dev:web`
- Build all configured workspaces: `pnpm build`

## Local Full-Stack Docker

The repository now includes a root `docker-compose.yml` for the local stack.

1. Create a local env file from the template:
   Docker uses the committed `.env.docker-compose` defaults directly.
2. Start the stack:
   `docker compose up --build`
   If your local Docker installation does not support the `docker compose` subcommand, use `docker-compose up --build` instead.
3. Open the frontend:
   `http://localhost:3000`
4. Check the Go API directly:
   `http://localhost:8080/healthz`
5. Check the Python engine directly:
   `http://localhost:8000/healthz`
6. Trigger the handshake flow:
   enter `AAPL` in the search bar on `localhost:3000`, press `Sync`, and watch the UI move from `IN_PROGRESS` to `SUCCESS`
7. Inspect the polling endpoint directly if needed:
   `http://localhost:8080/api/v1/status/AAPL`

## Local Database Initialization Check

Use this section to verify that `docker compose` brings up PostgreSQL and applies the current migration set locally.

Required initialization step:

```bash
docker compose up --build postgres db-migrate
```

If your machine only supports the legacy Compose command, use:

```bash
docker-compose up --build postgres db-migrate
```

What it does:

- Starts the local PostgreSQL container
- Starts the migration container
- Applies the current migration files to the local database

Optional verification commands:

1. Show the current tables:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "\dt"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "\dt"
```

What it does:

- Connects to the running local PostgreSQL container
- Opens `psql` against the `quantumvalue` database
- Prints the currently visible tables

2. Show the public schema table names in sorted order:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
```

What it does:

- Queries PostgreSQL system metadata
- Prints only table names from the `public` schema
- Gives a cleaner confirmation than `\dt`

3. Inspect the `companies` table:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d companies"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d companies"
```

What it does:

- Shows the `companies` columns
- Shows its primary key, unique constraints, and indexes

4. Inspect the `filings` table:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d filings"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d filings"
```

What it does:

- Shows the `filings` columns
- Shows the foreign key back to `companies`
- Shows its unique constraints and indexes

5. Inspect the `financial_metrics` table:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d financial_metrics"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d financial_metrics"
```

What it does:

- Shows the `financial_metrics` columns
- Shows the `JSONB` metrics field
- Shows the one-to-one relationship to `filings`

6. Inspect the `sync_status` table:

```bash
docker compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d sync_status"
```

Legacy command equivalent:

```bash
docker-compose exec postgres psql -U quantumvalue -d quantumvalue -c "\d sync_status"
```

What it does:

- Shows the `sync_status` columns
- Shows the foreign key back to `companies`
- Shows the sync-tracking index

Expected tables:

- `companies`
- `filings`
- `financial_metrics`
- `sync_status`

## CI

GitHub Actions CI is defined in [`ci.yml`](.github/workflows/ci.yml).

- Triggers on pushes to `main`
- Triggers on pull requests
- Runs `pnpm test`, `pnpm lint`, and `pnpm build`
- Verifies Node, Go, and Python service builds inside CI
- Validates the Docker Compose configuration

## Supabase Provisioning

Provision the Supabase project manually in the official dashboard, then follow the terminal-first secret setup guide in [`infra/supabase-setup.md`](infra/supabase-setup.md).

The guide includes:

- `export` commands for manually entering only sensitive Supabase values
- a terminal command to append the non-secret local defaults and current exported values into `.env`
- `gh secret set` commands for GitHub Secrets
- a Go connection check command for the remote Supabase database

## Current Layout

- `apps/web`: Next.js 15 App Router frontend migrated from the staged dashboard template
- `design/frontend-template`: untouched raw HTML reference and staging area
- `services/go-gateway`: minimal Gin API gateway with health and handshake endpoints
- `services/python-engine`: minimal FastAPI engine service for local orchestration
- `db/migrations`: SQL migration source of truth for the local Postgres stack
- `infra`: future local environment and deployment scaffolding
