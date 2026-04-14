from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    IDLE = "idle"


@dataclass
class Request:
    id: str
    source: int
    dest: int
    time: int


@dataclass
class Passenger:
    request: Request
    car_id: str
    pickup_tick: int | None = None
    dropoff_tick: int | None = None
    scores: dict[str, float] | None = None


@dataclass
class Car:
    id: str
    floor: int
    capacity: int
    direction: Direction = Direction.IDLE
    passengers: list[Passenger] = field(default_factory=list)
    assigned: list[Passenger] = field(default_factory=list)
    stop_remaining: int = 0

    @property
    def remaining_capacity(self) -> int:
        return self.capacity - len(self.passengers)

    @property
    def is_idle(self) -> bool:
        return (
            self.direction is Direction.IDLE
            and not self.passengers
            and not self.assigned
            and self.stop_remaining == 0
        )

    def target_floors(self) -> set[int]:
        """Floors this car needs to visit: dropoffs + boardable pickups.

        Pickup floors are only included when the car has remaining capacity.
        A full car should deliver first, freeing capacity, before stopping
        for new pickups. (Pickup floors that coincide with a dropoff floor
        are still visited — alighting happens before boarding.)
        """
        floors: set[int] = set()
        for p in self.passengers:
            floors.add(p.request.dest)
        if self.remaining_capacity > 0:
            for p in self.assigned:
                floors.add(p.request.source)
        return floors


@dataclass
class Building:
    num_floors: int
    cars: list[Car]

    def idle_cars(self) -> list[Car]:
        return [c for c in self.cars if c.is_idle]

    def idle_count_at(self, floor: int) -> int:
        return sum(1 for c in self.cars if c.is_idle and c.floor == floor)
