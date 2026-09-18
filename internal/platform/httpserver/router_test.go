package httpserver

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestUnknownRouteUsesStandardErrorEnvelope(t *testing.T) {
	router := New(Dependencies{Logger: slog.New(slog.NewTextHandler(io.Discard, nil))})
	request := httptest.NewRequest(http.MethodGet, "/missing", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	require.Equal(t, http.StatusNotFound, response.Code)
	require.JSONEq(t, `{"error":{"code":"not_found","message":"Recurso não encontrado."}}`, response.Body.String())
}

func TestHealthReportsUnavailableDependencies(t *testing.T) {
	router := New(Dependencies{Logger: slog.New(slog.NewTextHandler(io.Discard, nil))})
	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	response := httptest.NewRecorder()

	router.ServeHTTP(response, request)

	require.Equal(t, http.StatusServiceUnavailable, response.Code)
	require.Contains(t, response.Body.String(), `"status":"degraded"`)
	require.Contains(t, response.Body.String(), `"postgres":"unavailable"`)
	require.Contains(t, response.Body.String(), `"version":"`+APIVersion+`"`)
}
