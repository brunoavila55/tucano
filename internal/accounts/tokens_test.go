package accounts

import (
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestAccessTokenRoundTrip(t *testing.T) {
	manager, err := NewTokenManager("test-secret-with-at-least-32-characters")
	require.NoError(t, err)
	userID := uuid.New()
	token, _, err := manager.IssueAccessToken(userID, time.Now())
	require.NoError(t, err)
	parsedID, err := manager.ParseAccessToken(token)
	require.NoError(t, err)
	require.Equal(t, userID, parsedID)
}

func TestExpiredAccessTokenIsRejected(t *testing.T) {
	manager, err := NewTokenManager("test-secret-with-at-least-32-characters")
	require.NoError(t, err)
	token, _, err := manager.IssueAccessToken(uuid.New(), time.Now().Add(-time.Hour))
	require.NoError(t, err)
	_, err = manager.ParseAccessToken(token)
	require.ErrorIs(t, err, ErrInvalidToken)
}

func TestOpaqueTokensAreRandomAndStoredAsHashes(t *testing.T) {
	first, firstHash, err := newOpaqueToken()
	require.NoError(t, err)
	second, secondHash, err := newOpaqueToken()
	require.NoError(t, err)
	require.NotEqual(t, first, second)
	require.NotEqual(t, firstHash, secondHash)
	require.Equal(t, firstHash, hashOpaqueToken(first))
	require.NotContains(t, string(firstHash), first)
}
