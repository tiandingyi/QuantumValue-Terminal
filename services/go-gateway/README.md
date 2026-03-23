# Go Gateway

This service now contains the minimal Gin-based API gateway for local Docker orchestration.

Current endpoints:

- `GET /healthz`
- `GET /api/v1/handshake`
- `POST /api/v1/sync/:ticker`
- `GET /api/v1/status/:ticker`
