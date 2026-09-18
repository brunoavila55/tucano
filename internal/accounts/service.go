package accounts

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	db "github.com/brunoavila55/tucano/internal/platform/database/sqlc"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
)

const (
	RoleProfessional = "professional"
	RoleClient       = "client"

	purposeVerifyEmail   = "verify_email"
	purposeResetPassword = "reset_password"
	refreshTokenTTL      = 30 * 24 * time.Hour
	verificationTokenTTL = 24 * time.Hour
	passwordResetTTL     = 30 * time.Minute
)

var (
	ErrConflict           = errors.New("resource already exists")
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrEmailNotVerified   = errors.New("email is not verified")
	ErrInvalidToken       = errors.New("invalid or expired token")
	ErrForbidden          = errors.New("forbidden")
	ErrInactiveAccount    = errors.New("account is not active")
	ErrProfileExists      = errors.New("profile already exists")
)

type Service struct {
	pool    *pgxpool.Pool
	queries *db.Queries
	tokens  *TokenManager
	now     func() time.Time
}

type AuditContext struct {
	IPAddress string
	UserAgent string
}

type RegisterInput struct {
	Email       string
	Password    string
	DisplayName string
	ProfileType string
	CompanyName string
}

type UserView struct {
	ID            uuid.UUID `json:"id"`
	Email         string    `json:"email"`
	DisplayName   string    `json:"display_name"`
	EmailVerified bool      `json:"email_verified"`
	Roles         []string  `json:"roles"`
}

type Session struct {
	AccessToken      string    `json:"access_token"`
	AccessExpiresAt  time.Time `json:"access_expires_at"`
	RefreshToken     string    `json:"-"`
	RefreshExpiresAt time.Time `json:"-"`
	User             UserView  `json:"user"`
}

func NewService(pool *pgxpool.Pool, secret string) (*Service, error) {
	tokens, err := NewTokenManager(secret)
	if err != nil {
		return nil, err
	}
	return &Service{pool: pool, queries: db.New(pool), tokens: tokens, now: time.Now}, nil
}

func (s *Service) Register(ctx context.Context, input RegisterInput, audit AuditContext) (UserView, string, error) {
	passwordHash, err := hashPassword(input.Password)
	if err != nil {
		return UserView{}, "", err
	}
	input.Email = normalizeEmail(input.Email)
	input.DisplayName = strings.TrimSpace(input.DisplayName)
	input.CompanyName = strings.TrimSpace(input.CompanyName)

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return UserView{}, "", fmt.Errorf("begin registration: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)
	user, err := queries.CreateUser(ctx, db.CreateUserParams{
		Email: input.Email, PasswordHash: passwordHash, DisplayName: input.DisplayName,
	})
	if err != nil {
		if isUniqueViolation(err) {
			return UserView{}, "", ErrConflict
		}
		return UserView{}, "", fmt.Errorf("create user: %w", err)
	}
	if err := createProfile(ctx, queries, user.ID, input.ProfileType, input.CompanyName); err != nil {
		return UserView{}, "", err
	}
	actionToken, err := s.issueActionToken(ctx, queries, user.ID, purposeVerifyEmail, verificationTokenTTL)
	if err != nil {
		return UserView{}, "", err
	}
	if err := recordAudit(ctx, queries, &user.ID, "account.registered", "user", &user.ID, map[string]any{"profile_type": input.ProfileType}, audit); err != nil {
		return UserView{}, "", err
	}
	if err := tx.Commit(ctx); err != nil {
		return UserView{}, "", fmt.Errorf("commit registration: %w", err)
	}
	view, err := s.userView(ctx, s.queries, user)
	return view, actionToken, err
}

func (s *Service) VerifyEmail(ctx context.Context, rawToken string, audit AuditContext) error {
	return s.consumeAction(ctx, rawToken, purposeVerifyEmail, audit, func(queries *db.Queries, userID uuid.UUID) error {
		if _, err := queries.MarkEmailVerified(ctx, userID); err != nil {
			return fmt.Errorf("mark email verified: %w", err)
		}
		return recordAudit(ctx, queries, &userID, "account.email_verified", "user", &userID, nil, audit)
	})
}

func (s *Service) Login(ctx context.Context, email, password string, audit AuditContext) (Session, error) {
	user, err := s.queries.GetUserByEmail(ctx, normalizeEmail(email))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			_ = comparePassword(dummyPasswordHash, password)
			return Session{}, ErrInvalidCredentials
		}
		return Session{}, fmt.Errorf("load login account: %w", err)
	}
	if !comparePassword(user.PasswordHash, password) {
		return Session{}, ErrInvalidCredentials
	}
	if user.Status != "active" {
		return Session{}, ErrInactiveAccount
	}
	if !user.EmailVerifiedAt.Valid {
		return Session{}, ErrEmailNotVerified
	}
	session, err := s.issueSession(ctx, s.queries, user)
	if err != nil {
		return Session{}, err
	}
	if err := recordAudit(ctx, s.queries, &user.ID, "account.logged_in", "user", &user.ID, nil, audit); err != nil {
		return Session{}, err
	}
	return session, nil
}

