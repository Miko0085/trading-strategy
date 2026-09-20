from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


# config.py -> app -> backend -> manual-grid-ui -> prototype -> repository root
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MODULE_ROOT = Path(__file__).resolve().parents[2]


def _non_empty(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _process_values() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if value != ""}


def _credential_bundle(process: Mapping[str, str], module: Mapping[str, str], root: Mapping[str, str]) -> tuple[str, str, bool, str]:
    for source_name, values in (("process_env", process), ("module_env", module), ("root_env", root)):
        key = _non_empty(values.get("BYBIT_API_KEY"))
        secret = _non_empty(values.get("BYBIT_API_SECRET"))
        if key and secret:
            testnet = (_non_empty(values.get("BYBIT_TESTNET")) or "false").lower() == "true"
            return key, secret, testnet, source_name
    return "", "", False, "none"


@dataclass(frozen=True)
class Settings:
    database_url: str | None = None
    bybit_api_key: str | None = None
    bybit_api_secret: str | None = None
    bybit_testnet: bool | None = None
    allowed_origins: str | None = None
    allow_fixture_data: bool | None = None
    stale_after_seconds: float | None = None
    credential_source: str | None = field(default=None, init=False)
    repository_root_found: bool = field(default=False, init=False)
    root_env_found: bool = field(default=False, init=False)
    module_env_found: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        explicit_credentials = self.bybit_api_key is not None or self.bybit_api_secret is not None
        process = _process_values()
        module = dotenv_values(MODULE_ROOT / ".env")
        root = dotenv_values(REPOSITORY_ROOT / ".env")
        key, secret, testnet, source = _credential_bundle(process, module, root)

        # UI settings intentionally never consult root dotenv values.
        values = {
            "database_url": self.database_url or _non_empty(process.get("DATABASE_URL")) or _non_empty(module.get("DATABASE_URL")) or "postgresql://manual_grid:manual_grid@localhost:5432/manual_grid",
            "bybit_api_key": self.bybit_api_key if self.bybit_api_key is not None else key,
            "bybit_api_secret": self.bybit_api_secret if self.bybit_api_secret is not None else secret,
            "bybit_testnet": self.bybit_testnet if self.bybit_testnet is not None else testnet,
            "allowed_origins": self.allowed_origins or _non_empty(process.get("MANUAL_GRID_ALLOWED_ORIGINS")) or _non_empty(module.get("MANUAL_GRID_ALLOWED_ORIGINS")) or "http://localhost:5173",
            "allow_fixture_data": self.allow_fixture_data if self.allow_fixture_data is not None else (_non_empty(process.get("MANUAL_GRID_ALLOW_FIXTURE_DATA")) or _non_empty(module.get("MANUAL_GRID_ALLOW_FIXTURE_DATA")) or "false").lower() == "true",
            "stale_after_seconds": self.stale_after_seconds if self.stale_after_seconds is not None else float(_non_empty(process.get("MANUAL_GRID_STALE_AFTER_SECONDS")) or _non_empty(module.get("MANUAL_GRID_STALE_AFTER_SECONDS")) or "30"),
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        selected_source = source if not explicit_credentials else ("process_env" if key and secret else "none")
        object.__setattr__(self, "credential_source", selected_source if key and secret and values["bybit_api_key"] and values["bybit_api_secret"] else "none")
        object.__setattr__(self, "repository_root_found", REPOSITORY_ROOT.is_dir() and (REPOSITORY_ROOT / ".git").exists())
        object.__setattr__(self, "root_env_found", (REPOSITORY_ROOT / ".env").is_file())
        object.__setattr__(self, "module_env_found", (MODULE_ROOT / ".env").is_file())

    @property
    def private_configured(self) -> bool:
        return bool(self.bybit_api_key and self.bybit_api_secret)

    @property
    def environment(self) -> str:
        return "testnet" if self.bybit_testnet else "mainnet"

    def validate(self) -> None:
        if bool(self.bybit_api_key) != bool(self.bybit_api_secret):
            raise ValueError("BYBIT_API_KEY and BYBIT_API_SECRET must be set together")
