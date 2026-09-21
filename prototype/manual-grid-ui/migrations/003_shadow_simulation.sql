CREATE TABLE IF NOT EXISTS shadow_grid_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    trigger TEXT NOT NULL,
    revision_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'VIRTUAL',
    payload JSONB NOT NULL,
    capital_snapshot JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS shadow_grid_revisions_symbol_created_idx ON shadow_grid_revisions(symbol, created_at DESC);
