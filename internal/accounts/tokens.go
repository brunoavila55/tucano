package accounts

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type TokenManager struct {
	secret    []byte
	issuer    string
	audience  string
	accessTTL time.Duration
}

type accessClaims struct {
	UserID string `json:"uid"`
	jwt.RegisteredClaims
}

func NewTokenManager(secret string) (*TokenManager, error) {
	if len(secret) < 32 {
		return nil, errors.New("token secret must contain at least 32 characters")
	}
	return &TokenManager{
		secret: []byte(secret), issuer: "tucano-api", audience: "tucano-web", accessTTL: 15 * time.Minute,
	}, nil
}

func (m *TokenManager) IssueAccessToken(userID uuid.UUID, now time.Time) (string, time.Time, error) {
	expiresAt := now.Add(m.accessTTL)
	claims := accessClaims{
		UserID: userID.String(),
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer: m.issuer, Subject: userID.String(), Audience: jwt.ClaimStrings{m.audience},
			IssuedAt: jwt.NewNumericDate(now), NotBefore: jwt.NewNumericDate(now), ExpiresAt: jwt.NewNumericDate(expiresAt),
			ID: uuid.NewString(),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(m.secret)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("sign access token: %w", err)
	}
	return signed, expiresAt, nil
}

func (m *TokenManager) ParseAccessToken(raw string) (uuid.UUID, error) {
	parsed, err := jwt.ParseWithClaims(raw, &accessClaims{}, func(token *jwt.Token) (any, error) {
		if token.Method != jwt.SigningMethodHS256 {
			return nil, errors.New("unexpected signing method")
		}
		return m.secret, nil
	}, jwt.WithIssuer(m.issuer), jwt.WithAudience(m.audience), jwt.WithExpirationRequired())
	if err != nil || !parsed.Valid {
		return uuid.Nil, ErrInvalidToken
	}
	claims, ok := parsed.Claims.(*accessClaims)
	if !ok || claims.UserID == "" || claims.Subject != claims.UserID {
		return uuid.Nil, ErrInvalidToken
	}
	userID, err := uuid.Parse(claims.UserID)
	if err != nil {
		return uuid.Nil, ErrInvalidToken
	}
	return userID, nil
}

func newOpaqueToken() (string, []byte, error) {
	value := make([]byte, 32)
	if _, err := rand.Read(value); err != nil {
		return "", nil, fmt.Errorf("generate secure token: %w", err)
	}
	raw := base64.RawURLEncoding.EncodeToString(value)
	return raw, hashOpaqueToken(raw), nil
}

func hashOpaqueToken(raw string) []byte {
	hash := sha256.Sum256([]byte(raw))
	return hash[:]
}
