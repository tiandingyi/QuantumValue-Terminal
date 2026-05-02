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

---

**User Story 6: Financial Fact Mapping Exception Guardrail**

**Role:** Data Quality Engineer
**Requirement:** I want the Python engine to treat unmapped required financial facts as a hard parsing exception before database persistence.
**Reason:** The SEC XBRL tag fallback list may be incomplete for some companies or industries. If the parser cannot map required facts into the canonical Pydantic model, the system should fail loudly instead of silently storing incomplete or misleading financial DNA.

**Scope & Boundaries:**

- **In-Scope:** Detecting unmapped required base facts during the SEC company-facts to `FinancialMetric` conversion step, surfacing structured parse errors, marking sync status as `FAILURE`, and preventing writes to `filings` and `financial_metrics` for failed conversions.
- **Out-of-Scope:** Automatically discovering new SEC taxonomy mappings, using AI to infer missing tags, or backfilling historical rows already written before this guardrail exists.

**Acceptance Criteria (Definition of Done):**

- **AC1: Required Mapping Failure Detection**
    - Given the parser cannot find a configured SEC XBRL tag for any required canonical base fact,
    - When converting raw SEC `companyfacts` into the `FinancialMetric` Pydantic model,
    - Then the parser must raise a structured exception that names the canonical field, attempted fallback tags, ticker/CIK when available, and filing period context when available.
- **AC2: No Partial Persistence on Parse Failure**
    - Given a required financial fact mapping fails,
    - When the sync pipeline reaches the `PARSE` stage,
    - Then the engine must not write or upsert the related `filings` or `financial_metrics` rows for that filing.
- **AC3: Sync Status Error Capture**
    - Given a mapping exception is raised,
    - When the background sync handles the failure,
    - Then the `PARSE` stage and overall `SEC_SYNC` status must be marked as `FAILURE`, with the missing field and candidate tag list captured in `last_error`.
- **AC4: Configurable Required vs Optional Facts**
    - Given some canonical facts may be legitimately unavailable for certain companies or periods,
    - When defining the mapping rules,
    - Then the engine must explicitly distinguish required facts from optional facts instead of treating every missing value the same way.
- **AC5: Regression Tests for Guardrail Behavior**
    - Add tests proving that a missing required mapping fails before persistence, records parse-stage diagnostics, and leaves the database persistence store untouched.
    - Add tests proving that a missing optional mapping still produces a valid `FinancialMetric` with `None` for that optional field.

### **Sprint 3: Analysis, Query, and Visualization - User Stories**

---

**User Story 1: Go Gateway High-Speed Data Pass-Through with sqlc**

**Role:** Backend Engineer
**Requirement:** I want the Go Gateway to expose secure, read-only RESTful endpoints using sqlc-generated PostgreSQL query code. The gateway must connect to the database purely via environment variables such as `DATABASE_URL`, remain agnostic to local PostgreSQL versus cloud Supabase, and fetch time-series `base_metrics` and `derived_metrics` JSONB payloads.
**Reason:** To ensure architectural portability for local offline development while using PRD-mandated sqlc types for fast, reliable JSONB pass-through into the Next.js frontend.

**Acceptance Criteria:**

- The Go codebase contains zero Supabase-specific SDKs or database logic.
- The Go database access layer uses sqlc-generated `Queries`; hand-written row scanning in route/store code is prohibited.
- The repository includes sqlc configuration plus query files so generated query code can be refreshed consistently.
- Environment configuration allows seamless switching between local and production PostgreSQL connection strings via env files.
- The Go Gin gateway implements a financials endpoint such as `GET /api/v1/financials/:ticker` that validates and resolves the ticker case-insensitively.
- The endpoint reads PostgreSQL JSONB columns from `financial_metrics.base_metrics` and `financial_metrics.derived_metrics` through sqlc and directly marshals them into a structured JSON response for the Next.js client.
- On a cache miss, the endpoint triggers the Python sync path and returns an accepted mining response instead of fabricating empty financial rows.
- `GET /api/v1/status/:ticker` prefers database-backed `SEC_SYNC` status rows and preserves `202 Accepted` for `PENDING` or `IN_PROGRESS` states.
- Go regression tests prove cached JSONB pass-through, invalid ticker rejection, cache-miss sync triggering, database error handling, and database-backed status polling.

**User Story 2: Derived Value Metrics Engine**

**Role:** Financial Analyst / Data Engineer
**Requirement:** I want the Python engine to automatically calculate derived financial metrics such as Free Cash Flow, Owner Earnings, ROE, Gross Margin, and 10-Year CAGR from the `base_metrics` JSONB payload, and persist them into the `derived_metrics` JSONB column.
**Reason:** To translate raw SEC accounting DNA into standardized fundamental business indicators necessary for assessing a company's economic moat and intrinsic value.

