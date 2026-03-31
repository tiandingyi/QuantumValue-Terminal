ALTER TABLE filings
    ADD COLUMN IF NOT EXISTS cik CHAR(10),
    ADD COLUMN IF NOT EXISTS form_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS period_end_date DATE,
    ADD COLUMN IF NOT EXISTS accession_number VARCHAR(32),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE filings AS f
SET
    cik = c.cik,
    form_type = f.type,
    period_end_date = COALESCE(f.period_end_date, f.filed_at),
    accession_number = f.accession_num,
    updated_at = NOW()
FROM companies AS c
WHERE c.id = f.company_id
  AND (f.cik IS NULL OR f.form_type IS NULL OR f.period_end_date IS NULL OR f.accession_number IS NULL);

ALTER TABLE filings
    ALTER COLUMN cik SET NOT NULL,
    ALTER COLUMN form_type SET NOT NULL,
    ALTER COLUMN period_end_date SET NOT NULL,
    ALTER COLUMN accession_number SET NOT NULL;

ALTER TABLE filings
    ADD CONSTRAINT filings_cik_form_period_key UNIQUE (cik, form_type, period_end_date);

ALTER TABLE financial_metrics
    ADD COLUMN IF NOT EXISTS base_metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS derived_metrics JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE financial_metrics
SET
    base_metrics = CASE
        WHEN metrics IS NULL THEN '{}'::JSONB
        ELSE metrics
    END,
    updated_at = NOW()
WHERE base_metrics = '{}'::JSONB;

DROP INDEX IF EXISTS idx_financial_metrics_gin;

CREATE INDEX IF NOT EXISTS idx_financial_metrics_base_gin
    ON financial_metrics
    USING GIN (base_metrics);

CREATE INDEX IF NOT EXISTS idx_financial_metrics_derived_gin
    ON financial_metrics
    USING GIN (derived_metrics);

ALTER TABLE sync_status
    ADD CONSTRAINT sync_status_company_task_key UNIQUE (company_id, task_type);

COMMENT ON COLUMN filings.cik IS '10-digit SEC identifier duplicated for direct filing upserts.';
COMMENT ON COLUMN filings.form_type IS 'Normalized SEC filing type such as 10-K or 10-Q.';
COMMENT ON COLUMN filings.period_end_date IS 'Reporting period end date used for filing-level idempotency.';
COMMENT ON COLUMN filings.accession_number IS 'SEC accession number preserved for traceability.';
COMMENT ON COLUMN filings.updated_at IS 'Timestamp when the filing registry row was last updated.';

COMMENT ON COLUMN financial_metrics.base_metrics IS 'Immutable standardized SEC base facts stored in wide-format JSONB.';
COMMENT ON COLUMN financial_metrics.derived_metrics IS 'Internal derived calculations stored separately from SEC source DNA.';
COMMENT ON COLUMN financial_metrics.updated_at IS 'Timestamp when the metrics payload was last updated.';
