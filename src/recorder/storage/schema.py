SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS raw_events_index (id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, source TEXT NOT NULL, topic TEXT, path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS market_candles (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, interval TEXT NOT NULL, start_ms INTEGER NOT NULL, end_ms INTEGER, open TEXT, high TEXT, low TEXT, close TEXT, volume TEXT, turnover TEXT, confirm INTEGER, exchange_ts INTEGER, received_at TEXT, source TEXT NOT NULL, UNIQUE(symbol, interval, start_ms));
CREATE TABLE IF NOT EXISTS market_snapshots (id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, timestamp TEXT NOT NULL, last_price TEXT, mark_price TEXT, index_price TEXT, bid TEXT, ask TEXT, account_event_id INTEGER);
CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, symbol TEXT, category TEXT, position_idx INTEGER, first_seen TEXT, last_seen TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_events (id INTEGER PRIMARY KEY, order_id TEXT NOT NULL, event_key TEXT NOT NULL UNIQUE, event_ts TEXT, order_status TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS executions (exec_id TEXT PRIMARY KEY, order_id TEXT, symbol TEXT, exec_ts TEXT, exec_price TEXT, exec_qty TEXT, exec_pnl TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS positions (id INTEGER PRIMARY KEY, symbol TEXT, position_idx INTEGER, event_ts TEXT, side TEXT, size TEXT, entry_price TEXT, mark_price TEXT, unrealised_pnl TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS position_events (id INTEGER PRIMARY KEY, position_id INTEGER, semantic_change INTEGER NOT NULL, event_ts TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wallet_snapshots (id INTEGER PRIMARY KEY, event_ts TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS closed_pnl (id INTEGER PRIMARY KEY, symbol TEXT, exec_id TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS funding (id INTEGER PRIMARY KEY, symbol TEXT, event_ts TEXT, raw_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS trader_notes (id INTEGER PRIMARY KEY, created_at TEXT, text TEXT, verified INTEGER DEFAULT 0, context_json TEXT);
CREATE TABLE IF NOT EXISTS trader_note_links (note_id INTEGER NOT NULL, timeline_id INTEGER NOT NULL, PRIMARY KEY(note_id, timeline_id));
CREATE TABLE IF NOT EXISTS voice_messages (voice_id TEXT PRIMARY KEY, telegram_message_id TEXT, telegram_file_id TEXT, received_at TEXT, duration REAL, local_path TEXT, file_size INTEGER, transcription_status TEXT);
CREATE TABLE IF NOT EXISTS transcriptions (voice_id TEXT PRIMARY KEY, transcript TEXT, language TEXT, status TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS timeline (id INTEGER PRIMARY KEY, timestamp_exchange TEXT, timestamp_received TEXT NOT NULL, event_type TEXT NOT NULL, symbol TEXT, source TEXT NOT NULL, source_id TEXT, summary_ru TEXT, linked_raw_event_id INTEGER);
CREATE TABLE IF NOT EXISTS collector_state (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS websocket_sessions (session_id TEXT PRIMARY KEY, source TEXT, connected_at TEXT, disconnected_at TEXT, reason TEXT, reconnect_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reconciliation_runs (id INTEGER PRIMARY KEY, reason TEXT, started_at TEXT, finished_at TEXT, records_checked INTEGER DEFAULT 0, missing_found INTEGER DEFAULT 0, recovered INTEGER DEFAULT 0, duplicates INTEGER DEFAULT 0, errors TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS reconciliation_findings (id INTEGER PRIMARY KEY, run_id INTEGER, kind TEXT, source_id TEXT, details TEXT);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_start ON market_candles(symbol, interval, start_ms);
CREATE INDEX IF NOT EXISTS idx_timeline_received ON timeline(timestamp_received);
CREATE INDEX IF NOT EXISTS idx_exec_order ON executions(order_id);
"""