**Acceptance Criteria:**

- The Python engine implements a calculation pipeline that triggers after base metrics are successfully parsed.
- The system accurately calculates Owner Earnings by adjusting net income for depreciation, amortization, and capital expenditures.
- The generated derived metrics are isolated and stored within the `derived_metrics` JSONB column in the `financial_metrics` table.
- Missing base facts gracefully skip dependent derived calculations without halting the overall pipeline.

**User Story 3: Quantitative Valuation Filter**

**Role:** Quant Developer
**Requirement:** I want the Python engine to implement a custom valuation formula evaluating `(10-Year CAGR + 10-Year Average Tax-After Dividend Yield) / Current Static PE`. It must also calculate historical P/E percentiles, specifically flagging targets positioned above the 80th percentile.
**Reason:** To programmatically filter the top 2% of companies with durable business models, ensuring selected targets represent a wide expected margin of safety and a high-certainty investment return.

**Acceptance Criteria:**

- The engine accurately aggregates 10-year historical data to compute CAGR for net profit and average dividend yield.
- The system computes current Static PE and evaluates the core formula, flagging any company where the resulting ratio is greater than 1.5.
- The system tracks historical P/E ratios and calculates the current P/E percentile relative to the company's historical baseline, raising a flag when it exceeds the 80th percentile.
- Valuation flags and scores are appended to a dedicated section within `derived_metrics`.

**User Story 4: Frontend "Archaeology" Visualization**

**Role:** Frontend Developer
**Requirement:** I want to build a React Server Component or client-side Chart.js module in the Next.js app that consumes the Go Gateway financials endpoint to render a 10-year financial trend dashboard.
**Reason:** To provide a professional, ready-to-use visual interface that synthesizes complex numerical data into clear graphical trends for immediate fundamental analysis.

**Acceptance Criteria:**

- The Next.js UI features a dashboard layout displaying at least two Chart.js time-series graphs, such as Revenue vs. Net Income and Free Cash Flow.
- The UI displays a prominent Valuation Scorecard showing the target's current P/E Percentile, Owner Earnings, and Quantitative Formula Score.
- The component correctly handles loading states and displays a graceful fallback if the 10-year historical data is incomplete.

**User Story 5: Browser E2E Verification for Sync-to-Dashboard Flow**

**Role:** QA Engineer / Full-Stack Developer
**Requirement:** I want every frontend-facing Sprint 3 card to include an end-to-end browser verification path that operates the actual Next.js UI against the local Docker stack.
**Reason:** To catch hydration issues, non-clicking buttons, stale default ticker state, missing historical rows, and other real user-flow regressions that unit tests or direct API checks cannot reveal.

**Acceptance Criteria:**

- Before marking any UI or sync-to-dashboard card complete, the agent must run the local parity stack with `docker compose` and operate the frontend in a real browser, not only through curl or component helper tests.
- The E2E flow must enter a non-default ticker such as `cost`, click `Sync`, and verify that the UI visibly transitions from the previous active ticker to the requested ticker.
- The E2E flow must confirm the Go Gateway receives the matching `/api/v1/sync/:ticker`, `/api/v1/status/:ticker`, and `/api/v1/financials/:ticker` traffic while preserving the PRD architecture: Next.js -> Go Gateway -> sqlc/PostgreSQL and Go Gateway -> Python sync.
- The E2E flow must verify that historical filing data appears in the UI after sync, including at least one charted financial series and the historical filing table populated from Go Gateway JSONB data.
- The E2E flow must explicitly check UX affordances that unit tests miss, including that the Sync button is clickable, the cursor affordance is correct, loading/mining states are visible, and stale placeholder copy such as the default `AAPL` state does not remain after a successful ticker change.
- The E2E evidence must include either a Playwright trace/screenshot artifact under `output/playwright/` or a terminal-recorded browser snapshot plus the exact command used to reproduce the flow.
- If Playwright CLI or browser automation tooling is unavailable, the card cannot be marked complete until the blocker is documented and resolved; API-only verification is insufficient for frontend-facing cards.
- CI should eventually run a deterministic E2E variant against seeded or mocked local data, but local human-equivalent browser operation remains required before closing the story.

**User Story 6: Full SEC Historical Filing Ingestion**

**Role:** Data Engineer
**Requirement:** I want a company sync to ingest every SEC-available supported historical filing for that issuer instead of stopping at a fixed year count or recent-filing cap.
**Reason:** So that the terminal can behave like true financial archaeology: the frontend receives the complete parseable 10-K history, plus the newest 10-Q when no annual report exists for the latest year.

**Scope & Boundaries:**

