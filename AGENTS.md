# IMPORTANT:
# Always read memory-bank/PRD.md before writing any code.
# Always read memory-bank/tech-stack.md before writing any code.
# If a database schema file exists, read it before changing persistence logic.
# After adding a major feature or completing a milestone, update memory-bank/progress.md.

# Repository Guidelines

## Project Structure & Module Organization
This repository is currently documentation-first. The active planning files are:
- `README.md`: lightweight project entry point.
- `AGENTS.md`: repository-specific instructions for coding agents.
- `memory-bank/PRD.md`: product and architecture blueprint.
- `memory-bank/tech-stack.md`: approved stack and deployment direction.
- `memory-bank/implementation-plan.md`: current execution plan.
- `memory-bank/progress.md`: milestone and delivery log.

As implementation begins, follow the architecture in `memory-bank/PRD.md` and keep a clean monorepo shape:
- `apps/web` for Next.js 15 UI.
- `services/go-gateway` for Gin API.
- `services/python-engine` for FastAPI ingestion/sync.
- `db/migrations` for SQL migrations and schema evolution.
- `infra/` for `docker-compose` and environment templates.
- `design/frontend-template/` for raw imported HTML, screenshots, and reference assets before they are migrated into `apps/web`.

## Build, Test, and Development Commands
Tooling target is **pnpm workspaces + Turborepo** with service-local commands, but that workspace has not been bootstrapped yet.
- Once the monorepo is initialized, use `pnpm install` to install workspace dependencies.
- Once Turborepo is configured, use `pnpm turbo run dev` to start local dev services.
- Once Turborepo is configured, use `pnpm turbo run build` to build all packages/apps.
- Once tests exist, use `pnpm turbo run test` to run the workspace test suites.
- Once infra exists, use `docker compose up -d` to start local parity services.
- Once migrations exist, use `migrate -path db/migrations -database "$DATABASE_URL" up` to apply schema changes.

## Coding Style & Naming Conventions
- Use 2 spaces for frontend (`ts/tsx/css`) and 4 spaces for Python; run `gofmt` for Go.
- Naming:
  - React components: `PascalCase` (`FinancialMatrix.tsx`).
  - TS/JS/Python files: `kebab-case` for routes, `snake_case` for Python modules.
  - Go packages: short, lowercase names.
- Prefer small modules with explicit boundaries between `web`, `go-gateway`, and `python-engine`.

## Testing Guidelines
- Frontend: colocate tests as `*.test.ts(x)`.
- Go: use `*_test.go` in the same package.
- Python: use `tests/test_*.py`.
- Add tests for new behavior and bug fixes; prioritize API contracts, parsing/validation logic, and migration safety.
- Run the relevant test commands before opening a PR. Use `pnpm turbo run test` after the workspace is initialized.

## Commit & Pull Request Guidelines
Git history is minimal (`first commit`), so adopt Conventional Commits now:
- `feat: add SEC sync status endpoint`
- `fix: handle empty filing payload`
- `docs: clarify local setup`

PRs should include:
- Clear scope and rationale.
- Linked issue/task.
- Test evidence (command + result summary).
- Screenshots or terminal logs for UI/API behavior changes.

## Security & Configuration Tips
- Never commit secrets; keep local values in `.env.local`/`.env` and provide `.env.example`.
- Treat migrations as the single source of truth for schema changes.
- Validate external SEC payloads before persistence.
