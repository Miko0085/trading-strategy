CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ui_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('mainnet', 'testnet')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS grids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL REFERENCES ui_accounts(id),
    symbol TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS grid_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), grid_id UUID NOT NULL REFERENCES grids(id),
    revision_no INTEGER NOT NULL, payload JSONB NOT NULL, market_snapshot JSONB NOT NULL,
    comment TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(grid_id, revision_no)
);
CREATE TABLE IF NOT EXISTS grid_order_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), revision_id UUID NOT NULL REFERENCES grid_revisions(id),
    side TEXT NOT NULL CHECK (side IN ('long', 'short')), level INTEGER NOT NULL,
    entry_offset_pct NUMERIC NOT NULL, configured_qty NUMERIC NOT NULL, note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tp_step_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), order_config_id UUID NOT NULL REFERENCES grid_order_configs(id),
    step_no INTEGER NOT NULL, move_pct NUMERIC NOT NULL, close_pct NUMERIC NOT NULL
);
CREATE TABLE IF NOT EXISTS allocation_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), revision_id UUID NOT NULL REFERENCES grid_revisions(id),
    long_pct NUMERIC NOT NULL, short_pct NUMERIC NOT NULL, reserve_pct NUMERIC NOT NULL,
    active_long_count INTEGER NOT NULL, active_short_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS account_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID NOT NULL REFERENCES ui_accounts(id),
    symbol TEXT NOT NULL, payload JSONB NOT NULL, captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), account_id UUID REFERENCES ui_accounts(id),
    entity TEXT NOT NULL, action TEXT NOT NULL, before_payload JSONB, after_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS execution_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), revision_id UUID NOT NULL REFERENCES grid_revisions(id),
    status TEXT NOT NULL DEFAULT 'draft', payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS execution_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), plan_id UUID NOT NULL REFERENCES execution_plans(id),
    command_type TEXT NOT NULL, payload JSONB NOT NULL, status TEXT NOT NULL DEFAULT 'not_implemented',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
