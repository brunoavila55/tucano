package accounts

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestPasswordHashRoundTrip(t *testing.T) {
	hash, err := hashPassword("uma-senha-segura-123")
	require.NoError(t, err)
	require.True(t, comparePassword(hash, "uma-senha-segura-123"))
	require.False(t, comparePassword(hash, "senha-incorreta-123"))
}

func TestPasswordLengthIsValidated(t *testing.T) {
	_, err := hashPassword("curta")
	require.ErrorContains(t, err, "entre 12 e 128")
}
