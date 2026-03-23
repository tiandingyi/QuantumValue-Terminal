package main

import "testing"

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
