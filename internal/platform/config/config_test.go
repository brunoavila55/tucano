package config

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestLoadRequiresDatabaseURL(t *testing.T) {
	t.Setenv("DATABASE_URL", "")
	_, err := Load()
	require.ErrorContains(t, err, "DATABASE_URL")
}

func TestLoadUsesSafeDefaults(t *testing.T) {
	t.Setenv("DATABASE_URL", "postgres://example")
	t.Setenv("ALLOWED_ORIGINS", "https://tucano.example, https://app.tucano.example")

	cfg, err := Load()
	require.NoError(t, err)
	require.Equal(t, "development", cfg.Environment)
	require.Equal(t, "8080", cfg.Port)
	require.Equal(t, "http://localhost:8080", cfg.AppOrigin)
	require.Equal(t, []string{"https://tucano.example", "https://app.tucano.example"}, cfg.AllowedOrigins)
}

func TestLoadRejectsDevelopmentSecretInProduction(t *testing.T) {
	t.Setenv("DATABASE_URL", "postgres://example")
	t.Setenv("APP_ENV", "production")
	t.Setenv("JWT_SECRET", "development-only-secret-change-me")
	_, err := Load()
	require.ErrorContains(t, err, "JWT_SECRET")
}

func TestLoadRequiresSMTPInProduction(t *testing.T) {
	t.Setenv("DATABASE_URL", "postgres://example")
	t.Setenv("APP_ENV", "production")
	t.Setenv("JWT_SECRET", "production-secret-with-at-least-32-chars")
	t.Setenv("SMTP_HOST", "")
	_, err := Load()
	require.ErrorContains(t, err, "SMTP_HOST")
}
