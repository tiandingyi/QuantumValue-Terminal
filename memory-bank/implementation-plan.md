### Sprint 1: Infrastructure & "The Handshake"

**User Story 1: Monorepo & UI Template Foundation**
- **Requirement**: I want to initialize a unified monorepo structure using Turborepo and `pnpm workspaces`, and migrate the provided HTML/Tailwind dashboard template into the Next.js app.
- **Reason**: So that I have a high-performance development workflow and a ready-to-use visual interface for testing end-to-end connectivity.
- **Acceptance Criteria**:
    - Root `package.json` and `pnpm-workspace.yaml` correctly define workspaces for `apps/` and shared project tooling, with database migrations living under `db/`.
    - `turbo.json` is configured to orchestrate task pipelines for build, lint, and test.
    - The provided static HTML/Tailwind template is stored in `design/frontend-template/` as the unmodified reference source.
    - The template is successfully migrated into functional Next.js React components within `apps/web`.

**Implementation Note**
- Keep raw template files, screenshots, and copied vendor assets in `design/frontend-template/`.
- Keep production app code only in `apps/web`.
- Do not edit the raw template in place once migration work starts; use it as a reference source of truth.

User Story 2: One-Command Full-Stack Environment
- Requirement: I want to configure a comprehensive docker-compose.yml that networks all services together.
- Reason: So that any team member can start the web app, Go API, Python engine, and database migrations with a single command to perform end-to-end testing.
- Acceptance Criteria:
    - docker-compose.yml orchestrates the web (Next.js), api-go (Gin), engine-py (FastAPI), and db-migrate services.
    - Docker internal networking is correctly configured so the Next.js container can securely route API calls to the Go container, and Go can route to Python.
    - Local environment variables and CORS policies are managed via a .env.example template to allow seamless cross-origin requests during local development.

User Story 3: The End-to-End "Handshake"
- Requirement: I want to use the Next.js UI template to trigger a full-stack handshake request that flows through the Go Gateway to the Python Engine, running entirely within Docker Compose.
- Reason: To validate the end-to-end network topology, API contracts, and the asynchronous 202 Accepted polling mechanism before building complex parsing logic.
- Acceptance Criteria:
    - An interaction on the Next.js UI (e.g., typing a ticker in the search bar and hitting enter) triggers an HTTP request to the Go Gateway.
    ◦ The Go Gateway successfully receives the request and forwards a mock sync command to the Python Analysis Engine's /health or /sync endpoint.
    - The Python engine returns a successful response to Go, which then passes the result (or a 202 Accepted status) all the way back to the Next.js UI for display.
    - This entire flow is testable simply by running docker-compose up and interacting with localhost:3000 in the browser.

User Story 4: Automated CI Pipeline
- Requirement: I want to set up a GitHub Actions workflow.
- Reason: So that automated testing and build checks are performed on every push to ensure code stability.
- Acceptance Criteria:
    - `.github/workflows/ci.yml` triggers on `push` to `main` and on `pull_request`.
    - The workflow installs dependencies with the repository's pinned `pnpm` lockfile and uses the workspace Turborepo pipeline for `pnpm test`, `pnpm lint`, and `pnpm build`.
    - The workflow provisions the required runtimes for Node.js, Go, and Python so all three services can be validated in CI.
    - Frontend, Go, and Python build checks all pass in CI, and the Docker Compose configuration is syntax-validated.
    - Any failed test, lint, or build step causes the workflow to fail.

