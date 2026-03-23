package main

import (
    "encoding/json"
    "context"
    "log"
    "net/http"
    "os"
    "strings"
    "time"
)

type serviceStatus struct {
    Name      string `json:"name"`
    URL       string `json:"url"`
    Reachable bool   `json:"reachable"`
}

type handshakeResponse struct {
    Status    string          `json:"status"`
    Timestamp string          `json:"timestamp"`
    Services  []serviceStatus `json:"services"`
}

func main() {
    port := getEnv("PORT", "8080")
    engineBaseURL := getEnv("ENGINE_BASE_URL", "http://localhost:8000")
    mux := http.NewServeMux()

    mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        withCORS(w, r)
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }

        writeJSON(w, http.StatusOK, map[string]string{
            "service": "api-go",
            "status":  "ok",
            "engine":  engineBaseURL,
        })
    })

    mux.HandleFunc("/api/v1/handshake", func(w http.ResponseWriter, r *http.Request) {
        withCORS(w, r)
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }

        statuses := []serviceStatus{
            {
                Name:      "api-go",
                URL:       "self",
                Reachable: true,
            },
            {
                Name:      "engine-py",
                URL:       engineBaseURL,
                Reachable: ping(engineBaseURL + "/healthz"),
            },
        }

        overall := "ready"
        for _, status := range statuses {
            if !status.Reachable {
                overall = "degraded"
                break
            }
        }

        writeJSON(w, http.StatusOK, handshakeResponse{
            Status:    overall,
            Timestamp: time.Now().UTC().Format(time.RFC3339),
            Services:  statuses,
        })
    })

    log.Printf("api-go listening on :%s", port)
    if err := http.ListenAndServe(":"+port, mux); err != nil {
        log.Fatal(err)
    }
}

func withCORS(w http.ResponseWriter, r *http.Request) {
    origin := r.Header.Get("Origin")
    if origin != "" && isAllowedOrigin(origin) {
        w.Header().Set("Access-Control-Allow-Origin", origin)
        w.Header().Set("Vary", "Origin")
    }
    w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    w.Header().Set("Access-Control-Allow-Headers", "Origin, Content-Type, Accept")
}

func allowedOrigins() []string {
    origins := getEnv("ALLOWED_ORIGINS", "http://localhost:3000,http://web:3000")
    values := strings.Split(origins, ",")
    result := make([]string, 0, len(values))
    for _, value := range values {
        trimmed := strings.TrimSpace(value)
        if trimmed != "" {
            result = append(result, trimmed)
        }
    }
    return result
}

func isAllowedOrigin(origin string) bool {
    for _, allowedOrigin := range allowedOrigins() {
        if origin == allowedOrigin {
            return true
        }
    }
    return false
}

func ping(url string) bool {
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return false
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return false
    }
    defer resp.Body.Close()

    return resp.StatusCode >= 200 && resp.StatusCode < 300
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(statusCode)
    if err := json.NewEncoder(w).Encode(payload); err != nil {
        log.Printf("json encode error: %v", err)
    }
}

func getEnv(key, fallback string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return fallback
}
