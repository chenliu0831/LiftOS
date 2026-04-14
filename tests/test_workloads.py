from liftos.simulator.workloads import down_peak, normal_hour, stress, up_peak


NUM_PASSENGERS = 200
NUM_FLOORS = 20
SEED = 42


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
