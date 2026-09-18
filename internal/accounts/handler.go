package accounts

import (
	"errors"
	"log/slog"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/brunoavila55/tucano/internal/platform/httpserver"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/httprate"
	"github.com/go-playground/validator/v10"
)

const refreshCookieName = "tucano_refresh"

type Handler struct {
	service        *Service
	mailer         Mailer
	logger         *slog.Logger
	validate       *validator.Validate
	development    bool
	secureCookie   bool
	allowedOrigins map[string]struct{}
}

type registerRequest struct {
	Email       string `json:"email" validate:"required,email,max=254"`
	Password    string `json:"password" validate:"required,min=12,max=128"`
	DisplayName string `json:"display_name" validate:"required,min=2,max=100"`
	ProfileType string `json:"profile_type" validate:"required,oneof=professional client"`
	CompanyName string `json:"company_name" validate:"max=150"`
}

type loginRequest struct {
	Email    string `json:"email" validate:"required,email,max=254"`
	Password string `json:"password" validate:"required,max=128"`
}

type emailRequest struct {
	Email string `json:"email" validate:"required,email,max=254"`
}

type tokenRequest struct {
	Token string `json:"token" validate:"required,max=256"`
}

type resetPasswordRequest struct {
	Token    string `json:"token" validate:"required,max=256"`
	Password string `json:"password" validate:"required,min=12,max=128"`
}

type profileRequest struct {
	ProfileType string `json:"profile_type" validate:"required,oneof=professional client"`
	CompanyName string `json:"company_name" validate:"max=150"`
}

type actionResponse struct {
	Message                string    `json:"message"`
	User                   *UserView `json:"user,omitempty"`
	DevelopmentActionToken string    `json:"development_action_token,omitempty"`
}

func NewHandler(service *Service, mailer Mailer, logger *slog.Logger, environment string, allowedOrigins []string) *Handler {
	handler := &Handler{
		service: service, mailer: mailer, logger: logger, validate: validator.New(validator.WithRequiredStructEnabled()),
		development: environment == "development", secureCookie: environment != "development", allowedOrigins: make(map[string]struct{}, len(allowedOrigins)),
	}
	for _, origin := range allowedOrigins {
		handler.allowedOrigins[origin] = struct{}{}
	}
	return handler
}

func (h *Handler) Routes(router chi.Router) {
	router.Route("/auth", func(r chi.Router) {
		strict := httprate.LimitByIP(10, time.Minute)
		r.With(strict).Post("/register", h.register)
		r.With(strict).Post("/login", h.login)
		r.With(h.requireTrustedOrigin).Post("/refresh", h.refresh)
		r.With(h.requireTrustedOrigin).Post("/logout", h.logout)
		r.With(strict).Post("/verify-email", h.verifyEmail)
		r.With(strict).Post("/resend-verification", h.resendVerification)
		r.With(strict).Post("/forgot-password", h.forgotPassword)
		r.With(strict).Post("/reset-password", h.resetPassword)
	})

	router.Route("/account", func(r chi.Router) {
		r.Use(Authenticate(h.service))
		r.Get("/me", h.me)
		r.Post("/profiles", h.addProfile)
	})
}

func (h *Handler) register(w http.ResponseWriter, r *http.Request) {
	var request registerRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	view, token, err := h.service.Register(r.Context(), RegisterInput(request), auditContext(r))
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	response := actionResponse{Message: "Cadastro criado. Verifique seu e-mail para entrar.", User: &view}
	if h.mailer.Enabled() {
		if err := h.mailer.SendVerification(view.Email, token); err != nil {
			h.logger.Error("verification email delivery failed", "error", err)
			httpserver.WriteError(w, http.StatusServiceUnavailable, "email_delivery_unavailable", "Cadastro criado, mas não foi possível enviar o e-mail. Tente reenviar em instantes.")
			return
		}
	} else if h.development {
		response.DevelopmentActionToken = token
	}
	httpserver.WriteJSON(w, http.StatusCreated, response)
}

