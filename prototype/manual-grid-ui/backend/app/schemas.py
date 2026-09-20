from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AllocationIn(BaseModel):
    long_pct: Decimal = Field(ge=0, le=100)
    short_pct: Decimal = Field(ge=0, le=100)
    reserve_pct: Decimal = Field(ge=0, le=100)

    @field_validator("reserve_pct")
    @classmethod
    def total_is_one_hundred(cls, value: Decimal, info):
        data = info.data
        if "long_pct" in data and "short_pct" in data and data["long_pct"] + data["short_pct"] + value != 100:
            raise ValueError("Распределение должно составлять 100%")
        return value


class RevisionIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    comment: str = Field(default="", max_length=500)
    payload: dict[str, Any]


class RevisionOut(BaseModel):
    id: str
    symbol: str
    comment: str
    payload: dict[str, Any]
    created_at: str
