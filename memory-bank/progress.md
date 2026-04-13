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
- Completed Sprint 2 User Story 5 sync status stage logging:
  - Added the story definition to the implementation plan so stage-level `SCRAPE`, `PARSE`, and `STORE` visibility is tracked explicitly.
  - Updated the FastAPI sync orchestration to upsert stage-specific `IN_PROGRESS` and `SUCCESS` rows while preserving the existing top-level `SEC_SYNC` status for handshake compatibility.
  - Hardened failure handling so the failing stage and the overall sync row both record `FAILURE` with the captured Python traceback in `last_error`.
  - Expanded sync tests to verify stage ordering on success, scrape-stage failure diagnostics, and store-stage failure diagnostics.

## 2026-04-13

- Completed Sprint 2 User Story 6 financial fact mapping exception guardrail:
  - Added a configurable required-vs-optional base fact mapping policy to the Python `FinancialMetric` parser.
  - Added a structured `FinancialMetricMappingError` that reports the missing canonical field, attempted SEC fallback tags, ticker, CIK, and filing-period context when available.
  - Updated the sync pipeline to pass company identity into the parser so parse-stage diagnostics are traceable.
  - Preserved optional fact tolerance while preventing required mapping failures from reaching filing or metrics persistence.
  - Added regression tests covering required mapping failures, optional missing facts, parse-stage failure status updates, and no partial persistence.
- Completed Sprint 3 User Story 1 Go Gateway sqlc financials pass-through API:
  - Reconciled the Sprint 3 story definitions so the first card is the PRD-mandated Go Gateway sqlc pass-through layer, followed by derived metrics, valuation, and frontend visualization cards.
  - Added sqlc configuration, query files, and generated Go query code for `companies`, `filings`, `financial_metrics`, and `sync_status`.
  - Refactored the Go PostgreSQL financials store to use sqlc-generated `Queries` instead of hand-written row scanning in route/store code.
  - Added `GET /api/v1/financials/:ticker` with case-insensitive ticker lookup, JSONB base/derived metric pass-through, and cache-miss triggering of the Python sync path.
  - Updated `GET /api/v1/status/:ticker` to prefer database-backed `SEC_SYNC` rows while preserving the Python proxy fallback for handshake compatibility.
  - Added Go regression tests for cached JSONB responses, invalid tickers, cache-miss sync triggering, database read failures, and database-backed in-progress status polling.
- Completed Sprint 3 User Story 2 derived value metrics engine:
  - Added a Python calculation layer that derives Free Cash Flow, Owner Earnings, ROE, Gross Margin, and revenue 10-year CAGR from normalized `FinancialMetric` base facts.
  - Updated the FastAPI sync pipeline so derived metrics are calculated immediately after base parsing, with existing historical `base_metrics` loaded from JSONB when available for CAGR, then persisted separately into `derived_metrics`.
  - Preserved base SEC DNA isolation by keeping `base_metrics` untouched and skipping only dependent derived calculations when inputs are missing.
  - Added unit tests for derived formulas, missing-input skip behavior, zero-denominator ratio safety, 10-year CAGR history requirements, and sync persistence handoff.
- Completed Sprint 3 User Story 3 quantitative valuation filter:
  - Added a valuation calculation module for net-income 10-year CAGR, average tax-after dividend yield, current static P/E, historical P/E percentile, valuation formula score, and threshold flags.
  - Kept market-derived inputs explicit so the engine does not fabricate current price, dividend yield, or P/E history when no market data source is configured.
  - Appended a dedicated `valuation` section inside `derived_metrics`, including skipped/missing-input diagnostics when valuation inputs are unavailable.
  - Updated persistence serialization so mixed derived metric dataclasses and nested valuation dictionaries are JSONB-ready.
  - Added unit tests for valuation formula scoring, P/E percentile flagging, formula threshold flagging, missing-input diagnostics, and sync persistence handoff.
- Completed Sprint 3 User Story 4 frontend archaeology visualization:
  - Added a Next.js dashboard module that consumes the Go Gateway `GET /api/v1/financials/:ticker` JSONB endpoint.
  - Rendered Revenue vs. Net Income and Free Cash Flow Chart.js time-series views from filing snapshots.
  - Added a Valuation Scorecard for current P/E percentile, Owner Earnings, and the quantitative formula score.
  - Added loading, cache-mining, endpoint-error, no-chartable-data, and incomplete-history fallback states.
  - Added frontend helper tests for JSONB financial payload transformation and scorecard formatting.
- Tightened Sprint 3 historical filing behavior after local Docker verification:
  - Updated the Python sync pipeline to parse and persist up to 20 recent supported SEC 10-K/10-Q filing periods per ticker instead of only the latest filing.
  - Kept Go Gateway reads on the existing sqlc JSONB pass-through path while allowing the frontend to receive multi-period filing snapshots.
  - Reworked the frontend scorecard to prioritize SEC-derived historical fundamentals and avoid surfacing skipped valuation inputs as primary `Pending` cards.
  - Added a historical filing table and fixed the Sync button cursor affordance.
  - Verified local `COST` sync now stores 20 `financial_metrics` rows from 2021-05-09 through 2026-02-15.
