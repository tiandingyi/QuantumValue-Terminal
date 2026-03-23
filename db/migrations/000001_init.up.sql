CREATE TABLE IF NOT EXISTS sync_status (
    ticker TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS filings (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    filing_date DATE NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    ticker TEXT PRIMARY KEY,
    metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_filings_ticker_date
    ON filings (ticker, filing_date DESC);

CREATE INDEX IF NOT EXISTS idx_financial_metrics_gin
    ON financial_metrics
    USING GIN (metrics);
