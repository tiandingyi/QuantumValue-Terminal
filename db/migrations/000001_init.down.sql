DROP INDEX IF EXISTS idx_sync_status_company_task;
DROP INDEX IF EXISTS idx_financial_metrics_gin;
DROP INDEX IF EXISTS idx_filings_company_filed_at;
DROP INDEX IF EXISTS idx_companies_is_active;

DROP TABLE IF EXISTS sync_status;
DROP TABLE IF EXISTS financial_metrics;
DROP TABLE IF EXISTS filings;
DROP TABLE IF EXISTS companies;
