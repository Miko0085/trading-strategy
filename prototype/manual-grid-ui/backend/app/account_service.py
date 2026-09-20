from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .account_state import normalize_account, normalize_instrument
from .bybit import ReadOnlyBybitClient, ReadOnlyBybitError


class AccountStateService:
    """Single backend owner of normalized factual market/account state."""

    def __init__(self, client: ReadOnlyBybitClient, *, stale_after_seconds: float = 30):
        self.client = client
        self.stale_after_seconds = stale_after_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    async def refresh(self, symbol: str, *, require_private: bool = False) -> dict[str, Any]:
        symbol = symbol.upper()
        if require_private and not self.client.api_key:
            raise ReadOnlyBybitError("Private Bybit integration is not configured")
        try:
            ticker = await self.client.mark_price("linear", symbol)
            instrument = normalize_instrument(await self.client.instrument("linear", symbol))
            wallet = await self.client.account_state() if require_private else {}
            positions = await self.client.positions("linear", symbol) if require_private else {}
            orders: dict[str, Any] = {}
            orders_available = not require_private
            orders_error = None
            if require_private:
                try:
                    orders = await self.client.open_orders("linear", symbol)
                    if not isinstance(orders.get("list"), list):
                        raise ReadOnlyBybitError("Bybit open orders result list is missing")
                    orders_available = True
                except ReadOnlyBybitError as exc:
                    orders_error = "Открытые ордера Bybit недоступны"
            state = normalize_account(wallet, positions, orders, ticker, instrument, "bybit_read_only" if require_private else "public_only")
            state["orders_available"] = orders_available
            state["orders_error"] = orders_error
            state["updated_at"] = datetime.now(UTC).isoformat()
            state["stale"] = False
            state["error"] = None
            self._cache[symbol] = state
            return state
        except ReadOnlyBybitError as exc:
            cached = self._cache.get(symbol)
            if cached is None:
                raise
            if require_private and cached.get("source") != "bybit_read_only":
                raise
            stale = dict(cached)
            stale["stale"] = True
            stale["error"] = "Нет свежего обновления Bybit"
            stale["stale_reason"] = str(exc)
            return stale

    async def get(self, symbol: str, *, require_private: bool = False) -> dict[str, Any]:
        return await self.get_fresh_or_refresh(symbol, max_age=self.stale_after_seconds, require_private=require_private)

    def get_cached(self, symbol: str, *, require_private: bool = False) -> dict[str, Any] | None:
        state = self._cache.get(symbol.upper())
        if state is None:
            return None
        if require_private and state.get("source") != "bybit_read_only":
            return None
        return state

    async def get_fresh_or_refresh(self, symbol: str, *, max_age: float | None = None, require_private: bool = False) -> dict[str, Any]:
        state = self.get_cached(symbol, require_private=require_private)
        updated_at = state.get("updated_at") if state else None
        age = (datetime.now(UTC) - datetime.fromisoformat(updated_at)).total_seconds() if updated_at else float("inf")
        if state is None or state.get("stale") or age > (self.stale_after_seconds if max_age is None else max_age):
            state = await self.refresh(symbol, require_private=require_private)
            updated_at = state.get("updated_at")
            age = (datetime.now(UTC) - datetime.fromisoformat(updated_at)).total_seconds() if updated_at else float("inf")
        if state.get("stale") or age > (self.stale_after_seconds if max_age is None else max_age):
            raise ReadOnlyBybitError("Account state is stale")
        return state
