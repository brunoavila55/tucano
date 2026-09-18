-- name: GetProfessionalProfileView :one
SELECT
    p.id,
    p.user_id,
    p.bio,
    p.primary_category_id,
    c.slug AS category_slug,
    c.name AS category_name,
    p.skills,
    p.service_region,
    (p.service_location IS NOT NULL)::boolean AS location_configured,
    p.service_radius_km,
    p.reference_price_cents,
    p.available_now,
    p.availability_timezone,
    p.updated_at
FROM professional_profiles p
LEFT JOIN service_categories c ON c.id = p.primary_category_id
WHERE p.user_id = $1;

-- name: UpdateProfessionalProfile :exec
UPDATE professional_profiles
SET
    bio = sqlc.arg(bio),
    primary_category_id = sqlc.arg(primary_category_id),
    skills = sqlc.arg(skills),
    service_region = sqlc.arg(service_region),
    service_location = CASE
        WHEN sqlc.narg(latitude)::double precision IS NULL OR sqlc.narg(longitude)::double precision IS NULL
            THEN service_location
        ELSE ST_SetSRID(ST_MakePoint(sqlc.narg(longitude)::double precision, sqlc.narg(latitude)::double precision), 4326)::geography
    END,
    service_radius_km = sqlc.arg(service_radius_km),
    reference_price_cents = sqlc.narg(reference_price_cents),
    available_now = sqlc.arg(available_now),
    availability_timezone = sqlc.arg(availability_timezone),
    updated_at = now()
WHERE user_id = sqlc.arg(user_id);

-- name: DeleteProfessionalAvailabilities :exec
DELETE FROM availabilities
WHERE professional_profile_id = (SELECT id FROM professional_profiles WHERE user_id = $1);

-- name: CreateProfessionalAvailability :one
INSERT INTO availabilities (professional_profile_id, weekday, start_time, end_time)
SELECT id, sqlc.arg(weekday), sqlc.arg(start_time), sqlc.arg(end_time)
FROM professional_profiles
WHERE user_id = sqlc.arg(user_id)
RETURNING id, professional_profile_id, weekday, start_time, end_time, created_at;

-- name: ListProfessionalAvailabilities :many
SELECT a.id, a.weekday, a.start_time, a.end_time
FROM availabilities a
JOIN professional_profiles p ON p.id = a.professional_profile_id
WHERE p.user_id = $1
ORDER BY a.weekday, a.start_time;

-- name: CountProfessionalPortfolioItems :one
SELECT count(*)::integer
FROM portfolio_items i
JOIN professional_profiles p ON p.id = i.professional_profile_id
WHERE p.user_id = $1;

-- name: LockProfessionalProfile :one
SELECT id
FROM professional_profiles
WHERE user_id = $1
FOR UPDATE;

-- name: CreateProfessionalPortfolioItem :one
INSERT INTO portfolio_items (professional_profile_id, storage_key, original_name, media_type, size_bytes, sort_order)
SELECT id, sqlc.arg(storage_key), sqlc.arg(original_name), sqlc.arg(media_type), sqlc.arg(size_bytes), sqlc.arg(sort_order)
FROM professional_profiles
WHERE user_id = sqlc.arg(user_id)
RETURNING id, storage_key, original_name, media_type, size_bytes, sort_order, created_at;

-- name: ListProfessionalPortfolioItems :many
SELECT i.id, i.storage_key, i.original_name, i.media_type, i.size_bytes, i.sort_order, i.created_at
FROM portfolio_items i
JOIN professional_profiles p ON p.id = i.professional_profile_id
WHERE p.user_id = $1
ORDER BY i.sort_order, i.created_at;

-- name: DeleteProfessionalPortfolioItem :one
DELETE FROM portfolio_items i
USING professional_profiles p
WHERE i.id = sqlc.arg(item_id)
  AND i.professional_profile_id = p.id
  AND p.user_id = sqlc.arg(user_id)
RETURNING i.storage_key;

-- name: SearchProfessionals :many
SELECT
    p.id,
    u.display_name,
    p.bio,
    c.id AS category_id,
    c.slug AS category_slug,
    c.name AS category_name,
    p.skills,
    p.service_region,
    p.service_radius_km,
    p.reference_price_cents,
    p.available_now,
    round((ST_Distance(
        p.service_location,
        ST_SetSRID(ST_MakePoint(sqlc.arg(longitude)::double precision, sqlc.arg(latitude)::double precision), 4326)::geography
    ) / 1000)::numeric, 1)::double precision AS distance_km,
    CAST(COALESCE((
        SELECT i.storage_key
        FROM portfolio_items i
        WHERE i.professional_profile_id = p.id
        ORDER BY i.sort_order, i.created_at
        LIMIT 1
    ), '') AS text) AS cover_storage_key
FROM professional_profiles p
JOIN users u ON u.id = p.user_id AND u.status = 'active' AND u.email_verified_at IS NOT NULL
JOIN service_categories c ON c.id = p.primary_category_id AND c.is_active = true
WHERE p.primary_category_id = sqlc.arg(category_id)
  AND p.service_location IS NOT NULL
  AND (NOT sqlc.arg(available_now_only)::boolean OR p.available_now = true)
  AND ST_DWithin(
      p.service_location,
      ST_SetSRID(ST_MakePoint(sqlc.arg(longitude)::double precision, sqlc.arg(latitude)::double precision), 4326)::geography,
      LEAST(sqlc.arg(radius_km)::integer, p.service_radius_km) * 1000
  )
ORDER BY distance_km, p.updated_at DESC, p.id
LIMIT sqlc.arg(page_size)::integer
OFFSET sqlc.arg(page_offset)::integer;

-- name: CountSearchProfessionals :one
SELECT count(*)::bigint
FROM professional_profiles p
JOIN users u ON u.id = p.user_id AND u.status = 'active' AND u.email_verified_at IS NOT NULL
JOIN service_categories c ON c.id = p.primary_category_id AND c.is_active = true
WHERE p.primary_category_id = sqlc.arg(category_id)
  AND p.service_location IS NOT NULL
  AND (NOT sqlc.arg(available_now_only)::boolean OR p.available_now = true)
  AND ST_DWithin(
      p.service_location,
      ST_SetSRID(ST_MakePoint(sqlc.arg(longitude)::double precision, sqlc.arg(latitude)::double precision), 4326)::geography,
      LEAST(sqlc.arg(radius_km)::integer, p.service_radius_km) * 1000
  );
