# Go Gateway

This service now contains the minimal Gin-based API gateway for local Docker orchestration.

Current endpoints:

- `GET /healthz`
- `GET /api/v1/handshake`
- `POST /api/v1/sync/:ticker`
- `GET /api/v1/status/:ticker`
- `GET /api/v1/financials/:ticker`

When `DATABASE_URL` is configured, the gateway reads cached SEC filing snapshots from PostgreSQL and returns JSONB `base_metrics` and `derived_metrics` through `GET /api/v1/financials/:ticker`. If no cached financials exist, the endpoint triggers the Python sync path and returns the mining response so callers can poll `GET /api/v1/status/:ticker`.

Database access is generated through sqlc:

- Query definitions live in `internal/db/queries/`.
- Generated Go code lives in `internal/db/sqlc/`.
- Regenerate after query or schema changes with `pnpm --filter api-go sqlc:generate`.