func (s *Service) Refresh(ctx context.Context, rawToken string) (Session, error) {
	if rawToken == "" {
		return Session{}, ErrInvalidToken
	}
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return Session{}, fmt.Errorf("begin refresh: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)
	userID, err := queries.ConsumeRefreshToken(ctx, hashOpaqueToken(rawToken))
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Session{}, ErrInvalidToken
		}
		return Session{}, fmt.Errorf("consume refresh token: %w", err)
	}
	user, err := queries.GetUserByID(ctx, userID)
	if err != nil || user.Status != "active" || !user.EmailVerifiedAt.Valid {
		return Session{}, ErrInvalidToken
	}
	session, err := s.issueSession(ctx, queries, user)
	if err != nil {
		return Session{}, err
	}
	if err := tx.Commit(ctx); err != nil {
		return Session{}, fmt.Errorf("commit refresh: %w", err)
	}
	return session, nil
}

func (s *Service) Logout(ctx context.Context, rawToken string, audit AuditContext) error {
	if rawToken == "" {
		return nil
	}
	hash := hashOpaqueToken(rawToken)
	userID, _ := s.queries.ConsumeRefreshToken(ctx, hash)
	if err := s.queries.RevokeRefreshToken(ctx, hash); err != nil {
		return fmt.Errorf("revoke refresh token: %w", err)
	}
	if userID != uuid.Nil {
		return recordAudit(ctx, s.queries, &userID, "account.logged_out", "user", &userID, nil, audit)
	}
	return nil
}

func (s *Service) RequestPasswordReset(ctx context.Context, email string, audit AuditContext) (string, string, error) {
	user, err := s.queries.GetUserByEmail(ctx, normalizeEmail(email))
	if errors.Is(err, pgx.ErrNoRows) || (err == nil && user.Status != "active") {
		return "", "", nil
	}
	if err != nil {
		return "", "", fmt.Errorf("load password reset account: %w", err)
	}
	token, err := s.issueActionToken(ctx, s.queries, user.ID, purposeResetPassword, passwordResetTTL)
	if err != nil {
		return "", "", err
	}
	if err := recordAudit(ctx, s.queries, &user.ID, "account.password_reset_requested", "user", &user.ID, nil, audit); err != nil {
		return "", "", err
	}
	return user.Email, token, nil
}

