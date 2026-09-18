"""V5 GET allowlist; the exact encoded query is both signed and transmitted."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import ssl
import time
from urllib.parse import urlencode

import aiohttp
import certifi
from yarl import URL

from recorder.events.models import RawEvent

PUBLIC = {"/v5/market/kline", "/v5/market/tickers", "/v5/market/time"}
ALLOWED = PUBLIC | {
    "/v5/user/query-api",
    "/v5/order/history",
    "/v5/order/realtime",
    "/v5/execution/list",
    "/v5/position/list",
    "/v5/account/wallet-balance",
    "/v5/account/info",
    "/v5/account/transaction-log",
    "/v5/position/closed-pnl",
}


class BybitError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"Bybit error code {code}")


class ReadOnlyBybitRest:
    def __init__(self, api_key="", api_secret="", testnet=False, capture=None):
        self.api_key, self.api_secret = api_key, api_secret
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.capture = capture
        self.last_capture = None

    def request_parts(self, path, params):
        if path not in ALLOWED:
            raise ValueError("Endpoint outside read-only allowlist")
        query = urlencode(sorted((k, str(v)) for k, v in params.items() if v is not None))
        url = URL(self.base_url + path + ("?" + query if query else ""), encoded=True)
        headers = {}
        if path not in PUBLIC:
            stamp, window = str(int(time.time() * 1000)), "5000"
            signature = hmac.new(
                self.api_secret.encode(),
                (stamp + self.api_key + window + query).encode(),
                hashlib.sha256,
            ).hexdigest()
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": stamp,
                "X-BAPI-RECV-WINDOW": window,
                "X-BAPI-SIGN": signature,
            }
        return url, headers

    async def _request(self, url, headers):
        context = ssl.create_default_context(cafile=certifi.where())
        async with (
            aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=context), timeout=aiohttp.ClientTimeout(total=30)
            ) as session,
            session.get(url, headers=headers, allow_redirects=False) as response,
        ):
            if response.status != 200:
                raise BybitError(f"HTTP_{response.status}")
            return await response.json()

    async def get(self, path, params):
        self.last_capture = None
        for attempt in range(3):
            url, headers = self.request_parts(path, params)
            try:
                response = await self._request(url, headers)
            except (aiohttp.ClientError, TimeoutError) as exc:
                if attempt == 2:
                    raise BybitError(type(exc).__name__) from None
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            # query-api includes API key: intentionally never persist its response.
            if self.capture and path != "/v5/user/query-api":
                self.last_capture = await self.capture(
                    RawEvent(
                        source="REST",
                        topic=path,
                        payload=response,
                        exchange_timestamp=response.get("time"),
                        context={"request": {k: v for k, v in params.items() if v is not None}},
                    )
                )
            if type(response.get("retCode")) is not int or response["retCode"] != 0:
                if response.get("retCode") in {10006, 10016} and attempt < 2:
                    await asyncio.sleep(0.5 * 2**attempt)
                    continue
                raise BybitError(response.get("retCode", "INVALID_RESPONSE"))
            if not isinstance(response.get("result"), dict):
                raise BybitError("INVALID_RESULT")
            return response
        raise BybitError("RETRY_EXHAUSTED")

    async def validate_read_only(self):
        response = await self.get("/v5/user/query-api", {})
        if (
            response.get("retCode") != 0
            or type(response["result"].get("readOnly")) is not int
            or response["result"]["readOnly"] != 1
        ):
            raise PermissionError("Private collector requires readOnly=1")
        return {"readOnly": 1}

    async def pages(self, path, params):
        cursor, seen = None, set()
        for _ in range(10000):
            response = await self.get(path, {**params, "cursor": cursor})
            result = response["result"]
            if not isinstance(result.get("list"), list):
                raise BybitError("INVALID_LIST")
            yield result["list"], self.last_capture
            cursor = result.get("nextPageCursor")
            if not cursor:
                return
            if cursor in seen:
                raise BybitError("REPEATED_CURSOR")
            seen.add(cursor)
        raise BybitError("PAGE_LIMIT")

    async def _paged(self, path, params):
        rows = []
        async for page, _ in self.pages(path, params):
            rows.extend(page)
        return rows

    async def executions(self, category, symbol=None, start_ms=None, end_ms=None):
        return await self._paged(
            "/v5/execution/list",
            {
                "category": category,
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 100,
            },
        )

    async def order_history(self, category, symbol=None, start_ms=None, end_ms=None):
        return await self._paged(
            "/v5/order/history",
            {
                "category": category,
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 50,
            },
        )

    async def klines(self, category, symbol, interval, start_ms, end_ms):
        result = await self.get(
            "/v5/market/kline",
            {
                "category": category,
                "symbol": symbol,
                "interval": interval,
                "start": start_ms,
                "end": end_ms,
                "limit": 1000,
            },
        )
        return result["result"]["list"]
