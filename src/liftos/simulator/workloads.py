from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from liftos.models import Request


@dataclass(frozen=True)
class RatePhase:
    """A constant-rate segment within a :class:`RateSchedule`.

    *start* and *end* are fractions of total duration in [0, 1].
    """

    start: float
    end: float
    rate: float


class RateSchedule:
    """Piecewise-constant Poisson arrival rate over normalised time [0, 1].

    Phases must cover [0, 1] exactly, with no gaps or overlaps.
    """

    def __init__(self, phases: list[RatePhase]) -> None:
        phases = sorted(phases, key=lambda p: p.start)
        if phases[0].start != 0.0 or phases[-1].end != 1.0:
            raise ValueError("Phases must cover [0.0, 1.0]")
        for a, b in zip(phases, phases[1:]):
            if a.end != b.start:
                raise ValueError(f"Gap or overlap between phases at {a.end}")
        self.phases = phases

    @classmethod
    def constant(cls, rate: float) -> RateSchedule:
        """Single constant rate across the entire duration."""
        return cls([RatePhase(0.0, 1.0, rate)])

    def weighted_rate(self) -> float:
        """Duration-weighted average rate."""
        return sum(p.rate * (p.end - p.start) for p in self.phases)

    def expected_duration(self, num_passengers: int) -> float:
        """Estimated total simulation ticks for *num_passengers*."""
        return num_passengers / self.weighted_rate()

    def rate_at(self, t: float, total_duration: float) -> float:
        """Return the Poisson rate at absolute time *t*."""
        frac = t / total_duration if total_duration > 0 else 0.0
        for phase in self.phases:
            if phase.start <= frac < phase.end:
                return phase.rate
        # t is at or past the last boundary — use the final phase
        return self.phases[-1].rate


def _generate_arrivals(
    num_passengers: int,
    num_floors: int,
    schedule: RateSchedule,
    source_fn: callable,
    dest_fn: callable,
    rng: random.Random,
) -> list[Request]:
    """Generate requests using Poisson arrivals following *schedule*."""
    total_duration = schedule.expected_duration(num_passengers)
    requests: list[Request] = []
    t = 0.0
    for i in range(num_passengers):
        rate = schedule.rate_at(t, total_duration)
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

    return _generate_arrivals(
        num_passengers, num_floors, RateSchedule.constant(rate), source, dest, rng
    )


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

    return _generate_arrivals(
        num_passengers, num_floors, RateSchedule.constant(rate), source, dest, rng
    )


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

    return _generate_arrivals(
        num_passengers, num_floors, RateSchedule.constant(rate), source, dest, rng
    )


def stress(
    num_passengers: int,
    num_floors: int,
    seed: int,
    base_rate: float = 0.3,
    spike_multiplier: float = 2.0,
) -> list[Request]:
    """Load spike: baseline *base_rate* with a *spike_multiplier*x burst
    from 30% to 50% of total duration."""
    rng = random.Random(seed)

    spike_rate = base_rate * spike_multiplier
    schedule = RateSchedule([
        RatePhase(0.0, 0.3, base_rate),
        RatePhase(0.3, 0.5, spike_rate),
        RatePhase(0.5, 1.0, base_rate),
    ])

    def source(r: random.Random) -> int:
        return r.randint(1, num_floors)

    def dest(r: random.Random, src: int) -> int:
        d = src
        while d == src:
            d = r.randint(1, num_floors)
        return d

    return _generate_arrivals(
        num_passengers, num_floors, schedule, source, dest, rng
    )


WORKLOADS: dict[str, callable] = {
    "up_peak": up_peak,
    "down_peak": down_peak,
    "normal_hour": normal_hour,
    "stress": stress,
}