func (s *Service) ResetPassword(ctx context.Context, rawToken, password string, audit AuditContext) error {
	passwordHash, err := hashPassword(password)
	if err != nil {
		return err
	}
	return s.consumeAction(ctx, rawToken, purposeResetPassword, audit, func(queries *db.Queries, userID uuid.UUID) error {
		if err := queries.UpdateUserPassword(ctx, db.UpdateUserPasswordParams{ID: userID, PasswordHash: passwordHash}); err != nil {
			return fmt.Errorf("update password: %w", err)
		}
		if err := queries.RevokeAllUserRefreshTokens(ctx, userID); err != nil {
			return fmt.Errorf("revoke sessions: %w", err)
		}
		return recordAudit(ctx, queries, &userID, "account.password_reset", "user", &userID, nil, audit)
	})
}

func (s *Service) ResendVerification(ctx context.Context, email string) (string, string, error) {
	user, err := s.queries.GetUserByEmail(ctx, normalizeEmail(email))
	if errors.Is(err, pgx.ErrNoRows) || (err == nil && (user.EmailVerifiedAt.Valid || user.Status != "active")) {
		return "", "", nil
	}
	if err != nil {
		return "", "", fmt.Errorf("load verification account: %w", err)
	}
	token, err := s.issueActionToken(ctx, s.queries, user.ID, purposeVerifyEmail, verificationTokenTTL)
	return user.Email, token, err
}

func (s *Service) Me(ctx context.Context, userID uuid.UUID) (UserView, error) {
	user, err := s.queries.GetUserByID(ctx, userID)
	if err != nil {
		return UserView{}, err
	}
	if user.Status != "active" {
		return UserView{}, ErrInactiveAccount
	}
	return s.userView(ctx, s.queries, user)
}

func (s *Service) AddProfile(ctx context.Context, userID uuid.UUID, profileType, companyName string, audit AuditContext) (UserView, error) {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return UserView{}, fmt.Errorf("begin profile creation: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)

	err = createProfile(ctx, queries, userID, profileType, strings.TrimSpace(companyName))
	if err != nil {
		if isUniqueViolation(err) {
			return UserView{}, ErrProfileExists
		}
		return UserView{}, err
	}
	if err := recordAudit(ctx, queries, &userID, "account.profile_added", profileType+"_profile", nil, nil, audit); err != nil {
		return UserView{}, err
	}
	if err := tx.Commit(ctx); err != nil {
		return UserView{}, fmt.Errorf("commit profile creation: %w", err)
	}
	return s.Me(ctx, userID)
}

func (s *Service) HasRole(ctx context.Context, userID uuid.UUID, role string) (bool, error) {
	roles, err := s.queries.GetUserRoles(ctx, userID)
	if err != nil {
		return false, err
	}
	switch role {
	case RoleProfessional:
		return roles.IsProfessional, nil
	case RoleClient:
		return roles.IsClient, nil
	default:
		return false, nil
	}
}

func (s *Service) ParseAccessToken(raw string) (uuid.UUID, error) {
	return s.tokens.ParseAccessToken(raw)
}

func (s *Service) issueSession(ctx context.Context, queries *db.Queries, user db.User) (Session, error) {
	now := s.now().UTC()
	accessToken, accessExpiresAt, err := s.tokens.IssueAccessToken(user.ID, now)
	if err != nil {
		return Session{}, err
	}
	refreshToken, refreshHash, err := newOpaqueToken()
	if err != nil {
		return Session{}, err
	}
	refreshExpiresAt := now.Add(refreshTokenTTL)
	if err := queries.CreateRefreshToken(ctx, db.CreateRefreshTokenParams{
		UserID: user.ID, TokenHash: refreshHash,
		ExpiresAt: pgtype.Timestamptz{Time: refreshExpiresAt, Valid: true},
	}); err != nil {
		return Session{}, fmt.Errorf("store refresh token: %w", err)
	}
	view, err := s.userView(ctx, queries, user)
	if err != nil {
		return Session{}, err
	}
	return Session{AccessToken: accessToken, AccessExpiresAt: accessExpiresAt, RefreshToken: refreshToken, RefreshExpiresAt: refreshExpiresAt, User: view}, nil
}

func (s *Service) issueActionToken(ctx context.Context, queries *db.Queries, userID uuid.UUID, purpose string, ttl time.Duration) (string, error) {
	if err := queries.InvalidateAccountActionTokens(ctx, db.InvalidateAccountActionTokensParams{UserID: userID, Purpose: purpose}); err != nil {
		return "", fmt.Errorf("invalidate previous action tokens: %w", err)
	}
	raw, hash, err := newOpaqueToken()
	if err != nil {
		return "", err
	}
	if err := queries.CreateAccountActionToken(ctx, db.CreateAccountActionTokenParams{
		UserID: userID, Purpose: purpose, TokenHash: hash,
		ExpiresAt: pgtype.Timestamptz{Time: s.now().UTC().Add(ttl), Valid: true},
	}); err != nil {
		return "", fmt.Errorf("store action token: %w", err)
	}
	return raw, nil
}

func (s *Service) consumeAction(ctx context.Context, rawToken, purpose string, audit AuditContext, action func(*db.Queries, uuid.UUID) error) error {
	if rawToken == "" {
		return ErrInvalidToken
	}
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin account action: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()
	queries := s.queries.WithTx(tx)
	userID, err := queries.ConsumeAccountActionToken(ctx, db.ConsumeAccountActionTokenParams{TokenHash: hashOpaqueToken(rawToken), Purpose: purpose})
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return ErrInvalidToken
		}
		return fmt.Errorf("consume account action token: %w", err)
	}
	if err := action(queries, userID); err != nil {
		return err
	}
	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("commit account action: %w", err)
	}
	return nil
}

