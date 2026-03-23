# QuantumValue Terminal

QuantumValue Terminal is a documentation-first monorepo for a long-horizon fundamental analysis platform built on SEC EDGAR data.

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
   `cp .env.example .env`
2. Start the stack:
   `docker compose up --build`
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

## Current Layout

- `apps/web`: Next.js 15 App Router frontend migrated from the staged dashboard template
- `design/frontend-template`: untouched raw HTML reference and staging area
- `services/go-gateway`: minimal Gin API gateway with health and handshake endpoints
- `services/python-engine`: minimal FastAPI engine service for local orchestration
- `db/migrations`: SQL migration source of truth for the local Postgres stack
- `infra`: future local environment and deployment scaffolding
