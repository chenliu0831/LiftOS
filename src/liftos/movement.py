from __future__ import annotations

from typing import Protocol

from liftos.models import Car, Direction


class MoveStrategy(Protocol):
    def next_direction(self, car: Car) -> Direction: ...


class Look:
    """LOOK algorithm: continue while targets exist ahead, then reverse."""

    def next_direction(self, car: Car) -> Direction:
        targets = car.target_floors()
        if not targets:
            return Direction.IDLE

        match car.direction:
            case Direction.IDLE:
                # Tie-break: prefer lower floor (DOWN) for determinism
                nearest = min(targets, key=lambda f: (abs(f - car.floor), f))
                if nearest > car.floor:
                    return Direction.UP
                elif nearest < car.floor:
                    return Direction.DOWN
                return Direction.IDLE

            case Direction.UP:
                if any(f > car.floor for f in targets):
                    return Direction.UP
                return Direction.DOWN

            case Direction.DOWN:
                if any(f < car.floor for f in targets):
                    return Direction.DOWN
                return Direction.UP


def move_one_floor(car: Car, strategy: MoveStrategy) -> None:
    """Advance the car one floor using the given movement strategy.

    Updates car.floor and car.direction in place.
    Does nothing if the car is idle or has a target at its current floor.
    """
    if car.floor in car.target_floors():
        return

    direction = strategy.next_direction(car)
    car.direction = direction

    match direction:
        case Direction.UP:
            car.floor += 1
        case Direction.DOWN:
            car.floor -= 1