- **In-Scope:** SEC submissions archive file discovery, historical 10-K/10-Q metadata extraction, duplicate accession handling, per-filing parse tolerance for older incomplete company-facts periods, JSONB persistence through the existing Python SQLAlchemy ingestion path, and Go sqlc read compatibility.
- **Out-of-Scope:** Hand-parsing legacy HTML filings that are absent from SEC companyfacts JSON, market-data enrichment, or changing the frontend annual-first display policy.

**Acceptance Criteria:**

- The engine fetches the main SEC submissions payload plus every archive payload listed under `filings.files`.
- Sync no longer uses a fixed 10-year or 20-filing ingestion cap.
- Only `10-K` and `10-Q` filings are selected for financial metric parsing and persistence.
- Duplicate filing metadata is removed by accession number, with a CIK/form/period fallback key.
- Individual older periods that cannot map required facts are skipped with diagnostics while all other parseable periods still persist.
- Sync status details report discovered, parsed, skipped, persisted, earliest-period, and latest-period values.
- The frontend contract remains unchanged: Go Gateway still serves expanded historical records through the existing sqlc-backed JSONB financials endpoint.

**User Story 7: Yearly Derived Metrics Table**

**Role:** Fundamental Analyst / Frontend User
**Requirement:** I want the system to calculate the target derived financial indicators for each available reporting year and display those yearly values in the frontend financial table.
**Reason:** So that the terminal can move beyond raw SEC facts and show a reusable, year-by-year analytical view of valuation, business quality, shareholder returns, financial risk, and pricing power.

**Scope & Boundaries:**

- **In-Scope:** Backend formula implementation, per-year derived metric calculation from existing `base_metrics`, persistence into `derived_metrics` JSONB, Go sqlc pass-through compatibility, frontend table columns, clear missing-input states, and browser E2E verification.
- **Out-of-Scope:** Hand-entered analyst overrides, non-SEC market-data provider integration unless a required metric explicitly has current price/market-cap inputs available, AI-based interpretation of missing fields, and changing the raw SEC base fact storage model.
- **Field mapping note:** Formulas below name concepts in English aligned with `base_metrics` / SEC mappings. The Python engine must map from SEC XBRL and canonical `base_metrics` keys (plus documented synonyms) to these concepts; when a concept is unavailable from filings, emit `missing_inputs` instead of guessing.

---

#### **Metric calculation spec (acceptance source of truth)**

##### **0. Global conventions**

- **Money units:** Numerator and denominator inside a single formula must share one scale (for example both in dollars or both in millions); never mix scales.
- **Two percentage conventions:**
  - DCF and growth math use **decimals**: `8% = 0.08`.
  - PEG / PEGY denominators use **whole percentage points**: `8% = 8` (not `0.08`).  
    Example: `PE = 20`, `CAGR = 10%` → `PEG = 20 / 10 = 2`, not `20 / 0.10`.
- **Margin of safety (default 30%):**

```text
margin_of_safety = 30%
margin_of_safety_price = intrinsic_value × (1 - 30%) = intrinsic_value × 70%
```

- **Persistence:** Persist every default parameter (`r`, `g_tv`, margin of safety, default retention, default payout, default effective tax rate, Munger exit multiples, and so on) inside `derived_metrics` for audit and replay.

##### **1. Valuation metrics**

**1.1 OE-DCF (owner earnings DCF)**

- **Defaults:** `r = 10% = 0.10`, `g_tv = 3% = 0.03`, forecast years `n = 10`, margin of safety `30%`.
- **Maintenance capex:**

```text
if D&A > 0: maintenance_capex = min(capex, D&A)
if D&A <= 0: maintenance_capex = capex
```

Where `D&A = depreciation_and_amortization` and `capex = cash_paid_for_ppe_and_intangibles` (map from cash-flow statement tags per SEC).

- **Owner earnings OE:**

```text
OE = net_income_attributable_to_parent + D&A - maintenance_capex
```

- **Smoothed OE:** Arithmetic mean of OE over the **latest up to 3** fiscal years; `avg_OE_per_share = avg_OE / shares_outstanding_current`.
- **Growth rate g (decimal):** Prefer the **median** of OE year-over-year changes over the **latest up to 7** years:

```text
OE_YoY_i = (OE_i - OE_{i-1}) / OE_{i-1}
median_g = median(OE_YoY)
```

- **Growth ceiling:**

```text
ROE = net_income_attributable_to_parent / parent_shareholders_equity
      (default: period-end equity; if using average equity, disclose in derived payload)
payout_ratio = cash_dividends / net_income_attributable_to_parent
retention_ratio = 1 - payout_ratio
g_ceiling = min(ROE × retention_ratio, 0.25)
```