func (h *Handler) login(w http.ResponseWriter, r *http.Request) {
	var request loginRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	session, err := h.service.Login(r.Context(), request.Email, request.Password, auditContext(r))
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	h.setRefreshCookie(w, session.RefreshToken, session.RefreshExpiresAt)
	httpserver.WriteJSON(w, http.StatusOK, session)
}

func (h *Handler) refresh(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(refreshCookieName)
	if err != nil {
		h.clearRefreshCookie(w)
		httpserver.WriteError(w, http.StatusUnauthorized, "invalid_refresh_token", "Sua sessão expirou. Entre novamente.")
		return
	}
	session, err := h.service.Refresh(r.Context(), cookie.Value)
	if err != nil {
		h.clearRefreshCookie(w)
		h.writeServiceError(w, err)
		return
	}
	h.setRefreshCookie(w, session.RefreshToken, session.RefreshExpiresAt)
	httpserver.WriteJSON(w, http.StatusOK, session)
}

func (h *Handler) logout(w http.ResponseWriter, r *http.Request) {
	cookie, _ := r.Cookie(refreshCookieName)
	if cookie != nil {
		if err := h.service.Logout(r.Context(), cookie.Value, auditContext(r)); err != nil {
			h.logger.Error("logout token revocation failed", "error", err)
		}
	}
	h.clearRefreshCookie(w)
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) verifyEmail(w http.ResponseWriter, r *http.Request) {
	var request tokenRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	if err := h.service.VerifyEmail(r.Context(), request.Token, auditContext(r)); err != nil {
		h.writeServiceError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, actionResponse{Message: "E-mail confirmado. Você já pode entrar."})
}

func (h *Handler) resendVerification(w http.ResponseWriter, r *http.Request) {
	var request emailRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	email, token, err := h.service.ResendVerification(r.Context(), request.Email)
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	response := actionResponse{Message: genericEmailMessage}
	responseForDevelopment(&response, token, h.development)
	h.deliverAction(func() error {
		if email == "" || !h.mailer.Enabled() {
			return nil
		}
		return h.mailer.SendVerification(email, token)
	})
	httpserver.WriteJSON(w, http.StatusAccepted, response)
}

func (h *Handler) forgotPassword(w http.ResponseWriter, r *http.Request) {
	var request emailRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	email, token, err := h.service.RequestPasswordReset(r.Context(), request.Email, auditContext(r))
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	response := actionResponse{Message: genericEmailMessage}
	responseForDevelopment(&response, token, h.development)
	h.deliverAction(func() error {
		if email == "" || !h.mailer.Enabled() {
			return nil
		}
		return h.mailer.SendPasswordReset(email, token)
	})
	httpserver.WriteJSON(w, http.StatusAccepted, response)
}

func (h *Handler) resetPassword(w http.ResponseWriter, r *http.Request) {
	var request resetPasswordRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	if err := h.service.ResetPassword(r.Context(), request.Token, request.Password, auditContext(r)); err != nil {
		h.writeServiceError(w, err)
		return
	}
	h.clearRefreshCookie(w)
	httpserver.WriteJSON(w, http.StatusOK, actionResponse{Message: "Senha redefinida. Entre novamente com sua nova senha."})
}

func (h *Handler) me(w http.ResponseWriter, r *http.Request) {
	userID, _ := UserIDFromContext(r.Context())
	view, err := h.service.Me(r.Context(), userID)
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusOK, map[string]any{"user": view})
}

func (h *Handler) addProfile(w http.ResponseWriter, r *http.Request) {
	var request profileRequest
	if !h.decodeAndValidate(w, r, &request) {
		return
	}
	userID, _ := UserIDFromContext(r.Context())
	view, err := h.service.AddProfile(r.Context(), userID, request.ProfileType, request.CompanyName, auditContext(r))
	if err != nil {
		h.writeServiceError(w, err)
		return
	}
	httpserver.WriteJSON(w, http.StatusCreated, map[string]any{"user": view})
}

func (h *Handler) decodeAndValidate(w http.ResponseWriter, r *http.Request, target any) bool {
	if err := httpserver.DecodeJSON(w, r, target); err != nil {
		httpserver.WriteError(w, http.StatusBadRequest, "invalid_json", "Envie um JSON válido somente com os campos esperados.")
		return false
	}
	if err := h.validate.Struct(target); err != nil {
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "validation_error", validationMessage(err))
		return false
	}
	return true
}

