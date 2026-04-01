### Sprint 1: Infrastructure & "The Handshake"

**Migration Guardrail**
- Never rewrite or replace the contents of an existing numbered migration once it has been introduced into the repository or used by any local/remote environment.
- All schema evolution must happen through new forward-only migration files so local Docker state, remote databases, and `schema_migrations` history stay consistent.

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

### **Sprint 2: The SEC Harvester (Python) - User Stories**

---

**User Story 1: SEC EDGAR API Integration**

**Title:** SEC EDGAR API Basic Integration & Company Data Fetching (with Ticker Support)

**Role:** Data Engineer
**Requirement:** I want to implement a Python `US_Provider` module that allows users to input standard US stock tickers, automatically converts them to their corresponding CIKs, and fetches the raw "Company Facts" and "Submissions" JSON data from the SEC EDGAR API.
**Reason:** To provide a reliable, legally compliant, and foundational raw data source for subsequent quantitative analysis, data flattening, and "financial archaeology."

**Acceptance Criteria (Definition of Done):**

- **AC1: Independent Local Verification (POC First)**
    - Before integrating any code into the FastAPI backend engine, a standalone Python test script (e.g., `sec_test.py`) must be delivered.
    - **Execution:** The script must run successfully in a local Python 3.x environment using `python sec_test.py` (with the `requests` library installed).
    - **Definition of Success:**
        1. **No Blocking Errors:** The script executes fully without throwing `403 Forbidden` (verifying UA and rate limits) or `404 Not Found` (verifying Ticker-to-CIK mapping).
        2. **Basic Validation:** Successfully prints the correct English entity name for a hardcoded target ticker (e.g., printing "NVIDIA CORP" for `NVDA`).
        3. **Deep Data Extraction:** Successfully extracts and prints at least one specific financial metric from the deeply nested JSON tree (e.g., clearly outputting the exact monetary value and end date of the latest "Assets").
- **AC2: Automated Ticker-to-CIK Mapping**
    - The system must call the SEC's `company_tickers.json` endpoint to map user-input tickers (e.g., `AAPL`) to their base CIKs (e.g., `320193`).
    - The input must be case-insensitive (`aapl` and `AAPL` must both be valid).
- **AC3: CIK Formatting & Endpoint Integration**
    - Prior to making data requests, the system must automatically pad the base CIK to a strict 10-digit string format (e.g., converting `320193` to `0000320193`).
    - Successfully retrieve data from the Submissions endpoint (`/submissions/CIK{cik}.json`) and the Company Facts endpoint (`/api/xbrl/companyfacts/CIK{cik}.json`).
- **AC4: Mandatory Compliance Headers (SEC Fair Access)**
    - All outbound HTTP requests *must* carry the realistic, compliant User-Agent header: `Dingyi Quant Research data-ops@dingyi-analytics.net`. Failure to include this fails the AC.
    - Headers must also include `Accept-Encoding: gzip, deflate` to optimize payload transmission.
- **AC5: API Rate Limiting**
    - The module must implement an internal throttling mechanism (e.g., a `time.sleep` of 0.15 seconds per request in a single-threaded context).
    - Outbound requests must strictly remain under the SEC's limit of 10 requests per second to prevent triggering circuit breakers and IP bans.

---

**User Story 2: Raw XBRL Data Parsing & Standardization (Pydantic Layer)**

**Role:** Financial Analyst
**Requirement:** I want the system's Python engine to automatically parse raw SEC XBRL/JSON data and map it to a standardized `FinancialMetric` Pydantic model.
**Reason:** So that inconsistent accounting tags across different companies are normalized into a single source of truth, providing clean, unit-unified base facts for the downstream Value Investing Calculation Engine.

**Scope & Boundaries:**

- **In-Scope:** Mapping raw JSON to standardized Python objects, fault tolerance for missing data, extracting core financial facts, and strict absolute value conversion such as millions to full numeric values.
- **Out-of-Scope:** Frontend number formatting and calculation of downstream derived metrics such as Free Cash Flow, ROE, or Gross Margin.

**Acceptance Criteria (Definition of Done):**

