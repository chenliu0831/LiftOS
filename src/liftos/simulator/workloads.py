from __future__ import annotations

import json
import math
import random
from pathlib import Path

from liftos.models import Request


def _generate_arrivals(
    num_passengers: int,
    num_floors: int,
    rate: float,
    source_fn: callable,
    dest_fn: callable,
    rng: random.Random,
) -> list[Request]:
    """Generate requests using Poisson arrivals with given source/dest distributions."""
    requests: list[Request] = []
    t = 0.0
    for i in range(num_passengers):
        t += rng.expovariate(rate)
        source = source_fn(rng)
        dest = dest_fn(rng, source)
        requests.append(
            Request(
                id=f"p-{i:04d}",
                source=source,
                dest=dest,
                time=math.ceil(t),
            )
        )
    return requests


def up_peak(
    num_passengers: int,
    num_floors: int,
    seed: int,
    rate: float = 0.5,
    ground_fraction: float = 0.8,
) -> list[Request]:
    """Morning rush: most passengers originate at ground floor."""
    rng = random.Random(seed)

    def source(r: random.Random) -> int:
        if r.random() < ground_fraction:
            return 1
        return r.randint(2, num_floors)

    def dest(r: random.Random, src: int) -> int:
        d = src
        while d == src:
            d = r.randint(1, num_floors)
        return d

    return _generate_arrivals(num_passengers, num_floors, rate, source, dest, rng)


def down_peak(
    num_passengers: int,
    num_floors: int,
    seed: int,
    rate: float = 0.5,
) -> list[Request]:
    """Evening rush: passengers from upper floors travel to ground."""
    rng = random.Random(seed)

    def source(r: random.Random) -> int:
        return r.randint(2, num_floors)

    def dest(_r: random.Random, _src: int) -> int:
        return 1

    return _generate_arrivals(num_passengers, num_floors, rate, source, dest, rng)


def normal_hour(
    num_passengers: int,
    num_floors: int,
    seed: int,
    rate: float = 0.3,
) -> list[Request]:
    """Mid-day: passengers travel between arbitrary floors."""
    rng = random.Random(seed)

    def source(r: random.Random) -> int:
        return r.randint(1, num_floors)

    def dest(r: random.Random, src: int) -> int:
        d = src
        while d == src:
            d = r.randint(1, num_floors)
        return d

    return _generate_arrivals(num_passengers, num_floors, rate, source, dest, rng)


def stress(
    num_passengers: int,
    num_floors: int,
    seed: int,
    base_rate: float = 0.3,
    spike_rate: float = 2.0,
    spike_start_frac: float = 0.3,
    spike_duration_frac: float = 0.2,
) -> list[Request]:
    """Spike load: base rate with a sudden burst in the middle.

    Generates requests at base_rate, switches to spike_rate for the
    spike window, then drops back to base_rate.
    """
    rng = random.Random(seed)

    # Estimate total duration to place the spike window
    avg_duration = num_passengers / base_rate
    spike_start = avg_duration * spike_start_frac
    spike_end = spike_start + avg_duration * spike_duration_frac

    def source(r: random.Random) -> int:
        return r.randint(1, num_floors)

    def dest(r: random.Random, src: int) -> int:
        d = src
        while d == src:
            d = r.randint(1, num_floors)
        return d

    requests: list[Request] = []
    t = 0.0
    for i in range(num_passengers):
        rate = spike_rate if spike_start <= t < spike_end else base_rate
        t += rng.expovariate(rate)
        src = source(rng)
        dst = dest(rng, src)
        requests.append(
            Request(
                id=f"p-{i:04d}",
                source=src,
                dest=dst,
                time=math.ceil(t),
            )
        )

    return requests


WORKLOADS: dict[str, callable] = {
    "up_peak": up_peak,
    "down_peak": down_peak,
    "normal_hour": normal_hour,
    "stress": stress,
}
