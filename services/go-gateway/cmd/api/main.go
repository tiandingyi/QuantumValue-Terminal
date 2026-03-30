package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
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
	router := setupRouter(engineBaseURL)

	log.Printf("api-go listening on :%s", port)
	if err := router.Run(":" + port); err != nil {
		log.Fatal(err)
	}
}

func setupRouter(engineBaseURL string) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)

	router := gin.New()
	router.Use(gin.Logger(), gin.Recovery(), corsMiddleware())

	router.GET("/healthz", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "api-go",
			"status":  "ok",
			"engine":  engineBaseURL,
		})
	})

	router.GET("/api/v1/handshake", func(c *gin.Context) {
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

		c.JSON(http.StatusOK, handshakeResponse{
			Status:    overall,
			Timestamp: time.Now().UTC().Format(time.RFC3339),
			Services:  statuses,
		})
	})

	router.POST("/api/v1/sync/:ticker", func(c *gin.Context) {
		ticker := c.Param("ticker")
		if !isValidTicker(ticker) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ticker"})
			return
		}

		statusCode, payload, err := proxyEngineRequest(c.Request.Context(), http.MethodPost, engineBaseURL+"/sync/"+strings.ToUpper(ticker), nil)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{
				"status":  "ERROR",
				"message": "Python engine is unavailable.",
			})
			return
		}

		c.Data(statusCode, "application/json", payload)
	})

	router.GET("/api/v1/status/:ticker", func(c *gin.Context) {
		ticker := c.Param("ticker")
		if !isValidTicker(ticker) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ticker"})
			return
		}

		statusCode, payload, err := proxyEngineRequest(c.Request.Context(), http.MethodGet, engineBaseURL+"/status/"+strings.ToUpper(ticker), nil)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{
				"status":  "ERROR",
				"message": "Unable to read sync status from the Python engine.",
			})
			return
		}

		c.Data(statusCode, "application/json", payload)
	})

	return router
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin != "" && isAllowedOrigin(origin) {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Vary", "Origin")
		}
		c.Header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Accept")

		if c.Request.Method == http.MethodOptions {
			c.Status(http.StatusNoContent)
			c.Abort()
			return
		}

		c.Next()
	}
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