func (h *Handler) writeServiceError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, ErrConflict):
		httpserver.WriteError(w, http.StatusConflict, "email_already_registered", "Já existe uma conta com este e-mail.")
	case errors.Is(err, ErrInvalidCredentials):
		httpserver.WriteError(w, http.StatusUnauthorized, "invalid_credentials", "E-mail ou senha inválidos.")
	case errors.Is(err, ErrEmailNotVerified):
		httpserver.WriteError(w, http.StatusForbidden, "email_not_verified", "Confirme seu e-mail antes de entrar.")
	case errors.Is(err, ErrInvalidToken):
		httpserver.WriteError(w, http.StatusUnauthorized, "invalid_or_expired_token", "Este link ou sessão é inválido ou expirou.")
	case errors.Is(err, ErrInactiveAccount):
		httpserver.WriteError(w, http.StatusForbidden, "inactive_account", "Esta conta não está disponível.")
	case errors.Is(err, ErrProfileExists):
		httpserver.WriteError(w, http.StatusConflict, "profile_already_exists", "Sua conta já possui esse perfil.")
	case strings.Contains(err.Error(), "senha deve"):
		httpserver.WriteError(w, http.StatusUnprocessableEntity, "invalid_password", err.Error())
	default:
		h.logger.Error("account request failed", "error", err)
		httpserver.WriteError(w, http.StatusInternalServerError, "internal_error", "Não foi possível concluir a solicitação.")
	}
}

func (h *Handler) setRefreshCookie(w http.ResponseWriter, token string, expiresAt time.Time) {
	http.SetCookie(w, &http.Cookie{
		Name: refreshCookieName, Value: token, Path: "/api/auth", Expires: expiresAt,
		MaxAge: int(time.Until(expiresAt).Seconds()), HttpOnly: true, Secure: h.secureCookie, SameSite: http.SameSiteStrictMode,
	})
}

func (h *Handler) clearRefreshCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name: refreshCookieName, Value: "", Path: "/api/auth", MaxAge: -1,
		Expires: time.Unix(1, 0), HttpOnly: true, Secure: h.secureCookie, SameSite: http.SameSiteStrictMode,
	})
}

func (h *Handler) deliverAction(delivery func() error) {
	if err := delivery(); err != nil {
		h.logger.Error("account email delivery failed", "error", err)
	}
}

func (h *Handler) requireTrustedOrigin(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := strings.TrimSpace(r.Header.Get("Origin"))
		if origin != "" {
			if _, allowed := h.allowedOrigins[origin]; !allowed {
				httpserver.WriteError(w, http.StatusForbidden, "untrusted_origin", "Origem da solicitação não autorizada.")
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

func responseForDevelopment(response *actionResponse, token string, development bool) {
	if development && token != "" {
		response.DevelopmentActionToken = token
	}
}

func validationMessage(err error) string {
	var validationErrors validator.ValidationErrors
	if !errors.As(err, &validationErrors) || len(validationErrors) == 0 {
		return "Revise os dados informados."
	}
	switch validationErrors[0].Field() {
	case "Email":
		return "Informe um e-mail válido."
	case "Password":
		return "A senha deve ter entre 12 e 128 caracteres."
	case "DisplayName":
		return "Informe um nome entre 2 e 100 caracteres."
	case "ProfileType":
		return "Escolha perfil profissional ou contratante."
	case "CompanyName":
		return "O nome da empresa deve ter no máximo 150 caracteres."
	default:
		return "Revise os dados informados."
	}
}

func auditContext(r *http.Request) AuditContext {
	ip := strings.TrimSpace(r.RemoteAddr)
	if host, _, err := net.SplitHostPort(ip); err == nil {
		ip = host
	}
	return AuditContext{IPAddress: ip, UserAgent: r.UserAgent()}
}

const genericEmailMessage = "Se existir uma conta elegível, enviaremos as instruções por e-mail."