If payout is unreliable: **default retention ≈ 60%** (disclose in payload).  
**Final:** `g = max(0, min(median_g, g_ceiling))` with `g` as a decimal.

- **DCF:**

```text
PV_stage1 = Σ[ avg_OE_per_share × (1 + g)^t / (1 + r)^t ],  t = 1..10
OE_10 = avg_OE_per_share × (1 + g)^10
terminal_value = OE_10 × (1 + g_tv) / (r - g_tv)
PV_terminal = terminal_value / (1 + r)^10
OE_DCF_core = PV_stage1 + PV_terminal
net_cash_per_share = net_cash / shares_outstanding
OE_DCF_total = OE_DCF_core + net_cash_per_share
OE_DCF_margin_of_safety_price = OE_DCF_total × 70%
```

**1.2 Munger-style horizon valuation**

- **Structure:**

```text
V = PV_dividends + PV_terminal_equity_value + net_cash_per_share
```

- **Inputs:** Same `avg_OE_per_share`; same `g` rules as OE-DCF; `r` default `10%`; `n` default `10`; `payout` = **3-year average** payout ratio; if no dividend data use **`payout = 40%`** (disclose).

```text
payout_ratio = cash_dividends / net_income_attributable_to_parent
EPS_10 = avg_OE_per_share × (1 + g)^10
PV_dividends = Σ[ avg_OE_per_share × (1 + g)^t × payout / (1 + r)^t ],  t = 1..10
```

- **Exit PE multiples:** conservative `15x`, base `20x`, optimistic `25x`.

```text
exit_value_15 = EPS_10 × 15 / (1 + r)^10
exit_value_20 = EPS_10 × 20 / (1 + r)^10
exit_value_25 = EPS_10 × 25 / (1 + r)^10
munger_15 = PV_dividends + exit_value_15 + net_cash_per_share
munger_20 = PV_dividends + exit_value_20 + net_cash_per_share
munger_25 = PV_dividends + exit_value_25 + net_cash_per_share
munger_k_margin_of_safety_price = munger_k × 70%   (k ∈ {15,20,25})
```

**1.3 CAGR (general)**

```text
CAGR = (ending / beginning)^(1 / n) - 1
```

- **EPS CAGR storage:** Persist as **whole percentage points** (for example `10.0` means 10%, not `0.10`).
- **EPS series:** Prefer `real_eps`; fall back to **basic EPS**. Default window **3 years**; if starting EPS `<= 0`, walk back to the earliest usable positive EPS (record fiscal start, end, and `n` in payload).

**1.4 PEG**

```text
PE = spot_price / EPS_for_PE
```

Prefer `real_eps` for `EPS_for_PE`; if missing or `<= 0`, use basic EPS.

```text
PEG = PE / CAGR_percent_points
```

If `CAGR <= 0` or denominator missing, **PEG is not applicable** (structured reason; no fabricated value).

**1.5 PEGY**

```text
dividend_yield_percent = cash_dividends / market_cap × 100
market_cap = spot_price × shares_outstanding
PEGY = PE / (CAGR_percent_points + dividend_yield_percent)
```

If `CAGR_percent_points + dividend_yield_percent <= 0`, **PEGY is not applicable**.

**1.6 Earnings yield**

```text
earnings_yield = 1 / PE = EPS / spot_price
```

Prefer `real_eps` for EPS; may also show `earnings_yield_percent = EPS / spot_price × 100`.

##### **2. Shareholder return and dividends**

**2.1 Cash dividends (source priority)**

- Prefer **pure dividend** cash-flow concepts (map from SEC: common dividends paid, dividends to shareholders, and equivalent tags).
- If unavailable, fall back to **dividends and interest paid** aggregates (may include interest → payout ratios may read high); set `dividend_source = fallback` in `derived_metrics`.

**2.2 Buybacks and equity issuance**

```text
buyback_cash = cash_paid_for_share_repurchases (0 if not separately disclosed)
equity_issuance_cash = cash_from_equity_issuance - minority_equity_issuance
  (if minority line missing: equity_issuance_cash = cash_from_equity_issuance)
net_buyback_cash = buyback_cash - equity_issuance_cash
```

**2.3 Yields**

```text
market_cap = spot_price × shares_outstanding
dividend_yield_percent = cash_dividends / market_cap × 100
net_buyback_yield_percent = net_buyback_cash / market_cap × 100
total_shareholder_yield_percent = dividend_yield_percent + net_buyback_yield_percent
                                = (cash_dividends + net_buyback_cash) / market_cap × 100
```

**2.4 Dividend payout ratio**

```text
dividend_payout_ratio_percent = cash_dividends / net_income_attributable_to_parent × 100
```

Cross-check with per-share basis only if share counts align: `DPS / basic_EPS × 100`.

