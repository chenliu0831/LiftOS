import json
from pathlib import Path

from liftos.logger import DispatchLogger, ElevatorLogger, PassengerLogger
from liftos.models import Car, Direction, Passenger, Request


def test_elevator_logger(tmp_path: Path):
    path = tmp_path / "elevator_log.jsonl"
    logger = ElevatorLogger(path)
    car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
    car.passengers = [
        Passenger(request=Request(id="p1", source=1, dest=10, time=0), car_id="C0")
    ]
    logger.log(tick=3, car=car)

    entry = json.loads(path.read_text().strip())
    assert entry == {
        "tick": 3,
        "car_id": "C0",
        "floor": 5,
        "direction": "up",
        "passenger_count": 1,
    }


def test_passenger_logger(tmp_path: Path):
    path = tmp_path / "passenger_log.jsonl"
    logger = PassengerLogger(path)
    passenger = Passenger(
        request=Request(id="p1", source=1, dest=7, time=5),
        car_id="C2",
        pickup_tick=9,
        dropoff_tick=18,
    )
    logger.log(passenger)

    entry = json.loads(path.read_text().strip())
    assert entry == {
        "id": "p1",
        "source": 1,
        "dest": 7,
        "request_tick": 5,
        "pickup_tick": 9,
        "dropoff_tick": 18,
        "car_id": "C2",
    }


def test_dispatch_logger_without_scores(tmp_path: Path):
    path = tmp_path / "dispatch_log.jsonl"
    logger = DispatchLogger(path)
    passenger = Passenger(
        request=Request(id="p1", source=1, dest=7, time=5),
        car_id="C0",
    )
    logger.log(tick=5, passenger=passenger)

    entry = json.loads(path.read_text().strip())
    assert entry == {"tick": 5, "passenger_id": "p1", "car_id": "C0"}
    assert "scores" not in entry


def test_dispatch_logger_with_scores(tmp_path: Path):
    path = tmp_path / "dispatch_log.jsonl"
    logger = DispatchLogger(path)
    passenger = Passenger(
        request=Request(id="p1", source=1, dest=7, time=5),
        car_id="C2",
        scores={"eta": 0.15, "ride": 0.08, "load": 0.42, "total": 0.65},
    )
    logger.log(tick=5, passenger=passenger)

    entry = json.loads(path.read_text().strip())
    assert entry["scores"] == {"eta": 0.15, "ride": 0.08, "load": 0.42, "total": 0.65}
