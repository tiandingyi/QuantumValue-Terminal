-- name: ListFinancialMetricSnapshots :many
SELECT
    c.ticker,
    c.cik,
    c.name AS company_name,
    f.form_type,
    f.period_end_date,
    f.filed_at,
    f.accession_number,
    fm.base_metrics,
    fm.derived_metrics,
    fm.updated_at
FROM companies AS c
JOIN filings AS f ON f.company_id = c.id
JOIN financial_metrics AS fm ON fm.filing_id = f.id
WHERE UPPER(c.ticker) = UPPER(sqlc.arg(ticker)::text)
ORDER BY f.period_end_date DESC, f.filed_at DESC
LIMIT 80;

-- name: GetSecSyncStatus :one
SELECT
    c.ticker,
    ss.status,
    ss.last_error,
    ss.updated_at
FROM companies AS c
JOIN sync_status AS ss ON ss.company_id = c.id
WHERE UPPER(c.ticker) = UPPER(sqlc.arg(ticker)::text)
  AND ss.task_type = 'SEC_SYNC'
LIMIT 1;
