"""Additive v2 migration. Existing recordings are retained; no guessed backfill."""

ADDITIONS = {
    "raw_events_index": {
        "capture_id": "TEXT",
        "byte_offset": "INTEGER",
        "byte_length": "INTEGER",
        "status": "TEXT DEFAULT 'legacy'",
        "error": "TEXT",
    },
    "orders": {"version_ms": "INTEGER DEFAULT 0"},
    "market_snapshots": {"ticker_received_at": "TEXT", "ticker_age_ms": "INTEGER"},
    "trader_notes": {
        "voice_id": "TEXT",
        "owner_id": "INTEGER",
        "chat_id": "INTEGER",
        "telegram_update_id": "INTEGER",
        "original_text": "TEXT",
    },
    "voice_messages": {
        "note_id": "INTEGER",
        "chat_id": "INTEGER",
        "attempt_count": "INTEGER DEFAULT 0",
        "last_attempt": "TEXT",
        "next_attempt": "TEXT",
    },
    "tracked_instruments": {"stopped_at": "TEXT"},
}
SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS raw_capture_unique ON raw_events_index(capture_id);
CREATE UNIQUE INDEX IF NOT EXISTS note_update_unique ON trader_notes(telegram_update_id);
CREATE TABLE IF NOT EXISTS current_states(kind TEXT, state_key TEXT, symbol TEXT, version_ms INTEGER, received_at TEXT, data_json TEXT, PRIMARY KEY(kind,state_key));
CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, kind TEXT, entity_key TEXT, version_key TEXT UNIQUE, symbol TEXT, exchange_ms INTEGER, received_at TEXT, raw_id INTEGER, timeline_id INTEGER, data_json TEXT, before_json TEXT, after_json TEXT);
CREATE TABLE IF NOT EXISTS data_gaps(id INTEGER PRIMARY KEY, kind TEXT, start_ms INTEGER, end_ms INTEGER, details TEXT, resolved INTEGER NOT NULL DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS note_revisions(id INTEGER PRIMARY KEY, note_id INTEGER, changed_at TEXT, previous_text TEXT, previous_links TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS telegram_updates(update_id INTEGER PRIMARY KEY, status TEXT, received_at TEXT, payload_json TEXT);
CREATE TABLE IF NOT EXISTS telegram_state(chat_id INTEGER, user_id INTEGER, data_json TEXT, PRIMARY KEY(chat_id,user_id));
CREATE TABLE IF NOT EXISTS notification_outbox(id INTEGER PRIMARY KEY, destination INTEGER, payload_json TEXT, sent_at TEXT, attempts INTEGER DEFAULT 0, last_error TEXT);
CREATE INDEX IF NOT EXISTS observations_kind_time ON observations(kind,exchange_ms);
CREATE INDEX IF NOT EXISTS observations_timeline ON observations(timeline_id);
CREATE INDEX IF NOT EXISTS gaps_unresolved ON data_gaps(resolved);
CREATE TABLE IF NOT EXISTS account_balances(observation_id INTEGER PRIMARY KEY, account_type TEXT, wallet_balance TEXT, equity TEXT, available_margin TEXT, perpetual_unrealised_pnl TEXT, initial_margin TEXT, maintenance_margin TEXT);
CREATE TABLE IF NOT EXISTS coin_balances(observation_id INTEGER, coin TEXT, wallet_balance TEXT, equity TEXT, unrealised_pnl TEXT, cumulative_realised_pnl TEXT, PRIMARY KEY(observation_id,coin));
CREATE TABLE IF NOT EXISTS position_balances(observation_id INTEGER PRIMARY KEY, symbol TEXT, position_idx INTEGER, side TEXT, size TEXT, entry_price TEXT, unrealised_pnl TEXT, current_realised_pnl TEXT, cumulative_realised_pnl TEXT);
CREATE TABLE IF NOT EXISTS pnl_records(observation_id INTEGER PRIMARY KEY, kind TEXT, symbol TEXT, source_id TEXT, currency TEXT, closed_pnl TEXT, funding TEXT, cash_flow TEXT, fee TEXT, exchange_ms INTEGER);
"""

SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS tracked_instruments(
    category TEXT NOT NULL, symbol TEXT NOT NULL, first_seen TEXT NOT NULL,
    source TEXT NOT NULL, raw_id INTEGER, market_started_at TEXT,
    PRIMARY KEY(category,symbol)
);
"""
