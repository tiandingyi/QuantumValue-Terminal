# Python Engine

This service contains the FastAPI analysis engine used by the local Docker stack, including the first live SEC EDGAR integration.

Current endpoints:

- `GET /healthz`
- `POST /sync/{ticker}`
- `GET /status/{ticker}`

Current SEC behavior:

- `POST /sync/{ticker}` starts an asynchronous SEC fetch for ticker-to-CIK resolution plus `submissions` and `companyfacts`.
- `GET /status/{ticker}` returns `IN_PROGRESS`, `SUCCESS`, or `FAILED`, and successful responses include a latest `Assets` summary in `details`.

Proof-of-concept script:

- From `services/python-engine`, run `python3 scripts/sec_test.py`.
- The script uses the SEC-compliant `User-Agent` header, resolves `NVDA` to its padded 10-digit CIK, fetches both SEC JSON payloads, and prints the latest `Assets` value and end date.