**2.5 Borrow-to-dividend risk (heuristic)**

```text
distributable_profit_proxy = OE - capex - current_debt_principal_maturities
```

If `distributable_profit_proxy <= cash_dividends`, flag **borrow-to-dividend / over-distribution risk**. If debt principal maturities are missing, do not assert the flag; return `missing_inputs`.

##### **3. Quality and risk metrics**

**3.1 Pledged shares to total shares**

```text
pledge_ratio_percent = pledged_shares / total_shares × 100
```

If upstream data supplies a pledge ratio directly, you may use it. Watch share units. Denominator is **company total shares**, not controlling shareholder stake.

**3.2 Book effective tax rate and benchmarks**

```text
book_effective_tax_rate_percent = income_tax_expense / EBT × 100
theoretical_tax_at_25_percent = EBT × 25%
theoretical_tax_at_15_percent = EBT × 15%
book_tax_to_theoretical_25_ratio_percent = income_tax_expense / (EBT × 25%) × 100
cash_taxes_to_theoretical_25_ratio_percent = cash_taxes_paid / (EBT × 25%) × 100
```

Note: `cash_taxes_paid` is not always corporate income tax alone (may include VAT and other levies); treat as supplemental.

**3.3 Goodwill to equity**

```text
goodwill_to_equity_percent = goodwill / equity_denominator × 100
```

`equity_denominator` priority: total shareholders’ equity; then parent equity; then other consolidated equity tags per available SEC mapping.

**3.4 Cash conversion (OCF to net income)**

```text
ocf_to_net_income = operating_cash_flow / net_income_attributable_to_parent
```

May display as a multiple (for example `1.37`) or `ocf_to_net_income_percent = OCF / net_income × 100`.

**3.5 ROIC (approximate)**

```text
EBIT ≈ operating_income + max(interest_expense, 0)
```

If interest expense is negative (net interest income), do not add back.

```text
effective_tax_rate = income_tax_expense / EBT
clamp effective_tax_rate to [0, 0.50]; if missing inputs, default to 0.25 (disclose)
NOPAT = EBIT × (1 - effective_tax_rate)
```

```text
interest_bearing_debt =
  short_term_borrowings
+ trading_financial_liabilities_interest_bearing (if disclosed)
+ current_portion_of_long_term_debt (interest-bearing portion; if indivisible, use reported total and document in metadata)
+ long_term_borrowings
+ bonds_payable
+ lease_liabilities (if disclosed)
```

```text
invested_capital ≈ interest_bearing_debt + parent_shareholders_equity - cash_and_equivalents
  (pick one cash field available in base_metrics and use consistently; record the choice)
ROIC = NOPAT / invested_capital
```

If `invested_capital <= 0` or required inputs are missing, **ROIC is not applicable**; return `missing_inputs`.

##### **4. Pricing power and profitability (in-table annual metrics)**

- **Margins (same fiscal year):**

```text
gross_margin_percent = gross_profit / revenue × 100
operating_margin_percent = operating_income / revenue × 100
net_margin_percent = net_income_attributable_to_parent / revenue × 100
```

If `revenue <= 0`, the margin is not applicable.

- **3-year CAGR:** Compute separately for revenue, gross profit, operating income, and net income using **section 1.3** rules (whole percentage points out; walk back if the start value is non-positive; record the window).

- **Year-over-year trends:** Where two consecutive years exist for revenue, gross profit, operating income, net income, and the margin series:

```text
YoY = (current_year - prior_year) / prior_year
```

Whether YoY is stored as a decimal or whole percentage points must be consistent per column and documented in `derived_metrics`.

---

#### **Table semantics and calculation rules**

- Each table row represents a year using annual `10-K` data by default.
- If the newest year has no annual `10-K`, the frontend may show the latest `10-Q` as a clearly labeled provisional current-year row.
- Backend calculations must use consistent units within each formula and must not mix absolute values with compact display units.
- Multi-year calculations must use the historical series available for that company and must record the lookback window actually used (for example 3-year OE average, up-to-7-year OE YoY median, 3-year payout average, EPS CAGR start/end years).
- Metrics that require missing market inputs (spot price, shares, market cap), dividend data, buyback data, pledge data, debt maturity data, or other SEC gaps must return structured `missing_inputs` diagnostics instead of fabricated values.

**Acceptance Criteria:**

