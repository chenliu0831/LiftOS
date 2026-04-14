import pytest

from liftos.simulator.workloads import (
    RatePhase,
    RateSchedule,
    down_peak,
    normal_hour,
    stress,
    up_peak,
)


NUM_PASSENGERS = 200
NUM_FLOORS = 20
SEED = 42


# -- RateSchedule unit tests -------------------------------------------------


class TestRateSchedule:
    def test_constant(self):
        s = RateSchedule.constant(0.5)
        assert len(s.phases) == 1
        assert s.weighted_rate() == 0.5
        assert s.expected_duration(100) == pytest.approx(200.0)

    def test_multi_phase_weighted_rate(self):
        s = RateSchedule([
            RatePhase(0.0, 0.3, 0.3),
            RatePhase(0.3, 0.5, 0.6),
            RatePhase(0.5, 1.0, 0.3),
        ])
        # 0.3*0.3 + 0.2*0.6 + 0.5*0.3 = 0.09 + 0.12 + 0.15 = 0.36
        assert s.weighted_rate() == pytest.approx(0.36)

    def test_rate_at(self):
        s = RateSchedule([
            RatePhase(0.0, 0.5, 1.0),
            RatePhase(0.5, 1.0, 2.0),
        ])
        assert s.rate_at(0.0, 100.0) == 1.0
        assert s.rate_at(25.0, 100.0) == 1.0
        assert s.rate_at(50.0, 100.0) == 2.0
        assert s.rate_at(75.0, 100.0) == 2.0
        # At or past end — returns last phase rate
        assert s.rate_at(100.0, 100.0) == 2.0

    def test_gap_rejected(self):
        with pytest.raises(ValueError, match="Gap or overlap"):
            RateSchedule([
                RatePhase(0.0, 0.4, 1.0),
                RatePhase(0.6, 1.0, 1.0),
            ])

    def test_incomplete_coverage_rejected(self):
        with pytest.raises(ValueError, match="cover"):
            RateSchedule([RatePhase(0.0, 0.5, 1.0)])


# -- Workload property tests --------------------------------------------------


class TestWorkloadProperties:
    """Verify each generator produces valid, deterministic requests."""

    def _check_common(self, requests):
        assert len(requests) == NUM_PASSENGERS
        for req in requests:
            assert 1 <= req.source <= NUM_FLOORS
            assert 1 <= req.dest <= NUM_FLOORS
            assert req.source != req.dest
            assert req.time >= 0
        # Times are non-decreasing
        times = [r.time for r in requests]
        assert times == sorted(times)

    def test_up_peak(self):
        reqs = up_peak(NUM_PASSENGERS, NUM_FLOORS, SEED)
        self._check_common(reqs)
        # Majority should originate at floor 1
        ground_count = sum(1 for r in reqs if r.source == 1)
        assert ground_count > NUM_PASSENGERS * 0.6

    def test_down_peak(self):
        reqs = down_peak(NUM_PASSENGERS, NUM_FLOORS, SEED)
        self._check_common(reqs)
        # All destinations should be floor 1
        assert all(r.dest == 1 for r in reqs)

    def test_normal_hour(self):
        reqs = normal_hour(NUM_PASSENGERS, NUM_FLOORS, SEED)
        self._check_common(reqs)
        # Should use more than just a few floors
        sources = {r.source for r in reqs}
        assert len(sources) > NUM_FLOORS // 2

    def test_stress(self):
        reqs = stress(NUM_PASSENGERS, NUM_FLOORS, SEED)
        self._check_common(reqs)

    def test_stress_has_three_phases(self):
        """Burst at 30-50% should produce passengers in all three phases."""
        reqs = stress(2000, NUM_FLOORS, SEED)
        times = [r.time for r in reqs]

        base = 0.3
        spike = base * 2.0
        schedule = RateSchedule([
            RatePhase(0.0, 0.3, base),
            RatePhase(0.3, 0.5, spike),
            RatePhase(0.5, 1.0, base),
        ])
        T = schedule.expected_duration(2000)

        before = sum(1 for t in times if t < T * 0.3)
        during = sum(1 for t in times if T * 0.3 <= t < T * 0.5)
        after = sum(1 for t in times if t >= T * 0.5)

        # All three phases must have meaningful traffic
        assert before > 100
        assert during > 100
        assert after > 100


class TestDeterminism:
    def test_same_seed_same_output(self):
        a = up_peak(100, 10, seed=99)
        b = up_peak(100, 10, seed=99)
        assert [(r.time, r.source, r.dest) for r in a] == [
            (r.time, r.source, r.dest) for r in b
        ]

    def test_different_seed_different_output(self):
        a = up_peak(100, 10, seed=1)
        b = up_peak(100, 10, seed=2)
        a_tuples = [(r.time, r.source, r.dest) for r in a]
        b_tuples = [(r.time, r.source, r.dest) for r in b]
        assert a_tuples != b_tuples
