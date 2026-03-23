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