- **AC1: Accurate Base Fact Extraction & Synonym Compatibility**
    - Given the system receives raw SEC JSON data containing various official accounting tags such as `RevenueFromContractWithCustomer` or `TotalRevenues`,
    - When the data is parsed through the `FinancialMetric` Pydantic model,
    - Then the model must correctly identify and output the following 13 core metrics:
        1. `revenue`
        2. `gross_profit`
        3. `operating_income`
        4. `net_income`
        5. `operating_cash_flow`
        6. `capex`
        7. `depreciation_and_amortization`
        8. `assets`
        9. `liabilities`
        10. `shareholders_equity`
        11. `long_term_debt`
        12. `eps_diluted`
        13. `shares_outstanding`
    - Engineers must add unit tests using mock JSON payloads with company-specific synonym tags and verify they map to the same internal field names.
- **AC2: Strict Unit Normalization**
    - Given the input JSON contains abbreviated numerical units such as `millions` or `billions`,
    - When the model parses those fields,
    - Then the output values must be converted to their absolute integer or float forms, and storing abbreviated relative values is prohibited.
- **AC3: Graceful Missing Value & Fault Tolerance Handling**
    - Given a report omits a metric entirely or reports the value as `null`,
    - When the engine parses the incomplete payload,
    - Then parsing must not throw a fatal exception, and the model must gracefully default the missing metric to `None` while logging a non-fatal warning.

---

**User Story 3: Database Persistence (JSONB "DNA" Injection)**

**Role:** Developer
**Requirement:** I want the Analysis Engine to persist validated SEC filing metadata and normalized metrics into the `filings` and `financial_metrics` tables using JSONB format.
**Reason:** So that the Go Gateway can perform high-speed, type-safe pass-through queries to the Next.js frontend without complex SQL pivots or joins.

**Scope & Boundaries:**

- **In-Scope:** SQLAlchemy-compatible database schema interaction, upsert logic, JSONB persistence, and separation of base versus derived metric blobs.
- **Out-of-Scope:** Go-side `sqlc` generation and Python-to-Go async callbacks.

**Acceptance Criteria (Definition of Done):**

- **AC1: Metadata Upsert & Filing Registry**
    - Given the Python engine has parsed a new 10-K or 10-Q filing,
    - When the data is committed to the `filings` table,
    - Then the engine must upsert using the unique combination of `cik`, `form_type`, and `period_end_date`, while populating `accession_number` and `filed_at`.
- **AC2: Wide-Format JSONB Storage (Base Metrics)**
    - Given a Pydantic model containing standardized base facts,
    - When persisting to the `financial_metrics` table,
    - Then all base facts must be serialized into a single `base_metrics` JSONB column for fast historical pass-through queries.
- **AC3: Derived Metrics & Calculation Traceability**
    - Given the system has generated derived ratios,
    - When saving them,
    - Then they must be stored in a separate `derived_metrics` JSONB column so raw SEC source DNA remains isolated from internal calculations.
- **AC4: Sync Status & Concurrency Control**
    - Given a background sync process is triggered via the Go Gateway,
    - When Python begins and ends scraping,
    - Then the engine must update database-backed sync status through the expected transition `PENDING -> IN_PROGRESS -> SUCCESS` or `FAILURE`.

---

**User Story 4: SEC Rate Limiting & Resilience**

**Role:** DevOps Engineer
**Requirement:** I want to implement a rate-limiting mechanism that restricts SEC API calls to no more than 10 requests per second.
**Reason:** To comply with SEC regulations and prevent the platform's IP from being blacklisted.

**Acceptance Criteria (Definition of Done):**

- **AC1: Request Frequency Guardrail**
    - The engine must use a shared request wrapper, middleware, decorator, or equivalent provider-level mechanism to keep SEC traffic at or below 10 requests per second.
- **AC2: 429 Resilience**
    - When the SEC returns `429 Too Many Requests`,
    - The engine must apply a back-off and retry strategy instead of failing immediately.
    - The retry flow should honor `Retry-After` when present and otherwise use a bounded back-off policy.

---

**User Story 5: Sync Status & Error Logging**

**Role:** DevOps Engineer
**Requirement:** I want the Python engine to update the `sync_status` table at each stage of the scraping process (`SCRAPE`, `PARSE`, `STORE`).
**Reason:** To provide real-time visibility into the progress of 20-year data backfills and simplify troubleshooting of failed extractions.

**Acceptance Criteria (Definition of Done):**

- **AC1: Stage-Level In-Progress Tracking**
    - Each stage task must begin by upserting an `IN_PROGRESS` status row in the database.
- **AC2: Stage-Level Success Tracking**
    - When a stage completes successfully, the engine must mark that same stage row as `SUCCESS`.
- **AC3: Failure Diagnostics**
    - When a stage fails, the engine must mark the failing stage as `FAILURE` and capture the stack trace or error message in `last_error` for debugging.
