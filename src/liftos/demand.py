from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from liftos.models import Building, Car


class DemandTracker:
    """Tracks per-floor request frequency for idle-car redistribution."""

    def __init__(self) -> None:
        self._counts: dict[int, int] = defaultdict(int)

    def record(self, floor: int) -> None:
        self._counts[floor] += 1

    def demand_ranking(self) -> list[int]:
        """Floors sorted by descending request frequency."""
        return sorted(self._counts, key=lambda f: -self._counts[f])


def redistribute_target(
    car: Car,
    building: Building,
    demand: DemandTracker,
) -> int | None:
    """Pick the highest-demand floor where < 50% of cars are already idle."""
    cap = len(building.cars) * 0.5
    for floor in demand.demand_ranking():
        if building.idle_count_at(floor) < cap:
            return floor
    return None