- The Python engine implements a dedicated derived-metrics module that implements **the formulas in this story card verbatim** (including defaults, clamps, inapplicable cases, and `missing_inputs` rules) and calculates values per annual reporting year after base SEC facts are parsed.
- The new derived metrics are stored under clear **English** keys inside `financial_metrics.derived_metrics` without mutating `base_metrics`; each multi-year or valuation result includes **lookback metadata** and **parameter disclosure** where applicable.
- Go Gateway continues to read financial history only through sqlc-generated queries and returns the expanded `derived_metrics` JSONB without hand-written row scanning.
- The frontend financial table displays yearly rows with grouped columns for valuation, shareholder returns, quality/risk, and pricing power, aligned to the metric names implied above.
- The table shows readable formatting for large money values, percentages, multiples, and unavailable metrics.
- The frontend must surface missing-input states such as `Market data required`, `Dividend data unavailable`, or `SEC fact unavailable` rather than showing misleading zeros.
- Unit tests cover core formulas (OE-DCF, Munger three-band exits, EPS CAGR percent-point storage, PEG/PEGY denominator conventions, shareholder-return chain, tax and approximate ROIC), missing-input behavior, default parameter disclosure, and year-by-year calculation alignment.
- Browser E2E verifies a real ticker sync and confirms that the frontend table visibly renders derived metric columns for multiple historical years.

---

**User Story 8: Derived Metrics Data Completeness + Metric Glossary**

**Role:** Fundamental Analyst / Frontend User  
**Requirement:** I want the yearly derived-metrics table to maximize SEC-computable coverage and provide a bottom-page glossary that explains each metric's meaning and calculation formula.  
**Reason:** So I can distinguish true data unavailability from mapping/calculation gaps and understand the analytical intent of each displayed column.

**Scope & Boundaries:**

- **In-Scope:** E2E-driven missing-data diagnosis, parser tag coverage fixes for SEC-available inputs, derived-metric readiness fixes, and frontend glossary rendering sourced from the same metric schema used by the table.
- **Out-of-Scope:** Introducing a new third-party market data provider in this card; market-dependent metrics may remain unavailable with explicit missing-input diagnostics.

**Acceptance Criteria:**

- A Playwright E2E run against the local running stack captures current missing-cell states and classifies each as expected (market-input missing) vs unexpected (SEC-computable but unavailable).
- For SEC-computable metrics, parser mappings and derived calculations are corrected so affected columns resolve to `ready` wherever required filing inputs exist.
- For truly unavailable inputs, backend payloads keep structured `missing_inputs` reasons and frontend keeps explicit non-zero placeholders (`Market data required`, `Dividend data unavailable`, `SEC fact unavailable`).
- The dashboard renders a bottom glossary section that lists each derived table metric with:
  - metric name
  - plain-language meaning
  - formula used
  - missing/inapplicable display rule
- Glossary definitions are driven from a single frontend schema source shared with column definitions to avoid drift between table headers and documentation.
- Unit tests cover glossary rendering and at least one representative missing-state mapping path; E2E confirms glossary visibility and grouped table integrity.

---

**User Story 9: SEC Base-Fact Mapping Completeness for AAPL and COST**

**Role:** Fundamental Analyst / Data Quality Owner  
**Requirement:** I want the SEC parser and annual derived-metrics pipeline to treat obvious blank cells in `AAPL` and `COST` as a base-fact coverage defect first, expand the supported SEC tag candidates for those companies, and make the yearly table render fully populated for all SEC-computable columns on the page.  
**Reason:** So that the terminal reflects a trustworthy financial baseline for large-cap US issuers and does not present avoidable blanks on basic accounting fields because the fallback tag list is incomplete.

**PRD + Tech-Stack Alignment Constraints:**

- This card must stay inside the documented architecture: Next.js 15 frontend, Go Gin gateway, Python FastAPI analysis engine, and PostgreSQL JSONB pass-through.
- The remediation path must preserve the PRD rule that raw filing data is extracted from SEC EDGAR and persisted as normalized `base_metrics` plus separate `derived_metrics`; no frontend hardcoding or Go-side manual patching is allowed.
- This card must not introduce a third-party market-data dependency to satisfy table completeness. If a metric truly requires market inputs by formula, that metric remains explicitly missing and is not in scope for this card.
- The implementation must prefer richer SEC tag coverage, period-aligned parsing, and annual-filing correctness over display-only fallback behavior.

**Scope & Boundaries:**

- **In-Scope:** expanding SEC XBRL synonym coverage for already-modeled base facts, tightening period-aligned fact selection where basic values are being missed, repairing downstream SEC-computable yearly derived metrics that are blank only because upstream base facts were not captured, and verifying the result specifically on `AAPL` and `COST`.
- **Out-of-Scope:** adding new valuation formulas, changing the table layout, fabricating placeholder zeros, relaxing required-market-input rules, or backfilling unsupported metrics with non-SEC sources.

**Definition of “Basic Data” for This Card:**

