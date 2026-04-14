from liftos.models import Building, Car, Direction, Passenger, Request
from liftos.strategies.adaptive import Adaptive
from liftos.strategies.nearest_car import NearestCar
from liftos.strategies.round_robin import RoundRobin


def _req(id: str, source: int = 1, dest: int = 5) -> Request:
    return Request(id=id, source=source, dest=dest, time=0)


def _building(num_cars: int = 3) -> Building:
    cars = [Car(id=f"C{i}", floor=1, capacity=8) for i in range(num_cars)]
    return Building(num_floors=10, cars=cars)


class TestRoundRobin:
    def test_cycles_through_cars(self):
        building = _building(3)
        rr = RoundRobin()
        assigned = [rr.assign(_req(f"p{i}"), building).id for i in range(7)]
        assert assigned == ["C0", "C1", "C2", "C0", "C1", "C2", "C0"]

    def test_single_car(self):
        building = _building(1)
        rr = RoundRobin()
        assigned = [rr.assign(_req(f"p{i}"), building).id for i in range(3)]
        assert assigned == ["C0", "C0", "C0"]


class TestNearestCar:
    def test_picks_closest_car(self):
        cars = [
            Car(id="C0", floor=1, capacity=8),
            Car(id="C1", floor=5, capacity=8),
            Car(id="C2", floor=9, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        nc = NearestCar()

        assert nc.assign(_req("p1", source=4), building).id == "C1"
        assert nc.assign(_req("p2", source=1), building).id == "C0"
        assert nc.assign(_req("p3", source=10), building).id == "C2"

    def test_tie_breaks_by_car_id(self):
        cars = [
            Car(id="C0", floor=3, capacity=8),
            Car(id="C1", floor=7, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        nc = NearestCar()

        # source=5 is equidistant from floor 3 and floor 7
        assert nc.assign(_req("p1", source=5), building).id == "C0"


def _passenger(id: str, source: int, dest: int, car_id: str = "C0") -> Passenger:
    return Passenger(request=Request(id=id, source=source, dest=dest, time=0), car_id=car_id)


class TestAdaptive:
    def test_weights_must_sum_to_one(self):
        import pytest

        with pytest.raises(ValueError, match="must sum to 1.0"):
            Adaptive(w_eta=0.5, w_ride=0.5, w_load=0.5)

    def test_prefers_less_loaded_car(self):
        """With w_load=0.6, a nearby but loaded car loses to a farther empty one."""
        cars = [
            Car(id="C0", floor=3, capacity=4),  # close to source=4
            Car(id="C1", floor=7, capacity=4),  # farther from source=4
        ]
        # Load C0 to 3/4 capacity
        for i in range(3):
            cars[0].passengers.append(_passenger(f"x{i}", 1, 10, "C0"))
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive()

        result = adaptive.assign(_req("p1", source=4, dest=8), building)
        assert result.id == "C1"

    def test_prefers_closer_idle_car(self):
        """Two empty cars: closer one wins."""
        cars = [
            Car(id="C0", floor=1, capacity=8),
            Car(id="C1", floor=4, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive()

        result = adaptive.assign(_req("p1", source=5, dest=8), building)
        assert result.id == "C1"

    def test_scores_are_normalized(self):
        """All score components should be in [0, 1]."""
        cars = [Car(id="C0", floor=1, capacity=8)]
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive()

        adaptive.assign(_req("p1", source=5, dest=8), building)

        scores = adaptive.last_scores
        assert scores is not None
        assert 0.0 <= scores["eta"] <= 1.0
        assert 0.0 <= scores["ride"] <= 1.0
        assert 0.0 <= scores["load"] <= 1.0
        assert 0.0 <= scores["total"] <= 1.0

    def test_direction_aware_eta(self):
        """Car going UP away from source below should have higher ETA."""
        cars = [
            Car(id="C0", floor=5, capacity=8, direction=Direction.UP),
            Car(id="C1", floor=5, capacity=8, direction=Direction.DOWN),
        ]
        # Give both a target so they have a reason to be moving
        cars[0].passengers.append(_passenger("x0", 1, 10, "C0"))
        cars[1].passengers.append(_passenger("x1", 10, 1, "C1"))
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive(w_eta=1.0, w_ride=0.0, w_load=0.0)

        # source=3 is below both cars — C1 going DOWN should win
        result = adaptive.assign(_req("p1", source=3, dest=1), building)
        assert result.id == "C1"

    def test_load_includes_assigned_passengers(self):
        """Assigned passengers count toward load, preventing piling."""
        cars = [
            Car(id="C0", floor=1, capacity=4),
            Car(id="C1", floor=1, capacity=4),
        ]
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive()

        # Assign 3 passengers to C0 sequentially
        for i in range(3):
            car = adaptive.assign(_req(f"p{i}", source=3, dest=7), building)
            building.cars[building.cars.index(car)].assigned.append(
                _passenger(f"p{i}", 3, 7, car.id)
            )

        # 4th passenger: C0 has 3 assigned, C1 has 0 → should go to C1
        result = adaptive.assign(_req("p3", source=3, dest=7), building)
        assert result.id == "C1"

    def test_eta_overflow_when_over_capacity(self):
        """Car at capacity gets a round-trip penalty in ETA."""
        cars = [
            Car(id="C0", floor=1, capacity=2),  # close but full
            Car(id="C1", floor=8, capacity=2),  # far but empty
        ]
        # Fill C0: 2 onboard = at capacity
        cars[0].passengers = [
            _passenger("x0", 1, 5, "C0"),
            _passenger("x1", 1, 5, "C0"),
        ]
        building = Building(num_floors=10, cars=cars)
        # Use pure ETA weight so only distance matters
        adaptive = Adaptive(w_eta=1.0, w_ride=0.0, w_load=0.0)

        # C0 is 2 floors away but over capacity → round-trip penalty
        # C1 is 5 floors away but empty → should win
        result = adaptive.assign(_req("p1", source=3, dest=7), building)
        assert result.id == "C1"

    def test_deadline_penalty_fires_when_eta_exceeds_threshold(self):
        """Distant car gets deadline penalty, nearby car wins."""
        cars = [
            Car(id="C0", floor=1, capacity=8),   # ETA to floor 10 = 9
            Car(id="C1", floor=10, capacity=8),   # ETA to floor 10 = 0
        ]
        # num_floors=5 → deadline = 10. C0 ETA=9 < 10, no penalty.
        # But with num_floors=4 → deadline = 8. C0 ETA=9 > 8, penalty fires.
        building = Building(num_floors=4, cars=cars)
        adaptive = Adaptive(w_eta=0.0, w_ride=0.0, w_load=1.0)

        # With pure load weight and both empty, they'd tie → C0 wins by id.
        # But deadline penalty on C0 (ETA 9 > deadline 8) should push to C1.
        result = adaptive.assign(_req("p1", source=10, dest=1), building)
        assert result.id == "C1"

    def test_deadline_penalty_silent_under_threshold(self):
        """No penalty when ETA is within deadline."""
        cars = [Car(id="C0", floor=1, capacity=8)]
        building = Building(num_floors=10, cars=cars)
        adaptive = Adaptive()

        # ETA = 4 floors, deadline = 20 → no penalty
        adaptive.assign(_req("p1", source=5, dest=8), building)
        assert adaptive.last_scores["deadline"] == 0.0
