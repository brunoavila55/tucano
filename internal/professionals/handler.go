package professionals

import (
	"errors"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"log/slog"
	"net"
	"net/http"
	"strconv"
	"strings"

	"github.com/brunoavila55/tucano/internal/accounts"
	"github.com/brunoavila55/tucano/internal/platform/httpserver"
	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

type Handler struct {
	service *Service
	logger  *slog.Logger
}

func RegisterRoutes(router chi.Router, auth *accounts.Service, service *Service, logger *slog.Logger) {
	handler := &Handler{service: service, logger: logger}
	router.Get("/categories", handler.categories)
	router.Get("/uploads/{storageKey}", handler.upload)

	router.Route("/professional", func(r chi.Router) {
		r.Use(accounts.Authenticate(auth))
		r.Use(accounts.RequireRole(auth, accounts.RoleProfessional))
		r.Get("/dashboard", func(w http.ResponseWriter, _ *http.Request) {
			httpserver.WriteJSON(w, http.StatusOK, map[string]string{"profile": accounts.RoleProfessional})
		})
		r.Get("/profile", handler.profile)
		r.Put("/profile", handler.updateProfile)
		r.Post("/portfolio", handler.addPortfolioItem)
		r.Delete("/portfolio/{itemID}", handler.deletePortfolioItem)
	})

	router.With(accounts.Authenticate(auth), accounts.RequireRole(auth, accounts.RoleClient)).Get("/professionals/search", handler.search)
}

func (h *Handler) categories(w http.ResponseWriter, r *http.Request) {
	categories, err := h.service.Categories(r.Context())
	if err != nil {
		h.writeError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, map[string]any{"categories": categories})
}

func (h *Handler) profile(w http.ResponseWriter, r *http.Request) {
	userID, _ := accounts.UserIDFromContext(r.Context())
	profile, err := h.service.GetProfile(r.Context(), userID)
	if err != nil {
		h.writeError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, map[string]any{"profile": profile})
}

func (h *Handler) updateProfile(w http.ResponseWriter, r *http.Request) {
	var input ProfileInput
	if err := httpserver.DecodeJSON(w, r, &input); err != nil {
		httpserver.WriteError(w, http.StatusBadRequest, "invalid_json", "Envie um JSON válido somente com os campos esperados.")
		return
	}
	userID, _ := accounts.UserIDFromContext(r.Context())
	profile, err := h.service.UpdateProfile(r.Context(), userID, input, requestAuditContext(r))
	if err != nil {
		h.writeError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, map[string]any{"profile": profile})
}

func (h *Handler) addPortfolioItem(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxUploadBytes+(1<<20))
	if err := r.ParseMultipartForm(maxUploadBytes + (1 << 20)); err != nil {
		httpserver.WriteError(w, http.StatusRequestEntityTooLarge, "file_too_large", "A imagem deve ter no máximo 5 MB.")
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "file_required", "Escolha uma imagem para o portfólio.")
		return
	}
	defer func() {
		if err := file.Close(); err != nil {
			h.logger.Warn("portfolio upload close failed", "error", err)
		}
	}()
	_, format, err := image.DecodeConfig(file)
	if err != nil {
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "invalid_file", "O arquivo não é uma imagem JPEG ou PNG válida.")
		return
	}
	if _, err := file.Seek(0, 0); err != nil {
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "invalid_file", "Não foi possível processar a imagem.")
		return
	}
	mediaType := map[string]string{"jpeg": "image/jpeg", "png": "image/png"}[format]
	userID, _ := accounts.UserIDFromContext(r.Context())
	item, err := h.service.AddPortfolioItem(r.Context(), userID, header.Filename, mediaType, header.Size, file, requestAuditContext(r))
	if err != nil {
		h.writeError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusCreated, map[string]any{"item": item})
}

