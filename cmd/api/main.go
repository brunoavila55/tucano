package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/brunoavila55/tucano/internal/accounts"
	"github.com/brunoavila55/tucano/internal/clients"
	"github.com/brunoavila55/tucano/internal/platform/config"
	"github.com/brunoavila55/tucano/internal/platform/database"
	"github.com/brunoavila55/tucano/internal/platform/httpserver"
	"github.com/brunoavila55/tucano/internal/professionals"
	"github.com/go-chi/chi/v5"
	"github.com/redis/go-redis/v9"
)

// @title Tucano API
// @version 0.3.0
// @description API do marketplace Tucano. A plataforma aproxima as partes e não processa o pagamento dos serviços.
// @BasePath /
func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	cfg, err := config.Load()
	if err != nil {
		logger.Error("invalid configuration", "error", err)
		os.Exit(1)
	}

	ctx := context.Background()
	pool, err := database.Open(ctx, cfg.DatabaseURL)
	if err != nil {
		logger.Error("database connection failed", "error", err)
		os.Exit(1)
	}
	defer pool.Close()

	redisOptions, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		logger.Error("invalid redis configuration", "error", err)
		os.Exit(1)
	}
	redisClient := redis.NewClient(redisOptions)
	defer func() {
		if err := redisClient.Close(); err != nil {
			logger.Error("redis connection close failed", "error", err)
		}
	}()
	authService, err := accounts.NewService(pool, cfg.JWTSecret)
	if err != nil {
		logger.Error("authentication initialization failed", "error", err)
		os.Exit(1)
	}
	accountHandler := accounts.NewHandler(authService, accounts.NewSMTPMailer(cfg.SMTP, cfg.AppOrigin), logger, cfg.Environment, cfg.AllowedOrigins)
	professionalService, err := professionals.NewService(pool, cfg.UploadDir, logger)
	if err != nil {
		logger.Error("professional service initialization failed", "error", err)
		os.Exit(1)
	}

	server := &http.Server{
		Addr: ":" + cfg.Port,
		Handler: httpserver.New(httpserver.Dependencies{
			Logger: logger, Database: pool, Redis: redisClient, AllowedOrigins: cfg.AllowedOrigins,
			RegisterRoutes: func(router chi.Router) {
				accountHandler.Routes(router)
				professionals.RegisterRoutes(router, authService, professionalService, logger)
				clients.RegisterRoutes(router, authService)
			},
		}),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	go func() {
		logger.Info("api listening", "port", cfg.Port, "environment", cfg.Environment)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("api stopped unexpectedly", "error", err)
			os.Exit(1)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		logger.Error("graceful shutdown failed", "error", err)
	}
}
