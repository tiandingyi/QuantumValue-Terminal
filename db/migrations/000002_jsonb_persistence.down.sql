ALTER TABLE sync_status
    DROP CONSTRAINT IF EXISTS sync_status_company_task_key;

DROP INDEX IF EXISTS idx_financial_metrics_derived_gin;
DROP INDEX IF EXISTS idx_financial_metrics_base_gin;

CREATE INDEX IF NOT EXISTS idx_financial_metrics_gin
    ON financial_metrics
    USING GIN (metrics);

ALTER TABLE financial_metrics
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS derived_metrics,
    DROP COLUMN IF EXISTS base_metrics;

ALTER TABLE filings
    DROP CONSTRAINT IF EXISTS filings_cik_form_period_key;

ALTER TABLE filings
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS accession_number,
    DROP COLUMN IF EXISTS period_end_date,
    DROP COLUMN IF EXISTS form_type,
    DROP COLUMN IF EXISTS cik;
