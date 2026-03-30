package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestIsValidTicker(t *testing.T) {
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
