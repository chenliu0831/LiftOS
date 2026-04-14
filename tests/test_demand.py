from liftos.demand import DemandTracker, redistribute_target
from liftos.models import Building, Car


class TestDemandTracker:
    def test_ranking_by_frequency(self):
        tracker = DemandTracker()
        for _ in range(5):
            tracker.record(1)
        for _ in range(2):
            tracker.record(3)
        for _ in range(8):
            tracker.record(7)
        assert tracker.demand_ranking() == [7, 1, 3]

    def test_empty_tracker(self):
        tracker = DemandTracker()
        assert tracker.demand_ranking() == []


class TestRedistributeTarget:
    def test_picks_highest_demand_floor(self):
        building = Building(
            num_floors=10,
            cars=[Car(id="C0", floor=5, capacity=8)],
        )
        tracker = DemandTracker()
        for _ in range(10):
            tracker.record(1)
        for _ in range(3):
            tracker.record(7)

        target = redistribute_target(building.cars[0], building, tracker)
        assert target == 1

    def test_skips_floor_at_cap(self):
        """With 4 cars and 2 already idle at floor 1, floor 1 is at 50% cap."""
        cars = [
            Car(id="C0", floor=1, capacity=8),  # idle at floor 1
            Car(id="C1", floor=1, capacity=8),  # idle at floor 1
            Car(id="C2", floor=5, capacity=8),  # the car we're redistributing
            Car(id="C3", floor=8, capacity=8),
        ]
        building = Building(num_floors=10, cars=cars)
        tracker = DemandTracker()
        for _ in range(10):
            tracker.record(1)
        for _ in range(5):
            tracker.record(3)

        # Floor 1 has 2 idle cars, cap is 4*0.5=2 → 2 < 2 is False → skip
        target = redistribute_target(cars[2], building, tracker)
        assert target == 3

    def test_returns_none_when_no_demand(self):
        building = Building(
            num_floors=10,
            cars=[Car(id="C0", floor=5, capacity=8)],
        )
        tracker = DemandTracker()
        assert redistribute_target(building.cars[0], building, tracker) is None
