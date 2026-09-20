from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx


class ReadOnlyBybitError(RuntimeError):
    pass


class ReadOnlyBybitClient:
    """GET-only Bybit V5 adapter. There are deliberately no write methods."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key, self.api_secret = api_key, api_secret
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"

    def _headers(self, params: dict[str, Any]) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        query = "&".join(f"{key}={params[key]}" for key in sorted(params))
        payload = timestamp + self.api_key + recv_window + query
        signature = hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return {"X-BAPI-API-KEY": self.api_key, "X-BAPI-TIMESTAMP": timestamp, "X-BAPI-RECV-WINDOW": recv_window, "X-BAPI-SIGN": signature}

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as client:
            response = await client.get(path, params=params, headers=self._headers(params))
            response.raise_for_status()
            payload = response.json()
        if payload.get("retCode") != 0:
            raise ReadOnlyBybitError(f"Bybit retCode={payload.get('retCode')}")
        return payload

    async def validate_read_only(self) -> dict[str, Any]:
        payload = await self.get("/v5/user/query-api")
        result = payload.get("result", {})
        if str(result.get("readOnly")) != "1":
            raise ReadOnlyBybitError("Bybit API key is not read-only; private integration refused")
        return result

    async def account_state(self) -> dict[str, Any]:
        return (await self.get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})).get("result", {})

    async def positions(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.get("/v5/position/list", {"category": category, "symbol": symbol})).get("result", {})

    async def open_orders(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.get("/v5/order/realtime", {"category": category, "symbol": symbol})).get("result", {})

    async def instrument(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.get("/v5/market/instruments-info", {"category": category, "symbol": symbol})).get("result", {})

    async def mark_price(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.get("/v5/market/tickers", {"category": category, "symbol": symbol})).get("result", {})
