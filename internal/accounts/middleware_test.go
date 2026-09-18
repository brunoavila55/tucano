package accounts

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type fakeTokenParser struct {
	userID uuid.UUID
	err    error
}

func (p fakeTokenParser) ParseAccessToken(string) (uuid.UUID, error) { return p.userID, p.err }

type fakeRoleChecker struct{ roles map[uuid.UUID]map[string]bool }

func (c fakeRoleChecker) HasRole(_ context.Context, userID uuid.UUID, role string) (bool, error) {
	return c.roles[userID][role], nil
}

func TestRequireRoleRejectsTheOtherProfile(t *testing.T) {
	clientID := uuid.New()
	professionalID := uuid.New()
	checker := fakeRoleChecker{roles: map[uuid.UUID]map[string]bool{
		clientID:       {RoleClient: true},
		professionalID: {RoleProfessional: true},
	}}

	tests := []struct {
		name     string
		userID   uuid.UUID
		required string
		status   int
	}{
		{name: "client cannot enter professional route", userID: clientID, required: RoleProfessional, status: http.StatusForbidden},
		{name: "professional cannot enter client route", userID: professionalID, required: RoleClient, status: http.StatusForbidden},
		{name: "client enters client route", userID: clientID, required: RoleClient, status: http.StatusOK},
		{name: "professional enters professional route", userID: professionalID, required: RoleProfessional, status: http.StatusOK},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			handler := Authenticate(fakeTokenParser{userID: test.userID})(
				RequireRole(checker, test.required)(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
					w.WriteHeader(http.StatusOK)
				})),
			)
			request := httptest.NewRequest(http.MethodGet, "/protected", nil)
			request.Header.Set("Authorization", "Bearer valid-token")
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, request)
			require.Equal(t, test.status, response.Code)
		})
	}
}

func TestAuthenticateRejectsMissingAndInvalidTokens(t *testing.T) {
	next := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) })
	tests := []struct {
		name   string
		header string
		parser fakeTokenParser
	}{
		{name: "missing", parser: fakeTokenParser{}},
		{name: "invalid", header: "Bearer bad", parser: fakeTokenParser{err: errors.New("invalid")}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodGet, "/protected", nil)
			request.Header.Set("Authorization", test.header)
			response := httptest.NewRecorder()
			Authenticate(test.parser)(next).ServeHTTP(response, request)
			require.Equal(t, http.StatusUnauthorized, response.Code)
		})
	}
}