User Story 5: Supabase Persistence Bootstrap
- Requirement: I want to provision the Supabase persistence layer and apply the initial production schema for filings, metrics, and sync tracking.
- Reason: So that the Go Gateway and Python Analysis Engine can connect to a persistent PostgreSQL instance and store structured company, filing, metric, and sync state data in both development and production environments.
- Final Schema Design:
    - `companies`
      - `id UUID PRIMARY KEY` - Internal system identifier
      - `ticker VARCHAR UNIQUE NOT NULL` - Stock symbol (for example `AAPL`) used as the primary lookup handle
      - `cik CHAR(10) UNIQUE NOT NULL` - 10-digit SEC identifier that preserves leading zeros
      - `name VARCHAR NOT NULL` - Full legal name of the corporation
      - `sector VARCHAR NULL` - Broad economic sector (for example `Technology`)
      - `is_active BOOLEAN NOT NULL DEFAULT TRUE` - Enables or disables automated background scraping for the company
      - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when the company row was created
      - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when the company row was last updated
    - `filings`
      - `id UUID PRIMARY KEY` - Unique filing document identifier
      - `company_id UUID NOT NULL REFERENCES companies(id)` - Reference to the parent company in `companies`
      - `type VARCHAR NOT NULL` - Report type (for example `10-K` or `10-Q`)
      - `fiscal_year INT NOT NULL` - The calendar year this report represents
      - `period VARCHAR NOT NULL` - The fiscal period label (for example `FY`, `Q1`, `Q2`)
      - `accession_num VARCHAR UNIQUE NOT NULL` - SEC official receipt number used for deduplication
      - `filed_at DATE NOT NULL` - Date the report was officially published
      - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when this filing row was ingested
    - `financial_metrics`
      - `id UUID PRIMARY KEY` - Unique data record identifier
      - `filing_id UUID UNIQUE NOT NULL REFERENCES filings(id)` - Reference to `filings`, one metrics row per filing
      - `metrics JSONB NOT NULL` - Super-dictionary packing all parsed financial data (revenue, EPS, assets, liabilities, and more)
      - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when this metrics payload was ingested
    - `sync_status`
      - `id BIGSERIAL PRIMARY KEY` - Auto-incrementing log identifier for sync tracking
      - `company_id UUID NOT NULL REFERENCES companies(id)` - Reference to the company currently being processed
      - `task_type VARCHAR NOT NULL` - Current sync task type (for example `SCRAPE`, `PARSE`, `UPSERT`)
      - `status VARCHAR NOT NULL` - Task state (for example `PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`)
      - `last_error TEXT NULL` - Detailed error message or stack trace when a sync task fails
      - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when the sync status row was created
      - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` - Timestamp when the sync status row was last updated
- Acceptance Criteria:
    - The Supabase project is created manually through the official dashboard.
    - Only sensitive remote database values are entered manually through terminal `export` commands and then persisted into the local `.env`, while non-secret defaults remain committed in repo-managed env files.
    - The same sensitive values can be copied into GitHub Secrets through terminal commands without committing them to the repository.
    - Database initialization must remain runnable through `docker compose` locally, so a teammate can bring up the local PostgreSQL container and have the current migration set applied end to end without any manual SQL steps.
    - The initial migration creates `companies`, `filings`, `financial_metrics`, and `sync_status` exactly as defined above, including primary keys, foreign keys, unique constraints, and timestamps.
    - The remote Supabase PostgreSQL instance successfully accepts the migration from the repository migration tooling.
    - A successful connection test can be performed from the Go service to the remote Supabase PostgreSQL instance with `pnpm --filter api-go db:check`.
    - After migration, a basic verification query confirms that the expected tables exist in the remote database.

User Story 6: CI-Driven Supabase Initialization
- Requirement: I want GitHub Actions to initialize the remote Supabase database when the required secrets are available.
- Reason: So that the production persistence layer can be validated automatically and stay in sync with the repository migration set.
- Acceptance Criteria:
    - The CI workflow detects the required database secrets and uses them without committing any sensitive values to the repository.
    - The required CI secret is the remote Supabase `Supavisor session mode` connection string, exposed as `SUPABASE_DB_URL`; any direct connection secret remains optional for manual troubleshooting only.
    - GitHub Actions can connect to the remote Supabase PostgreSQL instance using the configured secrets.
    - The migration step applies the repository SQL migration set to the remote Supabase instance successfully.
    - A post-migration verification step confirms that `companies`, `filings`, `financial_metrics`, and `sync_status` exist in the remote database.
    - The workflow fails clearly if the connection, migration, or verification step fails.
    - Local `docker compose` initialization remains unchanged and continues to work independently of the remote Supabase CI path.
