from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class AllocationDTO(ApiModel):
    long_pct: Decimal = Field(ge=0, le=100, validation_alias=AliasChoices("long_pct", "longPct"))
    short_pct: Decimal = Field(ge=0, le=100, validation_alias=AliasChoices("short_pct", "shortPct"))
    reserve_pct: Decimal = Field(ge=0, le=100, validation_alias=AliasChoices("reserve_pct", "reservePct"))

    @model_validator(mode="after")
    def total_is_at_most_one_hundred(self) -> "AllocationDTO":
        if self.long_pct + self.short_pct + self.reserve_pct > 100:
            raise ValueError("Распределение не может превышать 100%")
        return self


class TPConfigDTO(ApiModel):
    move_pct: Decimal = Field(validation_alias=AliasChoices("move_pct", "movePct"))
    close_pct: Decimal = Field(validation_alias=AliasChoices("close_pct", "closePct"))


class GridOrderDTO(ApiModel):
    id: str | None = None
    offset_pct: Decimal = Field(validation_alias=AliasChoices("offset_pct", "offsetPct"))
    qty: Decimal = Field(gt=0)
    filled_qty: Decimal = Field(default=Decimal(0), ge=0, validation_alias=AliasChoices("filled_qty", "filledQty"))
    avg_fill_price: Decimal | None = Field(default=None, validation_alias=AliasChoices("avg_fill_price", "avgFill"))
    actual_closed_qty: Decimal = Field(default=Decimal(0), ge=0, validation_alias=AliasChoices("actual_closed_qty", "actualClosedQty"))
    tps: list[TPConfigDTO] = Field(default_factory=list)
    note: str = ""


class GridConfigurationDTO(ApiModel):
    symbol: str = Field(min_length=1, max_length=30)
    allocation: AllocationDTO
    planning_leverage: Decimal | None = Field(default=None, gt=0, validation_alias=AliasChoices("planning_leverage", "planningLeverage", "leverage"))
    enabled_long: bool = Field(default=True, validation_alias=AliasChoices("enabled_long", "enabledLong"))
    enabled_short: bool = Field(default=True, validation_alias=AliasChoices("enabled_short", "enabledShort"))
    active_long_count: int = Field(ge=0, validation_alias=AliasChoices("active_long_count", "activeLongCount"))
    active_short_count: int = Field(ge=0, validation_alias=AliasChoices("active_short_count", "activeShortCount"))
    long: list[GridOrderDTO] = Field(default_factory=list)
    short: list[GridOrderDTO] = Field(default_factory=list)
    fee_rate: Decimal | None = Field(default=None, ge=0, validation_alias=AliasChoices("fee_rate", "feeRate"))

    @model_validator(mode="after")
    def active_counts_fit(self) -> "GridConfigurationDTO":
        if not self.enabled_long and self.active_long_count != 0:
            raise ValueError("Для выключенной Long стороны active_long_count должен быть 0")
        if not self.enabled_short and self.active_short_count != 0:
            raise ValueError("Для выключенной Short стороны active_short_count должен быть 0")
        if self.enabled_long and (not self.long or self.active_long_count < 1):
            raise ValueError("Для включённой Long стороны нужен хотя бы один уровень")
        if self.enabled_short and (not self.short or self.active_short_count < 1):
            raise ValueError("Для включённой Short стороны нужен хотя бы один уровень")
        if not self.enabled_long and not self.enabled_short:
            raise ValueError("Включите хотя бы одну сторону стратегии")
        if self.active_long_count > len(self.long) or self.active_short_count > len(self.short):
            raise ValueError("Размер активного окна не может превышать число уровней")
        return self

    def domain_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=False)


class SaveRevisionDTO(ApiModel):
    symbol: str = Field(min_length=1, max_length=30)
    comment: str = Field(default="", max_length=500)
    configuration: GridConfigurationDTO | None = None
    payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def configuration_required(self) -> "SaveRevisionDTO":
        if self.configuration is None and self.payload is None:
            raise ValueError("configuration is required")
        return self


class RevisionOut(BaseModel):
    id: str
    symbol: str
    comment: str
    payload: dict[str, Any]
    created_at: str