- “Basic data” means metrics that should be obtainable directly from SEC filings for mature US issuers such as Apple and Costco, including but not limited to revenue, gross profit, cost of revenue, operating income, net income, operating cash flow, capex, depreciation and amortization, assets, liabilities, equity, debt structure, taxes, dividends, buybacks, share counts, and other already-modeled annual accounting facts.
- This card assumes that when one of these fields is blank for `AAPL` or `COST`, the first debugging hypothesis is incomplete SEC tag coverage or period matching, not true data absence.

**Acceptance Criteria:**

- A field-by-field audit is run against the live local yearly table for `AAPL` and `COST`, and every blank or unavailable cell is classified into one of only two buckets:
  - `SEC-computable and must be fixed in this card`
  - `Formula requires non-SEC market inputs and may remain explicitly unavailable`
- For both `AAPL` and `COST`, all table cells driven by SEC-computable inputs must render a non-empty value on the page after a fresh sync, rather than `SEC fact unavailable`, `Dividend data unavailable`, or an empty-looking placeholder.
- The parser fallback list for already-supported canonical fields is expanded wherever `AAPL` or `COST` disclose the fact under a different valid SEC taxonomy tag than the current candidate set covers.
- Period alignment must be verified so the engine does not miss a basic annual fact merely because the chosen anchor period is stricter than the companyfacts payload requires for that issuer’s filing pattern.
- Any yearly derived metric that is currently blank only because one upstream SEC-computable base fact was missed must become `ready` once the base fact mapping is repaired.
- Metrics that still require market inputs by design, such as `PE`, `PEG`, yield metrics tied to `spot_price`, or other explicitly market-derived outputs, must continue to return structured missing diagnostics and are not counted as defects for this card.
- Verification for this card must use both:
  - direct API inspection of `GET /api/v1/financials/AAPL` and `GET /api/v1/financials/COST`
  - browser verification on `http://localhost:3000` after a fresh sync for both tickers
- Regression coverage must include parser and/or sync tests that lock in the newly supported SEC tags or period-selection behavior for the repaired facts, so `AAPL` and `COST` do not regress on future refactors.

**Implementation Notes:**

- Treat `AAPL` and `COST` as must-pass sample companies for completeness, not as one-off exceptions; any added mapping should improve the general parser vocabulary for other US issuers where possible.
- Prefer canonical parser improvements in the Python engine over page-level presentation workarounds.
- Keep the current JSONB contract intact so the Go Gateway remains a pass-through reader and the frontend continues to consume the existing financial payload shape.

---

**User Story 10: AAPL and COST Zero-Blank Table Completion**

**Role:** Product Owner / Fundamental Analyst  
**Requirement:** I want the yearly table on `localhost:3000` to show a visible value in every rendered cell for `AAPL` and `COST`, and I want this card to be the final acceptance gate for those two sample companies.  
**Reason:** So that the product can be judged against a concrete user-facing standard instead of a partially complete backend-coverage standard, and so backlog ownership is unambiguous for the “no blanks on the table” outcome.

**Relationship to Existing Cards:**

- This card is the user-facing completion card for `AAPL` and `COST`.
- Story 8 remains the general SEC-computable completeness and glossary card.
- Story 9 remains the parser/base-fact remediation card for SEC mapping gaps.
- A blank table cell for `AAPL` or `COST` is not considered fully resolved until this card passes, even if Story 8 or Story 9 are individually marked complete.

**PRD + Tech-Stack Alignment Constraints:**

- The solution must remain within the documented architecture: Next.js 15 frontend, Go Gin gateway, Python FastAPI engine, and PostgreSQL JSONB storage/query flow.
- The card may be satisfied by one or both of the following implementation paths, as long as the final page shows no blank cells for `AAPL` and `COST`:
  - expanding SEC-based parsing/calculation coverage for values that should come from EDGAR filings
  - adding an explicitly approved market-data enrichment path for metrics whose formulas require price, yield, or market-cap inputs
- No frontend hardcoded per-company literals are allowed.
- Any new enrichment source must still persist normalized data through the existing backend pipeline instead of bypassing Go/Python/DB contracts.

**Scope & Boundaries:**

- **In-Scope:** any backend or data-pipeline work needed to make every rendered yearly table cell for `AAPL` and `COST` display a value, including SEC tag coverage expansion, period-selection fixes, derived-metric dependency repairs, and market-data enrichment where the formula inherently requires market inputs.
- **Out-of-Scope:** weakening formulas to force fake values, hiding columns only for these tickers, or inserting manual one-off values outside the normal data flow.

**Acceptance Criteria:**

