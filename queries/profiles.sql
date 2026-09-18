-- name: CreateProfessionalProfile :one
INSERT INTO professional_profiles (user_id)
VALUES ($1)
RETURNING *;

-- name: CreateClientProfile :one
INSERT INTO client_profiles (user_id, company_name)
VALUES ($1, $2)
RETURNING *;

-- name: GetProfessionalProfileByUserID :one
SELECT * FROM professional_profiles WHERE user_id = $1;

-- name: GetClientProfileByUserID :one
SELECT * FROM client_profiles WHERE user_id = $1;