func (h *Handler) deletePortfolioItem(w http.ResponseWriter, r *http.Request) {
	itemID, err := uuid.Parse(chi.URLParam(r, "itemID"))
	if err != nil {
		httpserver.WriteError(w, http.StatusNotFound, "portfolio_item_not_found", "Item do portfólio não encontrado.")
		return
	}
	userID, _ := accounts.UserIDFromContext(r.Context())
	if err := h.service.DeletePortfolioItem(r.Context(), userID, itemID, requestAuditContext(r)); err != nil {
		h.writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) search(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	categoryID, categoryErr := uuid.Parse(query.Get("category_id"))
	latitude, latitudeErr := strconv.ParseFloat(query.Get("latitude"), 64)
	longitude, longitudeErr := strconv.ParseFloat(query.Get("longitude"), 64)
	radius, radiusErr := int32Query(query.Get("radius_km"), 25)
	page, pageErr := int32Query(query.Get("page"), 1)
	pageSize, pageSizeErr := int32Query(query.Get("page_size"), 20)
	availableNow, availableErr := booleanQuery(query.Get("available_now"), false)
	if categoryErr != nil || latitudeErr != nil || longitudeErr != nil || radiusErr != nil || pageErr != nil || pageSizeErr != nil || availableErr != nil {
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "invalid_search", "Revise categoria, localização, raio e paginação da busca.")
		return
	}
	result, err := h.service.Search(r.Context(), SearchInput{
		CategoryID: categoryID, Latitude: latitude, Longitude: longitude, RadiusKm: radius,
		AvailableNowOnly: availableNow, Page: page, PageSize: pageSize,
	})
	if err != nil {
		h.writeError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, result)
}

func (h *Handler) upload(w http.ResponseWriter, r *http.Request) {
	path, valid := h.service.UploadPath(chi.URLParam(r, "storageKey"))
	if !valid {
		httpserver.WriteError(w, http.StatusNotFound, "file_not_found", "Arquivo não encontrado.")
		return
	}
	w.Header().Set("Cache-Control", "public, max-age=86400")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	http.ServeFile(w, r, path)
}

func (h *Handler) writeError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, ErrInvalidInput):
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "invalid_professional_profile", "Revise os dados do perfil, localização e disponibilidade.")
	case errors.Is(err, ErrCategoryNotFound):
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "category_not_available", "Escolha uma categoria disponível no catálogo.")
	case errors.Is(err, ErrLocationRequired):
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "location_required", "Informe sua localização para configurar a região atendida.")
	case errors.Is(err, ErrUnsupportedMedia):
		httpserver.WriteError(w, http.StatusUnsupportedMediaType, "unsupported_media", "Envie uma imagem JPEG ou PNG.")
	case errors.Is(err, ErrPortfolioFull):
		httpserver.WriteError(w, http.StatusConflict, "portfolio_limit_reached", fmt.Sprintf("O portfólio aceita até %d imagens nesta fase.", maxPortfolioItems))
	case errors.Is(err, ErrPortfolioNotFound):
		httpserver.WriteError(w, http.StatusNotFound, "portfolio_item_not_found", "Item do portfólio não encontrado.")
	default:
		h.logger.Error("professional request failed", "error", err)
		httpserver.WriteError(w, http.StatusInternalServerError, "internal_error", "Não foi possível concluir a solicitação.")
	}
}

func int32Query(value string, fallback int32) (int32, error) {
	if strings.TrimSpace(value) == "" {
		return fallback, nil
	}
	parsed, err := strconv.ParseInt(value, 10, 32)
	// #nosec G115 -- ParseInt with bitSize 32 guarantees the conversion range.
	return int32(parsed), err
}

func booleanQuery(value string, fallback bool) (bool, error) {
	if strings.TrimSpace(value) == "" {
		return fallback, nil
	}
	return strconv.ParseBool(value)
}

func requestAuditContext(r *http.Request) AuditContext {
	ip := strings.TrimSpace(r.RemoteAddr)
	if host, _, err := net.SplitHostPort(ip); err == nil {
		ip = host
	}
	return AuditContext{IPAddress: ip, UserAgent: r.UserAgent()}
}