- After a fresh sync and page load for `AAPL`, every rendered cell in the yearly table shows a visible value; no cell may display as blank, `SEC fact unavailable`, `Dividend data unavailable`, `Market data required`, or any equivalent missing-state placeholder.
- After a fresh sync and page load for `COST`, every rendered cell in the yearly table shows a visible value; no cell may display as blank, `SEC fact unavailable`, `Dividend data unavailable`, `Market data required`, or any equivalent missing-state placeholder.
- If a displayed metric depends on market inputs by formula, this card requires the system to source and persist those inputs through the normal backend pipeline so the final cell still resolves to a value.
- If a displayed metric depends only on SEC filing data, this card requires the parser/calculation path to be repaired so the final cell resolves to a value whenever the issuer disclosed the necessary facts.
- Verification must be performed at the actual product surface, not API-only:
  - browser verification on `http://localhost:3000` for `AAPL`
  - browser verification on `http://localhost:3000` for `COST`
  - screenshot or equivalent evidence showing the full table state for both sample tickers
- Supporting regression coverage must be added so future changes cannot reintroduce blank or placeholder cells for `AAPL` and `COST`.

**Implementation Notes:**

- This card intentionally resolves the ambiguity between “maximize SEC-computable coverage” and “make the user-facing table fully populated.”
- Story 8 and Story 9 may each deliver part of the solution, but this card is the single source of truth for the final user-visible acceptance outcome.

**Concrete Repair Plan:**

- **Workstream 1: Close remaining SEC parser coverage gaps**
  - Audit the canonical parser fallback lists in `services/python-engine/app/parsers/financial_metric_parser.py` against the live `AAPL` and `COST` filing payloads.
  - Expand candidate tag coverage for still-blank annual accounting facts, prioritizing debt maturity, interest expense, dividend, goodwill, and other already-modeled inputs that are present in EDGAR but not consistently matched by the current fallback list.
  - Add regression tests that lock in each newly supported synonym or anchor-period behavior using mocked company-facts samples derived from `AAPL` and `COST` disclosure patterns.

- **Workstream 2: Repair annual derived metrics blocked only by upstream fact misses**
  - Re-run yearly derived calculations after parser fixes and identify which cells remain unresolved only because one upstream SEC-computable base fact was previously missing.
  - Patch the corresponding formulas or dependency wiring in `services/python-engine/app/calculations/derived_metrics.py` so those metrics resolve to `ready` once the required SEC base fact is present.
  - Explicitly verify yearly ROIC, tax, dividend, buyback, goodwill/equity, and pricing-power columns for `AAPL` and `COST` after each parser enhancement pass.

- **Workstream 3: Implement market-data enrichment for formula-required columns**
  - Fill the current market-data hole that leaves `pe_ratio`, `earnings_yield_percent`, `peg_ratio`, `pegy_ratio`, `dividend_yield_percent`, `net_buyback_yield_percent`, and `total_shareholder_yield_percent` unresolved when `spot_price` or `market_cap` is absent.
  - Route those inputs through the Python engine sync flow so yearly derived metrics are computed from persisted backend data rather than from frontend-only lookups or hardcoded values.
  - Add regression tests covering positive-EPS PE/PEG/PEGY paths, unavailable market-input handling, and at least one fully populated annual row for both `AAPL` and `COST`.

- **Workstream 4: Improve page-level observability for final triage**
  - Keep the table contract intact, but make the browser/debug workflow capable of distinguishing `missing` vs `not_applicable` vs market-input dependency during final verification.
  - Ensure QA can map any remaining visible placeholder back to the underlying `missing_inputs` or `reason` without manual database inspection.
  - Preserve the user-facing table design while adding enough diagnostics in tests, screenshots, or debug surfaces to prevent repeated blind triage loops.

- **Workstream 5: End-to-end acceptance run for the two must-pass companies**
  - Run a fresh sync for `AAPL`, reload the dashboard, and verify that every rendered yearly table cell shows a concrete value.
  - Run a fresh sync for `COST`, reload the dashboard, and verify that every rendered yearly table cell shows a concrete value.
  - Capture browser evidence and corresponding API snapshots for both companies, and do not mark this card complete until the browser table is zero-blank for both tickers at the same time.

**Known Code Areas Still Not Covered Yet (must be addressed by this card):**

- `services/python-engine/app/parsers/financial_metric_parser.py`
  - Remaining fallback coverage still needs to be validated company-by-company for `AAPL` and `COST`, even after recent tag additions.
- `services/python-engine/app/calculations/derived_metrics.py`
  - The market-dependent branch still leaves PE / PEG / PEGY / yield metrics unresolved whenever `spot_price` or `market_cap` is absent.
- `services/python-engine/app/main.py`
  - The sync pipeline must be part of the final verification loop because parser fixes and market-data enrichment only matter if fresh syncs persist the repaired rows.
- `apps/web/lib/financials.ts`
  - Final acceptance still needs a stronger debug/verification path because the table currently compresses many backend reasons into generic placeholder labels.
