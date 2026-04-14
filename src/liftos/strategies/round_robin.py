from __future__ import annotations

from liftos.models import Building, Car, Request


class RoundRobin:
    def __init__(self) -> None:
        self._index = 0

    def assign(self, request: Request, building: Building) -> Car:
        car = building.cars[self._index % len(building.cars)]
        self._index += 1
        return car
