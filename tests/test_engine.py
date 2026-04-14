from liftos.engine import Engine, Loggers, EngineRunResult
from liftos.models import Building, Car, Request
from liftos.movement import Look
from liftos.strategies.round_robin import RoundRobin


def _build(num_floors: int, num_cars: int, capacity: int = 8) -> Building:
    cars = [Car(id=f"C{i}", floor=1, capacity=capacity) for i in range(num_cars)]
    return Building(num_floors=num_floors, cars=cars)


class TestSingleCarSinglePassenger:
    """1 car at floor 1. Passenger requests floor 3 → 5 at tick 0.

    Expected timeline:
      Tick 0: car moves 1→2
      Tick 1: car moves 2→3
      Tick 2: car at target floor 3, stop begins (stop_remaining=2)
      Tick 3: stop_remaining 2→1
      Tick 4: stop_remaining 1→0, BOARD p1 (pickup_tick=4)
      Tick 5: car moves 3→4
      Tick 6: car moves 4→5
      Tick 7: car at target floor 5, stop begins (stop_remaining=2)
      Tick 8: stop_remaining 2→1
      Tick 9: stop_remaining 1→0, ALIGHT p1 (dropoff_tick=9)
    """

    def test_tick_values(self):
        building = _build(num_floors=5, num_cars=1)
        requests = [Request(id="p1", source=3, dest=5, time=0)]

        result = Engine(building, RoundRobin(), Look()).run(requests)

        assert result.complete
        assert result.ticks == 9
        p = result.passengers[0]
        assert p.request.id == "p1"
        assert p.pickup_tick == 4
        assert p.dropoff_tick == 9
        assert p.car_id == "C0"


class TestTwoCarsRoundRobin:
    """2 cars at floor 1. Two passengers at tick 0, assigned round-robin.

    p1 (3→5) → C0:  pickup_tick=4, dropoff_tick=9
    p2 (4→2) → C1:  pickup_tick=5, dropoff_tick=10
    """

    def test_tick_values(self):
        building = _build(num_floors=5, num_cars=2)
        requests = [
            Request(id="p1", source=3, dest=5, time=0),
            Request(id="p2", source=4, dest=2, time=0),
        ]

        result = Engine(building, RoundRobin(), Look()).run(requests)

        assert result.complete
        assert result.ticks == 10
        by_id = {p.request.id: p for p in result.passengers}

        p1 = by_id["p1"]
        assert p1.car_id == "C0"
        assert p1.pickup_tick == 4
        assert p1.dropoff_tick == 9

        p2 = by_id["p2"]
        assert p2.car_id == "C1"
        assert p2.pickup_tick == 5
        assert p2.dropoff_tick == 10


class TestSourceEqualsDest:
    """Requests with source == dest are silently dropped."""

    def test_invalid_request_dropped(self):
        building = _build(num_floors=5, num_cars=1)
        requests = [
            Request(id="p1", source=3, dest=3, time=0),
            Request(id="p2", source=2, dest=4, time=0),
        ]

        result = Engine(building, RoundRobin(), Look()).run(requests)

        assert len(result.passengers) == 1
        assert result.passengers[0].request.id == "p2"
        assert result.complete


class TestStaggeredArrivals:
    """Requests arriving at different ticks, single car.

    p1 at tick 0: source=2, dest=4 → C0
    p2 at tick 5: source=3, dest=1 → C0

    p1 timeline:
      Tick 0: car moves 1→2
      Tick 1: car at target 2, stop begins
      Tick 2: stop_remaining 2→1
      Tick 3: stop_remaining 1→0, BOARD p1 (pickup_tick=3)
      Tick 4: car moves 2→3
      Tick 5: p2 arrives at source=3, car at floor 3 → target! stop begins
      Tick 6: stop_remaining 2→1
      Tick 7: stop_remaining 1→0, BOARD p2 (pickup_tick=7). p1 still on board.
      Tick 8: car moves 3→4
      Tick 9: car at target 4, stop begins
      Tick 10: stop_remaining 2→1
      Tick 11: stop_remaining 1→0, ALIGHT p1 (dropoff_tick=11)

    p2 timeline (continues from tick 12):
      Tick 12: car reverses, moves 4→3
      Tick 13: car moves 3→2
      Tick 14: car moves 2→1
      Tick 15: car at target 1, stop begins
      Tick 16: stop_remaining 2→1
      Tick 17: stop_remaining 1→0, ALIGHT p2 (dropoff_tick=17)
    """

    def test_tick_values(self):
        building = _build(num_floors=5, num_cars=1)
        requests = [
            Request(id="p1", source=2, dest=4, time=0),
            Request(id="p2", source=3, dest=1, time=5),
        ]

        result = Engine(building, RoundRobin(), Look()).run(requests)

        assert result.complete
        by_id = {p.request.id: p for p in result.passengers}

        p1 = by_id["p1"]
        assert p1.pickup_tick == 3
        assert p1.dropoff_tick == 11

        p2 = by_id["p2"]
        assert p2.pickup_tick == 7
        assert p2.dropoff_tick == 17


class TestCompletenessValidation:
    """max_ticks too low to serve all passengers → incomplete result."""

    def test_unserved_passengers(self):
        building = _build(num_floors=10, num_cars=1)
        requests = [Request(id="p1", source=8, dest=10, time=0)]

        result = Engine(building, RoundRobin(), Look()).run(requests, max_ticks=3)

        assert not result.complete
        assert len(result.unserved) == 1
        assert result.unserved[0].request.id == "p1"
