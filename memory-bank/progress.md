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
