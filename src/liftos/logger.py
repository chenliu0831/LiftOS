from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from liftos.models import Car, Passenger


def _make_logger(name: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(path, mode="w")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


class ElevatorLogger:
    """Writes one JSONL entry per car per tick."""

    def __init__(self, path: Path) -> None:
        self._logger = _make_logger(f"liftos.elevator.{id(self)}", path)

    def log(self, tick: int, car: Car) -> None:
        self._logger.info(json.dumps({
            "tick": tick,
            "car_id": car.id,
            "floor": car.floor,
            "direction": car.direction,
            "passenger_count": len(car.passengers),
        }))


class PassengerLogger:
    """Writes one JSONL entry per passenger at dropoff."""

    def __init__(self, path: Path) -> None:
        self._logger = _make_logger(f"liftos.passenger.{id(self)}", path)

    def log(self, passenger: Passenger) -> None:
        self._logger.info(json.dumps({
            "id": passenger.request.id,
            "source": passenger.request.source,
            "dest": passenger.request.dest,
            "request_tick": passenger.request.time,
            "pickup_tick": passenger.pickup_tick,
            "dropoff_tick": passenger.dropoff_tick,
            "car_id": passenger.car_id,
        }))


class DispatchLogger:
    """Writes one JSONL entry per scheduler assignment decision."""

    def __init__(self, path: Path) -> None:
        self._logger = _make_logger(f"liftos.dispatch.{id(self)}", path)

    def log(self, tick: int, passenger: Passenger) -> None:
        entry: dict = {
            "tick": tick,
            "passenger_id": passenger.request.id,
            "car_id": passenger.car_id,
        }
        if passenger.scores is not None:
            entry["scores"] = passenger.scores
        self._logger.info(json.dumps(entry))
