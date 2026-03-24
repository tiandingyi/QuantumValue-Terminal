CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(16) NOT NULL UNIQUE,
    cik CHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS filings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL,
    fiscal_year INT NOT NULL,
    period VARCHAR(16) NOT NULL,
    accession_num VARCHAR(32) NOT NULL UNIQUE,
    filed_at DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT filings_company_period_key UNIQUE (company_id, type, fiscal_year, period)
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL UNIQUE REFERENCES filings(id) ON DELETE CASCADE,
    metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_status (
    id BIGSERIAL PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    task_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_is_active
    ON companies (is_active);

CREATE INDEX IF NOT EXISTS idx_filings_company_filed_at
    ON filings (company_id, filed_at DESC);

CREATE INDEX IF NOT EXISTS idx_financial_metrics_gin
    ON financial_metrics
    USING GIN (metrics);

CREATE INDEX IF NOT EXISTS idx_sync_status_company_task
    ON sync_status (company_id, task_type, updated_at DESC);

COMMENT ON TABLE companies IS 'Master company registry for SEC-tracked issuers.';
COMMENT ON COLUMN companies.id IS 'Internal system identifier.';
COMMENT ON COLUMN companies.ticker IS 'Stock symbol used as the primary lookup handle (for example AAPL).';
COMMENT ON COLUMN companies.cik IS '10-digit SEC identifier that preserves leading zeros.';
COMMENT ON COLUMN companies.name IS 'Full legal name of the corporation.';
COMMENT ON COLUMN companies.sector IS 'Broad economic sector classification.';
COMMENT ON COLUMN companies.is_active IS 'True to enable automated background scraping for the company.';
COMMENT ON COLUMN companies.created_at IS 'Timestamp when the company row was created.';
COMMENT ON COLUMN companies.updated_at IS 'Timestamp when the company row was last updated.';

COMMENT ON TABLE filings IS 'Normalized SEC filing records associated with tracked companies.';
COMMENT ON COLUMN filings.id IS 'Unique filing document identifier.';
COMMENT ON COLUMN filings.company_id IS 'Reference to the parent company in the companies table.';
COMMENT ON COLUMN filings.type IS 'Report type such as 10-K or 10-Q.';
COMMENT ON COLUMN filings.fiscal_year IS 'Calendar year represented by the filing.';
COMMENT ON COLUMN filings.period IS 'Fiscal period label such as FY, Q1, or Q2.';
COMMENT ON COLUMN filings.accession_num IS 'SEC official receipt number used for deduplication.';
COMMENT ON COLUMN filings.filed_at IS 'Date the report was officially published.';
COMMENT ON COLUMN filings.created_at IS 'Timestamp when the filing row was ingested.';

COMMENT ON TABLE financial_metrics IS 'Structured financial payloads extracted from a single filing.';
COMMENT ON COLUMN financial_metrics.id IS 'Unique data record identifier.';
COMMENT ON COLUMN financial_metrics.filing_id IS 'Reference to filings, with exactly one metrics row per filing.';
COMMENT ON COLUMN financial_metrics.metrics IS 'JSONB super-dictionary containing parsed financial data such as revenue, EPS, assets, and liabilities.';
COMMENT ON COLUMN financial_metrics.created_at IS 'Timestamp when the metrics payload was ingested.';

COMMENT ON TABLE sync_status IS 'Sync tracking rows for scrape, parse, and persistence tasks.';
COMMENT ON COLUMN sync_status.id IS 'Auto-incrementing log identifier for sync tracking.';
COMMENT ON COLUMN sync_status.company_id IS 'Reference to the company currently being processed.';
COMMENT ON COLUMN sync_status.task_type IS 'Current sync task type such as SCRAPE, PARSE, or UPSERT.';
COMMENT ON COLUMN sync_status.status IS 'Task state such as PENDING, IN_PROGRESS, SUCCESS, or FAILED.';
COMMENT ON COLUMN sync_status.last_error IS 'Detailed error message or stack trace when a sync task fails.';
COMMENT ON COLUMN sync_status.created_at IS 'Timestamp when the sync status row was created.';
COMMENT ON COLUMN sync_status.updated_at IS 'Timestamp when the sync status row was last updated.';
