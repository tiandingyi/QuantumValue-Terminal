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

## Current Layout

- `apps/web`: Next.js 15 App Router frontend migrated from the staged dashboard template
- `design/frontend-template`: untouched raw HTML reference and staging area
- `services/go-gateway`: placeholder directory for the Gin API gateway
- `services/python-engine`: placeholder directory for the FastAPI ingestion service
- `db/migrations`: future SQL migration source of truth
- `infra`: future local environment and deployment scaffolding
