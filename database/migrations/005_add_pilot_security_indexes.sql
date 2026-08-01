-- Pilot security/performance indexes v1. Additive and reversible after a
-- reviewed retention decision. No application request applies this migration.

create index if not exists idx_pilot_sessions_completion_updated
  on pilot_sessions(completion_status, updated_at);

create index if not exists idx_pilot_events_idempotency
  on pilot_events(session_id, idempotency_key);

create index if not exists idx_professional_reviews_publication
  on professional_reviews(publication_status, reviewed_at);
