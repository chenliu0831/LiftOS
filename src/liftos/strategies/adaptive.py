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
        w_eta: float = 0.2,
        w_ride: float = 0.2,
        w_load: float = 0.6,
    ) -> None:
        total = w_eta + w_ride + w_load
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        self._w_eta = w_eta
        self._w_ride = w_ride
        self._w_load = w_load

    def assign(self, request: Request, building: Building) -> Car:
        best_car: Car | None = None
        best_score = float("inf")
        best_breakdown: dict[str, float] | None = None

        for car in building.cars:
            eta_raw = self._estimate_eta(car, request.source, building.num_floors)
            ride_raw = self._estimate_ride(car, request.source, request.dest)
            load_raw = len(car.passengers) / car.capacity if car.capacity > 0 else 1.0

            # Normalize to [0, 1]
            max_eta = 2 * building.num_floors
            norm_eta = min(eta_raw / max_eta, 1.0) if max_eta > 0 else 0.0

            max_ride = building.num_floors + len(car.passengers) * 2
            norm_ride = min(ride_raw / max_ride, 1.0) if max_ride > 0 else 0.0

            norm_load = load_raw  # already [0, 1]

            total = (
                self._w_eta * norm_eta
                + self._w_ride * norm_ride
                + self._w_load * norm_load
            )

            if total < best_score or (total == best_score and car.id < best_car.id):
                best_car = car
                best_score = total
                best_breakdown = {
                    "eta": round(norm_eta, 4),
                    "ride": round(norm_ride, 4),
                    "load": round(norm_load, 4),
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

        # Count pending stops between car and source in current direction
        targets = car.target_floors()
        match car.direction:
            case Direction.UP:
                if source >= car.floor:
                    stops_between = sum(
                        1 for f in targets if car.floor < f < source
                    )
                    return distance + stops_between * 2
                else:
                    # Car must go up, reverse, then come down to source
                    max_target = max(targets, default=car.floor)
                    up_distance = max_target - car.floor
                    stops_up = sum(
                        1 for f in targets if f > car.floor
                    )
                    down_distance = max_target - source
                    return up_distance + stops_up * 2 + down_distance

            case Direction.DOWN:
                if source <= car.floor:
                    stops_between = sum(
                        1 for f in targets if source < f < car.floor
                    )
                    return distance + stops_between * 2
                else:
                    min_target = min(targets, default=car.floor)
                    down_distance = car.floor - min_target
                    stops_down = sum(
                        1 for f in targets if f < car.floor
                    )
                    up_distance = source - min_target
                    return down_distance + stops_down * 2 + up_distance

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
