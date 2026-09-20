from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://manual_grid:manual_grid@localhost:5432/manual_grid")
    bybit_api_key: str = os.getenv("BYBIT_API_KEY", "")
    bybit_api_secret: str = os.getenv("BYBIT_API_SECRET", "")
    bybit_testnet: bool = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    bybit_readonly_required: bool = True
    allowed_origins: str = os.getenv("MANUAL_GRID_ALLOWED_ORIGINS", "http://localhost:5173")

    @property
    def private_configured(self) -> bool:
        return bool(self.bybit_api_key or self.bybit_api_secret)

    def validate(self) -> None:
        if bool(self.bybit_api_key) != bool(self.bybit_api_secret):
            raise ValueError("BYBIT_API_KEY and BYBIT_API_SECRET must be set together")
