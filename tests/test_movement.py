from liftos.models import Car, Direction, Passenger, Request
from liftos.movement import Look, move_one_floor


def _passenger(id: str, source: int, dest: int, car_id: str = "C0") -> Passenger:
    return Passenger(request=Request(id=id, source=source, dest=dest, time=0), car_id=car_id)


look = Look()


class TestLookDirection:
    def test_idle_car_no_targets_stays_idle(self):
        car = Car(id="C0", floor=5, capacity=8)
        assert look.next_direction(car) is Direction.IDLE

    def test_idle_car_targets_above(self):
        car = Car(id="C0", floor=1, capacity=8)
        car.assigned = [_passenger("p1", 5, 10)]
        assert look.next_direction(car) is Direction.UP

    def test_idle_car_targets_below(self):
        car = Car(id="C0", floor=8, capacity=8)
        car.assigned = [_passenger("p1", 3, 1)]
        assert look.next_direction(car) is Direction.DOWN

    def test_continue_up_with_targets_ahead(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 10)]
        assert look.next_direction(car) is Direction.UP

    def test_reverse_when_no_targets_ahead(self):
        car = Car(id="C0", floor=10, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 10, 3)]
        assert look.next_direction(car) is Direction.DOWN

    def test_continue_down_with_targets_below(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.DOWN)
        car.passengers = [_passenger("p1", 8, 1)]
        assert look.next_direction(car) is Direction.DOWN

    def test_reverse_up_when_no_targets_below(self):
        car = Car(id="C0", floor=1, capacity=8, direction=Direction.DOWN)
        car.assigned = [_passenger("p1", 7, 10)]
        assert look.next_direction(car) is Direction.UP

    def test_idle_car_target_at_current_floor(self):
        car = Car(id="C0", floor=5, capacity=8)
        car.assigned = [_passenger("p1", 5, 10)]
        assert look.next_direction(car) is Direction.IDLE

    def test_idle_car_equidistant_targets_breaks_tie_downward(self):
        car = Car(id="C0", floor=5, capacity=8)
        car.assigned = [_passenger("p1", 3, 10), _passenger("p2", 7, 1)]
        assert look.next_direction(car) is Direction.DOWN

    def test_up_ignores_targets_behind(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 8, 2)]  # dest=2 is behind
        car.assigned = [_passenger("p2", 8, 10)]   # source=8 is ahead
        assert look.next_direction(car) is Direction.UP

    def test_down_ignores_targets_behind(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.DOWN)
        car.passengers = [_passenger("p1", 2, 9)]  # dest=9 is behind
        car.assigned = [_passenger("p2", 2, 1)]    # source=2 is ahead
        assert look.next_direction(car) is Direction.DOWN


class TestMove:
    def test_moves_up(self):
        car = Car(id="C0", floor=3, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 1, 7)]
        move_one_floor(car, look)
        assert car.floor == 4
        assert car.direction is Direction.UP

    def test_moves_down(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.DOWN)
        car.passengers = [_passenger("p1", 8, 1)]
        move_one_floor(car, look)
        assert car.floor == 4
        assert car.direction is Direction.DOWN

    def test_no_move_when_idle_no_targets(self):
        car = Car(id="C0", floor=5, capacity=8)
        move_one_floor(car, look)
        assert car.floor == 5

    def test_no_move_when_target_at_current_floor(self):
        car = Car(id="C0", floor=5, capacity=8, direction=Direction.UP)
        car.assigned = [_passenger("p1", 5, 10)]
        move_one_floor(car, look)
        assert car.floor == 5
        assert car.direction is Direction.UP

    def test_reversal_updates_direction(self):
        car = Car(id="C0", floor=10, capacity=8, direction=Direction.UP)
        car.passengers = [_passenger("p1", 10, 3)]
        move_one_floor(car, look)
        assert car.floor == 9
        assert car.direction is Direction.DOWN

    def test_idle_car_starts_moving_toward_assigned(self):
        car = Car(id="C0", floor=1, capacity=8)
        car.assigned = [_passenger("p1", 5, 10)]
        move_one_floor(car, look)
        assert car.floor == 2
        assert car.direction is Direction.UP
