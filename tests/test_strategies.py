from liftos.models import Building, Car, Request
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
