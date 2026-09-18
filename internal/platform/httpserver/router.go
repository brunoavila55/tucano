package httpserver

import (
	"context"
	"log/slog"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/go-chi/httprate"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

const APIVersion = "0.3.0"

type Dependencies struct {
	Logger         *slog.Logger
	Database       *pgxpool.Pool
	Redis          *redis.Client
	AllowedOrigins []string
	RegisterRoutes func(chi.Router)
}

type healthResponse struct {
	Status   string            `json:"status"`
	Service  string            `json:"service"`
	Version  string            `json:"version"`
	Checks   map[string]string `json:"checks"`
	DateTime time.Time         `json:"date_time"`
}

func New(deps Dependencies) http.Handler {
	router := chi.NewRouter()
	router.Use(middleware.RequestID)
	router.Use(middleware.RealIP)
	router.Use(requestLogger(deps.Logger))
	router.Use(middleware.Recoverer)
	router.Use(middleware.Timeout(20 * time.Second))
	router.Use(httprate.LimitByIP(120, time.Minute))
	router.Use(cors.Handler(cors.Options{
		AllowedOrigins:   deps.AllowedOrigins,
		AllowedMethods:   []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete, http.MethodOptions},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"},
		ExposedHeaders:   []string{"X-Request-ID"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	router.Get("/health", healthHandler(deps))
	if deps.RegisterRoutes != nil {
		deps.RegisterRoutes(router)
	}
	router.NotFound(func(w http.ResponseWriter, _ *http.Request) {
		WriteError(w, http.StatusNotFound, "not_found", "Recurso não encontrado.")
	})
	router.MethodNotAllowed(func(w http.ResponseWriter, _ *http.Request) {
		WriteError(w, http.StatusMethodNotAllowed, "method_not_allowed", "Método não permitido.")
	})
	return router
}

// healthHandler godoc
// @Summary Verifica a saúde da API
// @Description Confirma conectividade com PostgreSQL e Redis.
// @Tags system
// @Produce json
// @Success 200 {object} healthResponse
// @Failure 503 {object} errorBody
// @Router /health [get]
func healthHandler(deps Dependencies) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		checks := map[string]string{"postgres": "ok", "redis": "ok"}
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()

		if deps.Database == nil || deps.Database.Ping(ctx) != nil {
			checks["postgres"] = "unavailable"
		}
		if deps.Redis == nil || deps.Redis.Ping(ctx).Err() != nil {
			checks["redis"] = "unavailable"
		}
		if checks["postgres"] != "ok" || checks["redis"] != "ok" {
			WriteJSON(w, http.StatusServiceUnavailable, healthResponse{
				Status: "degraded", Service: "tucano-api", Version: APIVersion, Checks: checks, DateTime: time.Now().UTC(),
			})
			return
		}

		WriteJSON(w, http.StatusOK, healthResponse{
			Status: "ok", Service: "tucano-api", Version: APIVersion, Checks: checks, DateTime: time.Now().UTC(),
		})
	}
}

func requestLogger(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			wrapper := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
			next.ServeHTTP(wrapper, r)
			logger.Info("request completed",
				"request_id", middleware.GetReqID(r.Context()),
				"method", r.Method,
				"path", r.URL.Path,
				"status", wrapper.Status(),
				"duration_ms", time.Since(start).Milliseconds(),
			)
		})
	}
}
