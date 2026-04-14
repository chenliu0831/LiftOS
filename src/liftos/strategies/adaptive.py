from __future__ import annotations

from liftos.models import Building, Car, Direction, Request


class Adaptive:
    """Weighted scorer biased toward minimizing total trip time.

    Scores each car on three normalized [0,1] components:
      eta:  estimated ticks to reach passenger's source floor
      ride: estimated ticks from source to dest once aboard
      load: current occupancy ratio

    Weights must sum to 1.0. Lowest total score wins.
    """

    def __init__(
        self,
        w_eta: float = 0.4,
        w_ride: float = 0.2,
        w_load: float = 0.4,
        w_deadline: float = 1.0,
        deadline_mult: float = 0.75,
    ) -> None:
        total = w_eta + w_ride + w_load
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        self._w_eta = w_eta
        self._w_ride = w_ride
        self._w_load = w_load
        self._w_deadline = w_deadline
        self._deadline_mult = deadline_mult

    def assign(self, request: Request, building: Building) -> Car:
        best_car: Car | None = None
        best_score = float("inf")
        best_breakdown: dict[str, float] | None = None

        pickup_deadline = building.num_floors * self._deadline_mult

        for car in building.cars:
            eta_raw = self._estimate_eta(car, request.source, building.num_floors)
            ride_raw = self._estimate_ride(car, request.source, request.dest)

            # Include assigned passengers in load — prevents piling
            committed = len(car.passengers) + len(car.assigned)
            load_raw = committed / car.capacity if car.capacity > 0 else 1.0

            # Capacity overflow — passenger won't board on first visit
            if committed >= car.capacity:
                eta_raw += 2 * building.num_floors

            # Normalize to [0, 1]
            max_eta = 2 * building.num_floors
            norm_eta = min(eta_raw / max_eta, 1.0) if max_eta > 0 else 0.0

            max_ride = building.num_floors + len(car.passengers) * 2
            norm_ride = min(ride_raw / max_ride, 1.0) if max_ride > 0 else 0.0

            norm_load = min(load_raw, 1.0)

            total = (
                self._w_eta * norm_eta
                + self._w_ride * norm_ride
                + self._w_load * norm_load
            )

            # Pickup deadline penalty
            deadline_penalty = 0.0
            if pickup_deadline > 0 and eta_raw > pickup_deadline:
                overdue_ratio = (eta_raw - pickup_deadline) / pickup_deadline
                deadline_penalty = overdue_ratio * self._w_deadline
                total += deadline_penalty

            if total < best_score or (total == best_score and car.id < best_car.id):
                best_car = car
                best_score = total
                best_breakdown = {
                    "eta": round(norm_eta, 4),
                    "ride": round(norm_ride, 4),
                    "load": round(norm_load, 4),
                    "deadline": round(deadline_penalty, 4),
                    "total": round(total, 4),
                }

        # Attach scores to be picked up by the dispatch logger.
        # The engine sets car_id and appends to assigned list.
        self._last_scores = best_breakdown
        return best_car  # type: ignore[return-value]

    @property
    def last_scores(self) -> dict[str, float] | None:
        return self._last_scores

    def _estimate_eta(self, car: Car, source: int, num_floors: int) -> float:
        """Estimate ticks for car to reach source floor."""
        distance = abs(car.floor - source)

        if car.direction is Direction.IDLE:
            return distance

        targets = car.target_floors()
        match car.direction:
            case Direction.UP:
                if source >= car.floor:
                    stops = sum(1 for f in targets if car.floor < f < source)
                    return distance + stops * 2
                else:
                    turnaround = max(
                        (f for f in targets if f > car.floor),
                        default=car.floor,
                    )
                    stops_fwd = sum(1 for f in targets if f > car.floor)
                    stops_rev = sum(
                        1 for f in targets if source < f < car.floor
                    )
                    return (
                        (turnaround - car.floor)
                        + stops_fwd * 2
                        + (turnaround - source)
                        + stops_rev * 2
                    )

            case Direction.DOWN:
                if source <= car.floor:
                    stops = sum(1 for f in targets if source < f < car.floor)
                    return distance + stops * 2
                else:
                    turnaround = min(
                        (f for f in targets if f < car.floor),
                        default=car.floor,
                    )
                    stops_fwd = sum(1 for f in targets if f < car.floor)
                    stops_rev = sum(
                        1 for f in targets if car.floor < f < source
                    )
                    return (
                        (car.floor - turnaround)
                        + stops_fwd * 2
                        + (source - turnaround)
                        + stops_rev * 2
                    )

        return distance  # fallback

    def _estimate_ride(self, car: Car, source: int, dest: int) -> float:
        """Estimate ticks from source to dest once passenger is aboard."""
        direct_distance = abs(dest - source)
        # Estimate intermediate stops: passengers on board whose dest
        # is between source and dest
        if dest > source:
            intermediate_stops = sum(
                1 for p in car.passengers if source < p.request.dest < dest
            )
        else:
            intermediate_stops = sum(
                1 for p in car.passengers if dest < p.request.dest < source
            )
        return direct_distance + intermediate_stops * 2
