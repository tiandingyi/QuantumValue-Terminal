package main

import (
    "bytes"
    "encoding/json"
    "context"
    "io"
    "log"
    "net/http"
    "os"
    "regexp"
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

type syncResponse struct {
    Ticker    string `json:"ticker"`
    Status    string `json:"status"`
    Message   string `json:"message"`
    UpdatedAt string `json:"updated_at"`
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

    mux.HandleFunc("/api/v1/sync/", func(w http.ResponseWriter, r *http.Request) {
        withCORS(w, r)
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }
        if r.Method != http.MethodPost {
            writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
            return
        }

        ticker := strings.TrimPrefix(r.URL.Path, "/api/v1/sync/")
        if !isValidTicker(ticker) {
            writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid ticker"})
            return
        }

        statusCode, payload, err := proxyEngineRequest(r.Context(), http.MethodPost, engineBaseURL+"/sync/"+strings.ToUpper(ticker), nil)
        if err != nil {
            writeJSON(w, http.StatusBadGateway, map[string]string{
                "status":  "ERROR",
                "message": "Python engine is unavailable.",
            })
            return
        }

        writeRawJSON(w, statusCode, payload)
    })

    mux.HandleFunc("/api/v1/status/", func(w http.ResponseWriter, r *http.Request) {
        withCORS(w, r)
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }
        if r.Method != http.MethodGet {
            writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
            return
        }

        ticker := strings.TrimPrefix(r.URL.Path, "/api/v1/status/")
        if !isValidTicker(ticker) {
            writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid ticker"})
            return
        }

        statusCode, payload, err := proxyEngineRequest(r.Context(), http.MethodGet, engineBaseURL+"/status/"+strings.ToUpper(ticker), nil)
        if err != nil {
            writeJSON(w, http.StatusBadGateway, map[string]string{
                "status":  "ERROR",
                "message": "Unable to read sync status from the Python engine.",
            })
            return
        }

        writeRawJSON(w, statusCode, payload)
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

func proxyEngineRequest(ctx context.Context, method, url string, body []byte) (int, []byte, error) {
    requestBody := io.Reader(nil)
    if body != nil {
        requestBody = bytes.NewReader(body)
    }

    req, err := http.NewRequestWithContext(ctx, method, url, requestBody)
    if err != nil {
        return 0, nil, err
    }
    req.Header.Set("Content-Type", "application/json")

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return 0, nil, err
    }
    defer resp.Body.Close()

    payload, err := io.ReadAll(resp.Body)
    if err != nil {
        return 0, nil, err
    }

    if resp.StatusCode == http.StatusAccepted {
        var acceptedPayload struct {
            Detail syncResponse `json:"detail"`
        }
        if err := json.Unmarshal(payload, &acceptedPayload); err == nil && acceptedPayload.Detail.Ticker != "" {
            normalizedPayload, marshalErr := json.Marshal(acceptedPayload.Detail)
            if marshalErr == nil {
                return resp.StatusCode, normalizedPayload, nil
            }
        }
    }

    return resp.StatusCode, payload, nil
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(statusCode)
    if err := json.NewEncoder(w).Encode(payload); err != nil {
        log.Printf("json encode error: %v", err)
    }
}

func writeRawJSON(w http.ResponseWriter, statusCode int, payload []byte) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(statusCode)
    if _, err := w.Write(payload); err != nil {
        log.Printf("json write error: %v", err)
    }
}

func isValidTicker(ticker string) bool {
    normalizedTicker := strings.ToUpper(strings.TrimSpace(ticker))
    if normalizedTicker == "" {
        return false
    }
    pattern := regexp.MustCompile(`^[A-Z0-9.-]{1,15}$`)
    return pattern.MatchString(normalizedTicker)
}

func getEnv(key, fallback string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return fallback
}