func (s *Service) userView(ctx context.Context, queries *db.Queries, user db.User) (UserView, error) {
	roles, err := queries.GetUserRoles(ctx, user.ID)
	if err != nil {
		return UserView{}, fmt.Errorf("load user roles: %w", err)
	}
	roleNames := make([]string, 0, 2)
	if roles.IsProfessional {
		roleNames = append(roleNames, RoleProfessional)
	}
	if roles.IsClient {
		roleNames = append(roleNames, RoleClient)
	}
	return UserView{ID: user.ID, Email: user.Email, DisplayName: user.DisplayName, EmailVerified: user.EmailVerifiedAt.Valid, Roles: roleNames}, nil
}

func createProfile(ctx context.Context, queries *db.Queries, userID uuid.UUID, profileType, companyName string) error {
	switch profileType {
	case RoleProfessional:
		_, err := queries.CreateProfessionalProfile(ctx, userID)
		return err
	case RoleClient:
		_, err := queries.CreateClientProfile(ctx, db.CreateClientProfileParams{UserID: userID, CompanyName: companyName})
		return err
	default:
		return fmt.Errorf("invalid profile type")
	}
}

func recordAudit(ctx context.Context, queries *db.Queries, actorID *uuid.UUID, action, resource string, resourceID *uuid.UUID, metadata map[string]any, audit AuditContext) error {
	if metadata == nil {
		metadata = map[string]any{}
	}
	encoded, err := json.Marshal(metadata)
	if err != nil {
		return fmt.Errorf("encode audit metadata: %w", err)
	}
	_, err = queries.CreateAuditEvent(ctx, db.CreateAuditEventParams{
		ActorID: actorID, Action: action, Resource: resource, ResourceID: resourceID,
		Metadata: encoded, IpAddress: audit.IPAddress, UserAgent: audit.UserAgent,
	})
	if err != nil {
		return fmt.Errorf("record audit event: %w", err)
	}
	return nil
}

func normalizeEmail(value string) string { return strings.ToLower(strings.TrimSpace(value)) }

func isUniqueViolation(err error) bool {
	var pgError *pgconn.PgError
	return errors.As(err, &pgError) && pgError.Code == "23505"
}

var dummyPasswordHash, _ = hashPassword("not-the-password-000")
