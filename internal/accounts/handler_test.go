package accounts

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestRequireTrustedOrigin(t *testing.T) {
	handler := NewHandler(nil, disabledMailer{}, slog.New(slog.NewTextHandler(io.Discard, nil)), "development", []string{"https://tucano.example"})
	next := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusNoContent) })

	tests := []struct {
		name   string
		origin string
		status int
	}{
		{name: "trusted browser origin", origin: "https://tucano.example", status: http.StatusNoContent},
		{name: "non browser client without origin", status: http.StatusNoContent},
		{name: "untrusted browser origin", origin: "https://attacker.example", status: http.StatusForbidden},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
			request.Header.Set("Origin", test.origin)
			response := httptest.NewRecorder()

			handler.requireTrustedOrigin(next).ServeHTTP(response, request)

			require.Equal(t, test.status, response.Code)
		})
	}
}

type disabledMailer struct{}

func (disabledMailer) Enabled() bool                          { return false }
func (disabledMailer) SendVerification(string, string) error  { return nil }
func (disabledMailer) SendPasswordReset(string, string) error { return nil }
