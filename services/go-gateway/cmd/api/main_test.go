package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

type fakeFinancialsStore struct {
	financials    financialsResponse
	financialsErr error
	status        gatewaySyncResponse
	statusErr     error
}

func (store fakeFinancialsStore) GetFinancials(ctx context.Context, ticker string) (financialsResponse, error) {
	return store.financials, store.financialsErr
}

func (store fakeFinancialsStore) GetSyncStatus(ctx context.Context, ticker string) (gatewaySyncResponse, error) {
	return store.status, store.statusErr
}

func (store fakeFinancialsStore) Close() error {
	return nil
}

func TestIsValidTicker(t *testing.T) {
	// Keep ticker validation tight because both sync and polling routes depend on it.
	validTickers := []string{"AAPL", "BRK.B", "0700.HK", "MSFT"}
	invalidTickers := []string{"", "BAD TICKER", "###", "ticker-with-way-too-many-characters"}

	for _, ticker := range validTickers {
		if !isValidTicker(ticker) {
			t.Fatalf("expected ticker %q to be valid", ticker)
		}
	}

	for _, ticker := range invalidTickers {
		if isValidTicker(ticker) {
			t.Fatalf("expected ticker %q to be invalid", ticker)
		}
	}
}

func TestHealthzReturnsConfiguredEngine(t *testing.T) {
	router := setupRouter("http://engine.test")
	request := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, response.Code)
	}

	var payload map[string]string
	if err := json.Unmarshal(response.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected valid json response: %v", err)
	}

	if payload["engine"] != "http://engine.test" {
		t.Fatalf("expected engine base url to be returned, got %q", payload["engine"])
	}
}

func TestCorsPreflightReturnsNoContent(t *testing.T) {
	// Confirm the shared CORS configuration still handles browser preflight requests.
	router := setupRouter("http://engine.test")
	request := httptest.NewRequest(http.MethodOptions, "/api/v1/handshake", nil)
	request.Header.Set("Origin", "http://localhost:3000")
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("expected status %d, got %d", http.StatusNoContent, response.Code)
	}

	if response.Header().Get("Access-Control-Allow-Origin") != "http://localhost:3000" {
		t.Fatalf("expected allowed origin header to be echoed")
	}
}

func TestSyncRejectsInvalidTicker(t *testing.T) {
	router := setupRouter("http://engine.test")
	request := httptest.NewRequest(http.MethodPost, "/api/v1/sync/###", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d", http.StatusBadRequest, response.Code)
	}
}

func TestFinancialsReturnsCachedJSONBPayload(t *testing.T) {
	router := setupRouterWithStore("http://engine.test", fakeFinancialsStore{
		financials: financialsResponse{
			Ticker:    "AAPL",
			CIK:       "0000320193",
			Company:   "Apple Inc.",
			Status:    "ready",
			UpdatedAt: "2026-04-13T00:00:00Z",
			Filings: []filingSnapshot{
				{
					FormType:        "10-K",
					PeriodEndDate:   "2025-09-27",
					FiledAt:         "2025-10-31",
					AccessionNumber: "0000320193-25-000079",
					BaseMetrics:     json.RawMessage(`{"revenue":391035000000}`),
					DerivedMetrics:  json.RawMessage(`{"gross_margin":{"value":0.46}}`),
					UpdatedAt:       "2026-04-13T00:00:00Z",
				},
			},
		},
	})
	request := httptest.NewRequest(http.MethodGet, "/api/v1/financials/aapl", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("expected status %d, got %d", http.StatusOK, response.Code)
	}

	var payload financialsResponse
	if err := json.Unmarshal(response.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected valid json response: %v", err)
	}
	if payload.Ticker != "AAPL" {
		t.Fatalf("expected AAPL payload, got %q", payload.Ticker)
	}
	if string(payload.Filings[0].BaseMetrics) != `{"revenue":391035000000}` {
		t.Fatalf("expected base metrics JSONB to pass through, got %s", payload.Filings[0].BaseMetrics)
	}
}

func TestFinancialsRejectsInvalidTicker(t *testing.T) {
	router := setupRouterWithStore("http://engine.test", fakeFinancialsStore{})
	request := httptest.NewRequest(http.MethodGet, "/api/v1/financials/###", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest {
		t.Fatalf("expected status %d, got %d", http.StatusBadRequest, response.Code)
	}
}

func TestFinancialsDatabaseErrorReturnsServiceUnavailable(t *testing.T) {
	router := setupRouterWithStore("http://engine.test", fakeFinancialsStore{
		financialsErr: errors.New("database unavailable"),
	})
	request := httptest.NewRequest(http.MethodGet, "/api/v1/financials/AAPL", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusServiceUnavailable {
		t.Fatalf("expected status %d, got %d", http.StatusServiceUnavailable, response.Code)
	}
}

func TestFinancialsCacheMissTriggersEngineSync(t *testing.T) {
	originalProxy := proxyEngineRequestFunc
	t.Cleanup(func() {
		proxyEngineRequestFunc = originalProxy
	})
	proxyEngineRequestFunc = func(ctx context.Context, method, url string, body []byte) (int, []byte, error) {
		if method != http.MethodPost || url != "http://engine.test/sync/AAPL" {
			t.Fatalf("expected POST http://engine.test/sync/AAPL, got %s %s", method, url)
		}
		return http.StatusAccepted, []byte(`{"ticker":"AAPL","status":"IN_PROGRESS","message":"Mining data.","updated_at":"2026-04-13T00:00:00Z"}`), nil
	}

	router := setupRouterWithStore("http://engine.test", fakeFinancialsStore{
		financialsErr: errFinancialsNotFound,
	})
	request := httptest.NewRequest(http.MethodGet, "/api/v1/financials/AAPL", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusAccepted {
		t.Fatalf("expected status %d, got %d", http.StatusAccepted, response.Code)
	}

	var payload gatewaySyncResponse
	if err := json.Unmarshal(response.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected valid json response: %v", err)
	}
	if payload.Status != "IN_PROGRESS" {
		t.Fatalf("expected cache miss to trigger engine sync, got %q", payload.Status)
	}
}

func TestStatusUsesDatabaseWhenAvailable(t *testing.T) {
	router := setupRouterWithStore("http://engine.test", fakeFinancialsStore{
		status: gatewaySyncResponse{
			Ticker:    "AAPL",
			Status:    "IN_PROGRESS",
			Message:   "Mining data from SEC EDGAR.",
			UpdatedAt: "2026-04-13T00:00:00Z",
		},
	})
	request := httptest.NewRequest(http.MethodGet, "/api/v1/status/aapl", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	if response.Code != http.StatusAccepted {
		t.Fatalf("expected status %d, got %d", http.StatusAccepted, response.Code)
	}

	var payload gatewaySyncResponse
	if err := json.Unmarshal(response.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected valid json response: %v", err)
	}
	if payload.Status != "IN_PROGRESS" {
		t.Fatalf("expected database status to be returned, got %q", payload.Status)
	}
}
