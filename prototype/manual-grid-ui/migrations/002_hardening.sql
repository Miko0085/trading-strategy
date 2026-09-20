ALTER TABLE grid_revisions ADD COLUMN IF NOT EXISTS validation_state TEXT NOT NULL DEFAULT 'BLOCKED';
ALTER TABLE grid_revisions ADD COLUMN IF NOT EXISTS validation_errors JSONB NOT NULL DEFAULT '[]';
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS entity_type TEXT NOT NULL DEFAULT 'grid_revision';
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS entity_id TEXT;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS side TEXT;
CREATE INDEX IF NOT EXISTS audit_events_created_at_idx ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_side_idx ON audit_events(side);
