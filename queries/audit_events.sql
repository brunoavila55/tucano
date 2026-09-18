-- name: CreateAuditEvent :one
INSERT INTO audit_events (actor_id, action, resource, resource_id, metadata, ip_address, user_agent)
VALUES (
    sqlc.arg(actor_id), sqlc.arg(action), sqlc.arg(resource), sqlc.arg(resource_id),
    sqlc.arg(metadata), NULLIF(sqlc.arg(ip_address), '')::inet, sqlc.arg(user_agent)
)
RETURNING id, actor_id, action, resource, resource_id, metadata, ip_address, user_agent, created_at;
