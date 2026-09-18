package main

import (
	"log/slog"
	"os"

	"github.com/brunoavila55/tucano/internal/platform/config"
	"github.com/hibiken/asynq"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	cfg, err := config.Load()
	if err != nil {
		logger.Error("invalid configuration", "error", err)
		os.Exit(1)
	}

	redisOptions, err := asynq.ParseRedisURI(cfg.RedisURL)
	if err != nil {
		logger.Error("invalid redis configuration", "error", err)
		os.Exit(1)
	}

	server := asynq.NewServer(redisOptions, asynq.Config{
		Concurrency: 10,
		Logger:      asynqLogger{logger: logger},
	})

	mux := asynq.NewServeMux()
	logger.Info("worker started", "environment", cfg.Environment)
	if err := server.Run(mux); err != nil {
		logger.Error("worker stopped", "error", err)
		os.Exit(1)
	}
}

type asynqLogger struct{ logger *slog.Logger }

func (l asynqLogger) Debug(args ...interface{}) { l.logger.Debug("asynq", "details", args) }
func (l asynqLogger) Info(args ...interface{})  { l.logger.Info("asynq", "details", args) }
func (l asynqLogger) Warn(args ...interface{})  { l.logger.Warn("asynq", "details", args) }
func (l asynqLogger) Error(args ...interface{}) { l.logger.Error("asynq", "details", args) }
func (l asynqLogger) Fatal(args ...interface{}) { l.logger.Error("asynq fatal", "details", args) }
