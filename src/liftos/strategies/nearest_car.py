from __future__ import annotations

from liftos.models import Building, Car, Request


class NearestCar:
    def assign(self, request: Request, building: Building) -> Car:
        return min(
            building.cars,
            key=lambda c: (abs(c.floor - request.source), c.id),
        )
