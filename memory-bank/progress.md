## 2026-03-23

- Completed Sprint 1 User Story 1 foundation work:
  - Added root `pnpm` workspace and `turbo.json` task orchestration.
  - Created monorepo skeleton for `apps/`, `services/`, `db/`, and `infra/`.
  - Bootstrapped `apps/web` as a Next.js 15 App Router frontend with Tailwind CSS.
  - Migrated the staged dashboard template into typed React components with a client-side Chart.js integration.
- Completed Sprint 1 User Story 2 local environment work:
  - Added root `docker-compose.yml` orchestrating web, api-go, engine-py, postgres, and db-migrate services.
  - Added `.env.example` to document local ports, internal service URLs, database credentials, and CORS origins.
  - Added a minimal Gin API gateway, FastAPI engine, and initial SQL migration set so the Docker stack can boot end to end.
  - Added a web stack health panel that checks the Go-to-Python handshake from the frontend.
- Completed Sprint 1 User Story 3 handshake flow:
  - Added ticker-triggered sync requests from the Next.js search UI.
  - Added Go gateway endpoints that forward mock sync and status requests to the Python engine.
  - Added Python engine mock async sync state with `IN_PROGRESS` to `SUCCESS` transitions.
  - Added frontend polling so the browser visibly moves from `IN_PROGRESS` to `SUCCESS` after a mock filing sync completes.
- Completed Sprint 1 User Story 4 CI foundation:
  - Added a GitHub Actions workflow that runs on pushes to `main` and on pull requests.
  - Added monorepo test, lint, and build verification through the Turborepo pipeline.
  - Added Go and Python workspace package scripts so non-frontend services participate in CI checks.
  - Added Docker Compose syntax validation to catch orchestration regressions in CI.
- Standardized runtime and frontend tooling versions:
  - Locked the project baseline to Node.js 22, pnpm 10, Go 1.25, Python 3.12, and Tailwind CSS 4.
  - Migrated the web app away from a Tailwind 3 config file to Tailwind 4 CSS-first theme tokens and PostCSS plugin wiring.
- Added Supabase provisioning scaffolding:
  - Split non-secret local defaults into committed env templates and reserved manual terminal exports for sensitive remote database values.
  - Added a terminal-first provisioning runbook for local `.env` and GitHub Secrets setup.
  - Added a Go `db:check` command to verify connectivity to a remote Supabase PostgreSQL instance.
- Finalized the initial database schema for persistence bootstrap:
  - Replaced the prototype migration with the canonical `companies`, `filings`, `financial_metrics`, and `sync_status` tables.
  - Preserved `docker compose` database initialization so the full schema can be applied locally without manual SQL.
- Added CI scaffolding for remote Supabase initialization:
  - Added a dedicated GitHub Actions job that runs only on pushes to `main`.
  - Scoped the remote initialization path to GitHub Secrets only, keeping local Docker env values separate.
  - Added migration application, Go connectivity verification, and remote table existence checks for Supabase.
- Tightened the remote Supabase CI path to the session-mode connection:
  - Reduced the required GitHub Actions secret set to `SUPABASE_DB_URL`.
  - Pointed CI migration and verification steps at the session pooler so hosted runners do not depend on the direct IPv6-only database host.

## 2026-03-30

- Realigned the Go gateway implementation with the documented architecture:
  - Replaced the temporary `net/http` router with a real Gin router in `services/go-gateway`.
  - Added route-level Go tests covering health, CORS preflight, and invalid ticker validation.
  - Updated the technical stack notes so the documented API layer matches the running code.
- Completed Sprint 2 User Story 1 SEC EDGAR foundation:
  - Added a reusable Python `USProvider` that resolves case-insensitive tickers through SEC `company_tickers.json`, pads CIKs to 10 digits, and fetches both `submissions` and `companyfacts`.
  - Enforced SEC Fair Access headers with the required `User-Agent` and `Accept-Encoding`, plus an internal 0.15 second throttle to stay below 10 requests per second.
  - Added a standalone proof-of-concept script at `services/python-engine/scripts/sec_test.py` and verified it live against SEC data for `NVDA`, including latest `Assets` extraction.
  - Upgraded the FastAPI sync flow so background jobs now perform real SEC fetches and expose a structured `latest_assets` summary in sync status details.
  - Added Python tests covering ticker mapping, CIK padding, header usage, throttling behavior, and async sync success/failure handling.

## 2026-03-31

- Completed Sprint 2 User Story 2 Pydantic standardization layer:
  - Added a canonical `FinancialMetric` Pydantic model for 13 base financial facts, separate from the downstream derived-metrics flow.
  - Added a dedicated parser that maps raw SEC company facts into standardized fields using synonym fallback lists for revenue, earnings, cash flow, leverage, equity, EPS, and share-count tags.
  - Enforced strict absolute-value normalization for abbreviated units such as `millions` and `billions` before model validation.
  - Hardened parsing fault tolerance so missing or `null` facts now default to `None` with non-fatal warning logs instead of breaking the pipeline.
  - Added mock-based parser tests covering synonym mapping, unit normalization, and graceful handling of missing metrics.
- Completed Sprint 2 User Story 3 JSONB persistence layer:
  - Added a second database migration that extends `filings` with direct upsert keys (`cik`, `form_type`, `period_end_date`, `accession_number`) and extends `financial_metrics` with separate `base_metrics` and `derived_metrics` JSONB columns.
  - Added a SQLAlchemy-backed persistence store that reflects the PostgreSQL schema, upserts companies, sync status, filing registry rows, and JSONB metric payloads.
  - Connected the Python sync flow to persist base Pydantic metrics and derived ratios while preserving in-memory polling responses for the existing handshake path.
  - Added filing metadata extraction plus persistence-focused unit tests covering filing selection, JSON-ready payloads, and sync status transitions without requiring a live database.

## 2026-04-01

- Completed Sprint 2 User Story 4 SEC rate limiting and resilience:
  - Added the story definition to the implementation plan so the SEC request guardrail and 429 recovery behavior are tracked alongside the earlier Sprint 2 stories.
  - Kept the existing provider-level throttle in place so SEC requests remain capped below 10 requests per second.
  - Added bounded 429 retry handling in `USProvider`, including `Retry-After` header support, exponential backoff fallback, and warning logs for each retry attempt.
  - Preserved failure transparency by raising a final `HTTPError` after the retry budget is exhausted instead of silently swallowing repeated SEC throttling responses.
  - Expanded provider tests to cover successful 429 recovery, retry exhaustion, and the interaction between retry sleeps and the existing throttle behavior.
