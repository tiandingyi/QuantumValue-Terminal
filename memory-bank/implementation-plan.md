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
