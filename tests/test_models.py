from liftos.models import Building, Car, Direction, Passenger, Request


def _req(id: str, source: int, dest: int, time: int = 0) -> Request:
    return Request(id=id, source=source, dest=dest, time=time)


def _passenger(id: str, source: int, dest: int, car_id: str = "C0") -> Passenger:
    return Passenger(request=_req(id, source, dest), car_id=car_id)


class TestCarTargetFloors:
    def test_empty_car_has_no_targets(self):
        car = Car(id="C0", floor=1, capacity=8)
        assert car.target_floors() == set()

    def test_onboard_passengers_add_dest_floors(self):
        car = Car(id="C0", floor=3, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 7), _passenger("p2", 2, 10)]
        assert car.target_floors() == {7, 10}

    def test_assigned_passengers_add_source_floors(self):
        car = Car(id="C0", floor=1, capacity=8, direction=Direction.UP)
        car.assigned = [_passenger("p1", 5, 10), _passenger("p2", 3, 8)]
        assert car.target_floors() == {5, 3}

    def test_mixed_onboard_and_assigned(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 10)]
        car.assigned = [_passenger("p2", 7, 2)]
        assert car.target_floors() == {10, 7}

    def test_full_car_excludes_pickup_floors(self):
        car = Car(id="C0", floor=1, capacity=2, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 5), _passenger("p2", 1, 8)]
        car.assigned = [_passenger("p3", 3, 10)]
        # Car is full (2/2) — pickup floor 3 should be excluded
        assert car.target_floors() == {5, 8}

    def test_full_car_still_includes_dropoff_floors(self):
        car = Car(id="C0", floor=1, capacity=1, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 5)]
        car.assigned = [_passenger("p2", 5, 10)]
        # Full, but floor 5 is both a dropoff and a pickup — included via dropoff
        assert car.target_floors() == {5}


class TestCarState:
    def test_idle_when_empty_and_no_work(self):
        car = Car(id="C0", floor=1, capacity=8)
        assert car.is_idle is True

    def test_not_idle_with_assigned_passengers(self):
        car = Car(id="C0", floor=1, capacity=8)
        car.assigned = [_passenger("p1", 3, 7)]
        assert car.is_idle is False

    def test_not_idle_with_onboard_passengers(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 10)]
        assert car.is_idle is False

    def test_not_idle_when_stopping(self):
        car = Car(id="C0", floor=5, capacity=8, stop_remaining=1)
        assert car.is_idle is False

    def test_remaining_capacity(self):
        car = Car(id="C0", floor=1, capacity=4)
        car.passengers = [_passenger("p1", 1, 5)]
        assert car.remaining_capacity == 3


class TestBuilding:
    def test_idle_cars(self):
        cars = [
            Car(id="C0", floor=1, capacity=8),
            Car(id="C1", floor=5, capacity=8, direction=Direction.UP),
            Car(id="C2", floor=3, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        idle = building.idle_cars()
        assert [c.id for c in idle] == ["C0", "C2"]

    def test_idle_count_at_floor(self):
        cars = [
            Car(id="C0", floor=1, capacity=8),
            Car(id="C1", floor=1, capacity=8),
            Car(id="C2", floor=5, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        assert building.idle_count_at(1) == 2
        assert building.idle_count_at(5) == 1
        assert building.idle_count_at(3) == 0
