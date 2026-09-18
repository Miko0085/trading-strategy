from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

VALID_INTERVALS = {"1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Ticker(Strict):
    enabled: bool = True
    raw_recording: Literal["sampled", "all"] = "sampled"
    sample_interval_seconds: float = Field(default=1, gt=0)


class Toggle(Strict):
    enabled: bool = False


class Orderbook(Toggle):
    depth: Literal[1, 50, 200, 1000] = 1


class MarketSubscriptions(Strict):
    primary_kline_interval: str = "1"
    kline_intervals: list[str] = Field(default_factory=lambda: ["1"])
    ticker: Ticker = Field(default_factory=Ticker)
    public_trades: Toggle = Field(default_factory=Toggle)
    orderbook: Orderbook = Field(default_factory=Orderbook)

    @model_validator(mode="after")
    def check_intervals(self):
        if (
            "1" not in self.kline_intervals
            or self.primary_kline_interval not in self.kline_intervals
            or not set(self.kline_intervals) <= VALID_INTERVALS
        ):
            raise ValueError("Include 1-minute and primary interval; use supported V5 intervals")
        if len(set(self.kline_intervals)) != len(self.kline_intervals):
            raise ValueError("duplicate intervals")
        return self


class SymbolsConfig(Strict):
    exchange: Literal["bybit"] = "bybit"
    category: Literal["linear", "inverse"] = "linear"
    symbols: list[str] = Field(default_factory=list)
    market: dict

    @model_validator(mode="after")
    def validate_fields(self):
        if any(not s.isalnum() or s != s.upper() for s in self.symbols) or len(
            set(self.symbols)
        ) != len(self.symbols):
            raise ValueError("unique uppercase symbols required")
        self.market = MarketSubscriptions.model_validate(self.market).model_dump()
        return self


class SQLiteConfig(Strict):
    enabled: Literal[True] = True
    path: str = "./data/db/strategy.db"
    wal: Literal[True] = True


class RawConfig(Strict):
    enabled: Literal[True] = True
    directory: str = "./data/raw"
    rotation: Literal["daily"] = "daily"


class ExportConfig(Strict):
    directory: str = "./data/exports"


class Storage(Strict):
    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig)
    raw_jsonl: RawConfig = Field(default_factory=RawConfig)
    parquet: ExportConfig = Field(default_factory=ExportConfig)


class Snapshots(Strict):
    enabled: bool = True
    on_account_event: bool = True


class Market(Strict):
    save_closed_klines: Literal[True] = True
    save_open_kline_updates_raw: bool = True
    snapshots: Snapshots = Field(default_factory=Snapshots)
    auto_discovery: bool = True
    discovery_interval_seconds: float = Field(default=1, gt=0, le=60)


class Reconciliation(Strict):
    enabled: bool = True
    on_startup: bool = True
    on_reconnect: bool = True
    periodic: bool = True
    interval_seconds: int = Field(default=300, ge=10)
    overlap_seconds: int = Field(default=120, ge=1)
    startup_lookback_hours: int = Field(default=24, ge=1, le=336)
    settle_coins: list[str] = Field(default_factory=lambda: ["USDT", "USDC"], min_length=1)

    @model_validator(mode="after")
    def check_settle_coins(self):
        if len(set(self.settle_coins)) != len(self.settle_coins) or any(
            not c.isalnum() or c != c.upper() for c in self.settle_coins
        ):
            raise ValueError("unique uppercase settlement coins required")
        return self


class Notifications(Strict):
    executions: bool = True
    partial_fills: bool = True
    position_changes: bool = True
    grid_activity: bool = True
    wallet_changes: bool = False
    technical_events: bool = False


class Linking(Strict):
    lookback_minutes: int = Field(default=10, ge=0, le=1440)
    lookforward_minutes: int = Field(default=3, ge=0, le=1440)


class Telegram(Strict):
    enabled: bool = True
    language: Literal["ru"] = "ru"
    notifications: Notifications = Field(default_factory=Notifications)
    event_linking: Linking = Field(default_factory=Linking)
    aggregation_seconds: int = Field(default=5, ge=1, le=60)


class Transcription(Strict):
    enabled: bool = True
    language: Literal["ru"] = "ru"
    max_attempts: int = Field(default=5, ge=1, le=20)
    retry_seconds: int = Field(default=60, ge=1)
    directory: str = "./data/voice"


class Dataset(Strict):
    timezone_storage: Literal["UTC"] = "UTC"


class RecorderConfig(Strict):
    environment: Literal["mainnet", "testnet"] = "mainnet"
    storage: dict
    market: dict
    reconciliation: dict
    telegram: dict
    transcription: dict
    dataset: dict

    @model_validator(mode="after")
    def nested(self):
        for name, cls in (
            ("storage", Storage),
            ("market", Market),
            ("reconciliation", Reconciliation),
            ("telegram", Telegram),
            ("transcription", Transcription),
            ("dataset", Dataset),
        ):
            setattr(self, name, cls.model_validate(getattr(self, name)).model_dump())
        return self


def load_config(symbols_path="config/symbols.yaml", recorder_path="config/recorder.yaml"):
    load_dotenv()

    def read(path):
        with Path(path).open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    symbols = SymbolsConfig.model_validate(read(symbols_path))
    recorder = RecorderConfig.model_validate(read(recorder_path))
    legacy = os.getenv("BYBIT_TESTNET")
    if legacy and legacy.lower() not in {"true", "false"}:
        raise ValueError("BYBIT_TESTNET must be true/false")
    if legacy and (legacy.lower() == "true") != (recorder.environment == "testnet"):
        raise ValueError("BYBIT_TESTNET conflicts with recorder.yaml environment")
    return symbols, recorder


def credentials():
    return os.getenv("BYBIT_API_KEY"), os.getenv("BYBIT_API_SECRET")
