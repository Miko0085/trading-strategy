from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveWindowPolicy:
    level_count: int
    active_count: int

    def __post_init__(self) -> None:
        if self.level_count < 1 or self.active_count < 1 or self.active_count > self.level_count:
            raise ValueError("active window must be between 1 and level count")

    def active_levels(self, completed_levels: set[int] | None = None) -> list[int]:
        completed = completed_levels or set()
        remaining = [level for level in range(1, self.level_count + 1) if level not in completed]
        return remaining[: self.active_count]

    def queued_levels(self, completed_levels: set[int] | None = None) -> list[int]:
        active = set(self.active_levels(completed_levels))
        completed = completed_levels or set()
        return [level for level in range(1, self.level_count + 1) if level not in completed and level not in active]
