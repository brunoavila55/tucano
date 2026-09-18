ALTER TABLE audit_events DROP CONSTRAINT IF EXISTS audit_events_actor_fk;
DROP TABLE IF EXISTS account_action_tokens;
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS client_profiles;
DROP TABLE IF EXISTS professional_profiles;
DROP TABLE IF EXISTS users;
