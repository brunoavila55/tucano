-- name: CreateUser :one
INSERT INTO users (email, password_hash, display_name)
VALUES ($1, $2, $3)
RETURNING *;

-- name: GetUserByEmail :one
SELECT * FROM users WHERE email = $1;

-- name: GetUserByID :one
SELECT * FROM users WHERE id = $1;

-- name: MarkEmailVerified :one
UPDATE users
SET email_verified_at = COALESCE(email_verified_at, now()), updated_at = now()
WHERE id = $1 AND status = 'active'
RETURNING *;

-- name: UpdateUserPassword :exec
UPDATE users
SET password_hash = $2, updated_at = now()
WHERE id = $1 AND status = 'active';

-- name: CreateAccountActionToken :exec
INSERT INTO account_action_tokens (user_id, purpose, token_hash, expires_at)
VALUES ($1, $2, $3, $4);

-- name: InvalidateAccountActionTokens :exec
UPDATE account_action_tokens
SET used_at = now()
WHERE user_id = $1 AND purpose = $2 AND used_at IS NULL;

-- name: ConsumeAccountActionToken :one
UPDATE account_action_tokens
SET used_at = now()
WHERE token_hash = $1
  AND purpose = $2
  AND used_at IS NULL
  AND expires_at > now()
RETURNING user_id;

-- name: CreateRefreshToken :exec
INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
VALUES ($1, $2, $3);

-- name: ConsumeRefreshToken :one
UPDATE refresh_tokens
SET revoked_at = now()
WHERE token_hash = $1
  AND revoked_at IS NULL
  AND expires_at > now()
RETURNING user_id;

-- name: RevokeRefreshToken :exec
UPDATE refresh_tokens
SET revoked_at = COALESCE(revoked_at, now())
WHERE token_hash = $1;

-- name: RevokeAllUserRefreshTokens :exec
UPDATE refresh_tokens
SET revoked_at = now()
WHERE user_id = $1 AND revoked_at IS NULL;

-- name: GetUserRoles :one
SELECT
    EXISTS(
        SELECT 1 FROM professional_profiles
        WHERE professional_profiles.user_id = sqlc.arg(user_id)
    )::boolean AS is_professional,
    EXISTS(
        SELECT 1 FROM client_profiles
        WHERE client_profiles.user_id = sqlc.arg(user_id)
    )::boolean AS is_client;
