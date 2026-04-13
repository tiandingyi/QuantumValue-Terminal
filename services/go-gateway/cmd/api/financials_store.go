package main

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	dbsqlc "quantumvalue-terminal/services/go-gateway/internal/db/sqlc"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
)

var errFinancialsNotFound = errors.New("financials not found")
var errSyncStatusNotFound = errors.New("sync status not found")

type financialsStore interface {
	GetFinancials(ctx context.Context, ticker string) (financialsResponse, error)
	GetSyncStatus(ctx context.Context, ticker string) (gatewaySyncResponse, error)
	Close() error
}

type postgresFinancialsStore struct {
	pool    *pgxpool.Pool
	queries dbsqlc.Querier
}

type financialsResponse struct {
	Ticker    string           `json:"ticker"`
	CIK       string           `json:"cik"`
	Company   string           `json:"company"`
	Status    string           `json:"status"`
	UpdatedAt string           `json:"updated_at"`
	Filings   []filingSnapshot `json:"filings"`
}

type filingSnapshot struct {
	FormType        string          `json:"form_type"`
	PeriodEndDate   string          `json:"period_end_date"`
	FiledAt         string          `json:"filed_at"`
	AccessionNumber string          `json:"accession_number"`
	BaseMetrics     json.RawMessage `json:"base_metrics"`
	DerivedMetrics  json.RawMessage `json:"derived_metrics"`
	UpdatedAt       string          `json:"updated_at"`
}

type gatewaySyncResponse struct {
	Ticker    string          `json:"ticker"`
	Status    string          `json:"status"`
	Message   string          `json:"message"`
	UpdatedAt string          `json:"updated_at"`
	Details   json.RawMessage `json:"details,omitempty"`
}

func newPostgresFinancialsStore(databaseURL string) (*postgresFinancialsStore, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, err
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}

	return &postgresFinancialsStore{
		pool:    pool,
		queries: dbsqlc.New(pool),
	}, nil
}

func (store *postgresFinancialsStore) Close() error {
	store.pool.Close()
	return nil
}

func (store *postgresFinancialsStore) GetFinancials(ctx context.Context, ticker string) (financialsResponse, error) {
	rows, err := store.queries.ListFinancialMetricSnapshots(ctx, ticker)
	if err != nil {
		return financialsResponse{}, err
	}
	if len(rows) == 0 {
		return financialsResponse{}, errFinancialsNotFound
	}

	response := financialsResponse{
		Ticker:  rows[0].Ticker,
		CIK:     rows[0].Cik,
		Company: rows[0].CompanyName,
		Status:  "ready",
		Filings: make([]filingSnapshot, 0, len(rows)),
	}
	var latestUpdatedAt time.Time

	for _, row := range rows {
		response.Filings = append(response.Filings, filingSnapshot{
			FormType:        row.FormType,
			PeriodEndDate:   formatPGDate(row.PeriodEndDate),
			FiledAt:         formatPGDate(row.FiledAt),
			AccessionNumber: row.AccessionNumber,
			BaseMetrics:     row.BaseMetrics,
			DerivedMetrics:  row.DerivedMetrics,
			UpdatedAt:       formatPGTimestamp(row.UpdatedAt),
		})

		if row.UpdatedAt.Valid && row.UpdatedAt.Time.After(latestUpdatedAt) {
			latestUpdatedAt = row.UpdatedAt.Time
		}
	}
	response.UpdatedAt = latestUpdatedAt.UTC().Format(time.RFC3339)
	return response, nil
}

func (store *postgresFinancialsStore) GetSyncStatus(ctx context.Context, ticker string) (gatewaySyncResponse, error) {
	row, err := store.queries.GetSecSyncStatus(ctx, ticker)
	if errors.Is(err, pgx.ErrNoRows) {
		return gatewaySyncResponse{}, errSyncStatusNotFound
	}
	if err != nil {
		return gatewaySyncResponse{}, err
	}

	response := gatewaySyncResponse{
		Ticker:    row.Ticker,
		Status:    row.Status,
		UpdatedAt: formatPGTimestamp(row.UpdatedAt),
	}
	switch response.Status {
	case "SUCCESS":
		response.Message = "Financial DNA is ready."
	case "IN_PROGRESS", "PENDING":
		response.Message = "Mining data from SEC EDGAR."
	case "FAILURE", "FAILED":
		if row.LastError.Valid && row.LastError.String != "" {
			response.Message = row.LastError.String
		} else {
			response.Message = "Sync failed."
		}
	default:
		response.Message = "Sync status is available."
	}

	return response, nil
}

func formatPGDate(value pgtype.Date) string {
	if !value.Valid {
		return ""
	}
	return value.Time.Format("2006-01-02")
}

func formatPGTimestamp(value pgtype.Timestamptz) string {
	if !value.Valid {
		return ""
	}
	return value.Time.UTC().Format(time.RFC3339)
}
