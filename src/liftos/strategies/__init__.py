from liftos.strategies.adaptive import Adaptive
from liftos.strategies.nearest_car import NearestCar
from liftos.strategies.round_robin import RoundRobin

STRATEGIES: dict[str, type] = {
    "round_robin": RoundRobin,
    "nearest_car": NearestCar,
    "adaptive": Adaptive,
}

__all__ = ["STRATEGIES", "Adaptive", "NearestCar", "RoundRobin"]
