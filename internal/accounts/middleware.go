package accounts

import (
	"context"
	"errors"
	"net/http"
	"strings"

	"github.com/brunoavila55/tucano/internal/platform/httpserver"
	"github.com/google/uuid"
)

type contextKey string

const userIDContextKey contextKey = "authenticated-user-id"

type AccessTokenParser interface {
	ParseAccessToken(raw string) (uuid.UUID, error)
}

type RoleChecker interface {
	HasRole(ctx context.Context, userID uuid.UUID, role string) (bool, error)
}

func Authenticate(parser AccessTokenParser) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			header := strings.TrimSpace(r.Header.Get("Authorization"))
			parts := strings.Fields(header)
			if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
				httpserver.WriteError(w, http.StatusUnauthorized, "authentication_required", "Faça login para continuar.")
				return
			}
			userID, err := parser.ParseAccessToken(parts[1])
			if err != nil {
				httpserver.WriteError(w, http.StatusUnauthorized, "invalid_access_token", "Sua sessão expirou. Entre novamente.")
				return
			}
			ctx := context.WithValue(r.Context(), userIDContextKey, userID)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func RequireRole(checker RoleChecker, role string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			userID, ok := UserIDFromContext(r.Context())
			if !ok {
				httpserver.WriteError(w, http.StatusUnauthorized, "authentication_required", "Faça login para continuar.")
				return
			}
			allowed, err := checker.HasRole(r.Context(), userID, role)
			if err != nil {
				httpserver.WriteError(w, http.StatusInternalServerError, "internal_error", "Não foi possível validar sua permissão.")
				return
			}
			if !allowed {
				httpserver.WriteError(w, http.StatusForbidden, "role_required", "Este acesso não está disponível para o perfil atual.")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func UserIDFromContext(ctx context.Context) (uuid.UUID, bool) {
	userID, ok := ctx.Value(userIDContextKey).(uuid.UUID)
	return userID, ok && userID != uuid.Nil
}

func IsAuthenticationError(err error) bool {
	return errors.Is(err, ErrInvalidCredentials) || errors.Is(err, ErrInvalidToken)
}
