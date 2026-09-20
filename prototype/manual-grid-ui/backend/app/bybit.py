from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx


class ReadOnlyBybitError(RuntimeError):
    pass


class ReadOnlyBybitClient:
    """GET-only Bybit V5 adapter. No trading method belongs in this class."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, http_client: httpx.AsyncClient | None = None):
        self.api_key, self.api_secret = api_key, api_secret
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self._client = http_client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    def _query(self, params: dict[str, Any]) -> str:
        return urlencode(sorted((key, str(value)) for key, value in params.items()))

    def _headers(self, params: dict[str, Any]) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        query = self._query(params)
        payload = timestamp + self.api_key + recv_window + query
        signature = hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return {"X-BAPI-API-KEY": self.api_key, "X-BAPI-TIMESTAMP": timestamp, "X-BAPI-RECV-WINDOW": recv_window, "X-BAPI-SIGN": signature}

    async def _request(self, path: str, params: dict[str, Any], authenticated: bool) -> dict[str, Any]:
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self.base_url, timeout=10)
        try:
            headers = self._headers(params) if authenticated else {}
            response = await client.get(path, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ReadOnlyBybitError("Bybit read-only request failed") from exc
        finally:
            if owns_client:
                await client.aclose()
        if payload.get("retCode") != 0:
            raise ReadOnlyBybitError(f"Bybit read-only request rejected: retCode={payload.get('retCode')}")
        return payload

    async def public_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request(path, params or {}, authenticated=False)

    async def private_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            raise ReadOnlyBybitError("Private Bybit integration is not configured")
        return await self._request(path, params or {}, authenticated=True)

    async def validate_read_only(self) -> dict[str, Any]:
        result = (await self.private_get("/v5/user/query-api")).get("result", {})
        if str(result.get("readOnly")) != "1":
            raise ReadOnlyBybitError("Bybit API key is not read-only; private integration refused")
        return result

    async def account_state(self) -> dict[str, Any]:
        return (await self.private_get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})).get("result", {})

    async def positions(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.private_get("/v5/position/list", {"category": category, "symbol": symbol})).get("result", {})

    async def open_orders(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.private_get("/v5/order/realtime", {"category": category, "symbol": symbol})).get("result", {})

    async def instrument(self, category: str, symbol: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return (await self.public_get("/v5/market/instruments-info", params)).get("result", {})

    async def mark_price(self, category: str, symbol: str) -> dict[str, Any]:
        return (await self.public_get("/v5/market/tickers", {"category": category, "symbol": symbol})).get("result", {})
