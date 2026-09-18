-- name: ListActiveCategories :many
SELECT id, slug, name, description
FROM service_categories
WHERE is_active = true
ORDER BY name;

-- name: GetActiveCategory :one
SELECT id, slug, name, description
FROM service_categories
WHERE id = $1 AND is_active = true;
