from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MODULE_ROOT = Path(__file__).resolve().parents[2]


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _value(name: str, module_env: dict[str, str], root_env: dict[str, str], *, root_fallback: bool = False) -> str | None:
    if name in os.environ and os.environ[name]:
        return os.environ[name]
    if name in module_env and module_env[name]:
        return module_env[name]
    return root_env.get(name) if root_fallback and root_env.get(name) else None


@dataclass(frozen=True)
class Settings:
    database_url: str | None = None
    bybit_api_key: str | None = None
    bybit_api_secret: str | None = None
    bybit_testnet: bool | None = None
    allowed_origins: str | None = None
    allow_fixture_data: bool | None = None
    stale_after_seconds: float | None = None
    _loaded: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        module_env = _read_dotenv(MODULE_ROOT / ".env")
        root_env = _read_dotenv(REPOSITORY_ROOT / ".env")
        values = {
            "database_url": self.database_url or _value("DATABASE_URL", module_env, root_env) or "postgresql://manual_grid:manual_grid@localhost:5432/manual_grid",
            "bybit_api_key": self.bybit_api_key if self.bybit_api_key is not None else _value("BYBIT_API_KEY", module_env, root_env, root_fallback=True) or "",
            "bybit_api_secret": self.bybit_api_secret if self.bybit_api_secret is not None else _value("BYBIT_API_SECRET", module_env, root_env, root_fallback=True) or "",
            "bybit_testnet": self.bybit_testnet if self.bybit_testnet is not None else (_value("BYBIT_TESTNET", module_env, root_env, root_fallback=True) or "false").lower() == "true",
            "allowed_origins": self.allowed_origins or _value("MANUAL_GRID_ALLOWED_ORIGINS", module_env, root_env) or "http://localhost:5173",
            "allow_fixture_data": self.allow_fixture_data if self.allow_fixture_data is not None else (_value("MANUAL_GRID_ALLOW_FIXTURE_DATA", module_env, root_env) or "false").lower() == "true",
            "stale_after_seconds": self.stale_after_seconds if self.stale_after_seconds is not None else float(_value("MANUAL_GRID_STALE_AFTER_SECONDS", module_env, root_env) or "30"),
        }
        for key, value in values.items():
            object.__setattr__(self, key, value)

    @property
    def private_configured(self) -> bool:
        return bool(self.bybit_api_key or self.bybit_api_secret)

    def validate(self) -> None:
        if bool(self.bybit_api_key) != bool(self.bybit_api_secret):
            raise ValueError("BYBIT_API_KEY and BYBIT_API_SECRET must be set together")
