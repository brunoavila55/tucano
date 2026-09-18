package config

import (
	"errors"
	"fmt"
	"os"
	"strings"
)

type SMTPConfig struct {
	Host     string
	Port     string
	Username string
	Password string
	From     string
}

func (c SMTPConfig) Enabled() bool { return c.Host != "" }

type Config struct {
	Environment    string
	Port           string
	AppOrigin      string
	DatabaseURL    string
	RedisURL       string
	JWTSecret      string
	UploadDir      string
	AllowedOrigins []string
	SMTP           SMTPConfig
}

func Load() (Config, error) {
	cfg := Config{
		Environment:    valueOrDefault("APP_ENV", "development"),
		Port:           valueOrDefault("API_PORT", "8080"),
		AppOrigin:      strings.TrimRight(valueOrDefault("APP_ORIGIN", "http://localhost:8080"), "/"),
		DatabaseURL:    os.Getenv("DATABASE_URL"),
		RedisURL:       valueOrDefault("REDIS_URL", "redis://localhost:6379/0"),
		JWTSecret:      valueOrDefault("JWT_SECRET", "development-only-secret-change-me"),
		UploadDir:      valueOrDefault("UPLOAD_DIR", "/data/uploads"),
		AllowedOrigins: splitCSV(valueOrDefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080")),
		SMTP: SMTPConfig{
			Host: os.Getenv("SMTP_HOST"), Port: valueOrDefault("SMTP_PORT", "587"),
			Username: os.Getenv("SMTP_USERNAME"), Password: os.Getenv("SMTP_PASSWORD"),
			From: os.Getenv("SMTP_FROM"),
		},
	}

	if cfg.DatabaseURL == "" {
		return Config{}, errors.New("DATABASE_URL is required")
	}
	if len(cfg.JWTSecret) < 32 {
		return Config{}, errors.New("JWT_SECRET must contain at least 32 characters")
	}
	if cfg.Environment != "development" && cfg.JWTSecret == "development-only-secret-change-me" {
		return Config{}, errors.New("JWT_SECRET must be changed outside development")
	}
	if cfg.Environment != "development" && !cfg.SMTP.Enabled() {
		return Config{}, errors.New("SMTP_HOST is required outside development")
	}
	if cfg.SMTP.Enabled() && cfg.SMTP.From == "" {
		return Config{}, fmt.Errorf("SMTP_FROM is required when SMTP_HOST is configured")
	}
	return cfg, nil
}

func valueOrDefault(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func splitCSV(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}
