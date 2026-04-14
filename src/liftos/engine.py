from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from liftos.movement import MoveStrategy, move_one_floor

if TYPE_CHECKING:
    from liftos.logger import DispatchLogger, ElevatorLogger, PassengerLogger
    from liftos.models import Building, Car, Passenger, Request
    from liftos.scheduler import Scheduler


@dataclass
class EngineRunResult:
    passengers: list[Passenger]
    ticks: int

    @property
    def unserved(self) -> list[Passenger]:
        return [p for p in self.passengers if p.dropoff_tick is None]

    @property
    def complete(self) -> bool:
        return len(self.unserved) == 0


@dataclass
class Loggers:
    elevator: ElevatorLogger | None = None
    passenger: PassengerLogger | None = None
    dispatch: DispatchLogger | None = None


class Engine:
    def __init__(
        self,
        building: Building,
        scheduler: Scheduler,
        move_strategy: MoveStrategy,
        loggers: Loggers | None = None,
    ) -> None:
        self._building = building
        self._scheduler = scheduler
        self._move_strategy = move_strategy
        self._loggers = loggers or Loggers()

    def run(self, requests: list[Request], max_ticks: int = 2500) -> EngineRunResult:
        requests_by_tick: dict[int, list[Request]] = {}
        for req in requests:
            requests_by_tick.setdefault(req.time, []).append(req)

        last_request_tick = max((r.time for r in requests), default=-1)
        all_passengers: list[Passenger] = []
        tick = 0

        while tick <= max_ticks:
            # INSERT
            new_passengers = self._insert(requests_by_tick.pop(tick, []))
            all_passengers.extend(new_passengers)

            # DISPATCH
            self._dispatch(new_passengers, tick)

            # MERGE
            for car in self._building.cars:
                self._merge(car, tick)

            # FINISH
            self._finish(tick)

            # Termination check
            all_inserted = tick >= last_request_tick
            all_served = all_passengers and all(
                p.dropoff_tick is not None for p in all_passengers
            )
            if all_inserted and all_served:
                break

            tick += 1

        return EngineRunResult(passengers=all_passengers, ticks=tick)

    def _insert(self, requests: list[Request]) -> list[Passenger]:
        from liftos.models import Passenger

        passengers = []
        for req in requests:
            if req.source == req.dest:
                continue
            passengers.append(Passenger(request=req, car_id=""))
        return passengers

    def _dispatch(self, passengers: list[Passenger], tick: int) -> None:
        for passenger in passengers:
            car = self._scheduler.assign(passenger.request, self._building)
            passenger.car_id = car.id
            if scores := getattr(self._scheduler, "last_scores", None):
                passenger.scores = scores
            car.assigned.append(passenger)
            if self._loggers.dispatch:
                self._loggers.dispatch.log(tick, passenger)

    def _merge(self, car: Car, tick: int) -> None:
        if car.stop_remaining > 0:
            car.stop_remaining -= 1
            if car.stop_remaining == 0:
                self._alight(car, tick)
                self._board(car, tick)
            return

        if car.floor in car.target_floors():
            car.stop_remaining = 2
            return

        move_one_floor(car, self._move_strategy)

    def _alight(self, car: Car, tick: int) -> None:
        remaining = []
        for p in car.passengers:
            if p.request.dest == car.floor:
                p.dropoff_tick = tick
                if self._loggers.passenger:
                    self._loggers.passenger.log(p)
            else:
                remaining.append(p)
        car.passengers = remaining

    def _board(self, car: Car, tick: int) -> None:
        still_waiting = []
        for p in car.assigned:
            if p.request.source == car.floor and car.remaining_capacity > 0:
                p.pickup_tick = tick
                car.passengers.append(p)
            else:
                still_waiting.append(p)
        car.assigned = still_waiting

    def _finish(self, tick: int) -> None:
        if self._loggers.elevator:
            for car in self._building.cars:
                self._loggers.elevator.log(tick, car)
