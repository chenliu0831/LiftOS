from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from liftos.demand import DemandTracker, redistribute_target
from liftos.movement import MoveStrategy, move_one_floor

if TYPE_CHECKING:
    from liftos.logger import DispatchLogger, ElevatorLogger, PassengerLogger
    from liftos.models import Building, Car, Direction, Passenger, Request
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
        self._demand = DemandTracker()

    def run(self, requests: list[Request], max_ticks: int = 2500) -> EngineRunResult:
        pending: dict[int, list[Request]] = {}
        for req in requests:
            pending.setdefault(req.time, []).append(req)
        last_arrival = max((r.time for r in requests), default=-1)

        passengers: list[Passenger] = []
        for tick in range(max_ticks + 1):
            passengers.extend(self._step(tick, pending))
            if tick >= last_arrival and self._all_delivered(passengers):
                break

        return EngineRunResult(passengers=passengers, ticks=tick)

    def _step(
        self, tick: int, pending: dict[int, list[Request]]
    ) -> list[Passenger]:
        """Execute one simulation tick. Returns newly inserted passengers."""
        new_passengers = self._insert(pending.pop(tick, []))
        self._dispatch(new_passengers, tick)
        for car in self._building.cars:
            self._merge(car, tick)
        for car in self._building.cars:
            self._redistribute(car)
        self._finish(tick)
        return new_passengers

    @staticmethod
    def _all_delivered(passengers: list[Passenger]) -> bool:
        return bool(passengers) and all(
            p.dropoff_tick is not None for p in passengers
        )

    def _insert(self, requests: list[Request]) -> list[Passenger]:
        from liftos.models import Passenger

        passengers = []
        for req in requests:
            if req.source == req.dest:
                continue
            self._demand.record(req.source)
            passengers.append(Passenger(request=req, car_id=""))
        return passengers

    def _redistribute(self, car: Car) -> None:
        from liftos.models import Direction

        if not car.is_idle:
            return
        target = redistribute_target(car, self._building, self._demand)
        if target is None or target == car.floor:
            return
        if target > car.floor:
            car.direction = Direction.UP
            car.floor += 1
        else:
            car.direction = Direction.DOWN
            car.floor -= 1

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
