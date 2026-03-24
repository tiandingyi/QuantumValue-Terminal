package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type checkResult struct {
	ConnectedAt string `json:"connected_at"`
	Database    string `json:"database"`
	User        string `json:"user"`
}

func main() {
	databaseURL := firstNonEmpty("SUPABASE_DB_URL", "DATABASE_URL")
	if databaseURL == "" {
		log.Fatal("missing SUPABASE_DB_URL or DATABASE_URL")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		log.Fatalf("unable to create pgx pool: %v", err)
	}
	defer pool.Close()

	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("unable to ping database: %v", err)
	}

	var result checkResult
	result.ConnectedAt = time.Now().UTC().Format(time.RFC3339)

	if err := pool.QueryRow(ctx, "select current_database(), current_user").Scan(&result.Database, &result.User); err != nil {
		log.Fatalf("unable to fetch database metadata: %v", err)
	}

	payload, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		log.Fatalf("unable to encode result: %v", err)
	}

	fmt.Println(string(payload))
}

func firstNonEmpty(keys ...string) string {
	for _, key := range keys {
		if value := os.Getenv(key); value != "" {
			return value
		}
	}
	return ""
}
