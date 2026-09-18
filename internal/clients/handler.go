package clients

import (
	"net/http"

	"github.com/brunoavila55/tucano/internal/accounts"
	"github.com/brunoavila55/tucano/internal/platform/httpserver"
	"github.com/go-chi/chi/v5"
)

func RegisterRoutes(router chi.Router, auth *accounts.Service) {
	router.Route("/client", func(r chi.Router) {
		r.Use(accounts.Authenticate(auth))
		r.Use(accounts.RequireRole(auth, accounts.RoleClient))
		r.Get("/dashboard", func(w http.ResponseWriter, _ *http.Request) {
			httpserver.WriteJSON(w, http.StatusOK, map[string]string{"profile": accounts.RoleClient})
		})
	})
}
