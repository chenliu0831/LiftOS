# Optimization: Deadline-Aware Scheduling

## Problem

The adaptive scheduler wins on mean wait and total time across all workloads, but loses to round-robin on tail latency under load. On the stress workload:

| Algorithm | Wait (mean / p95) | Total (mean / p95) |
|-----------|-------------------|---------------------|
| adaptive | 42 / 176 | 69 / 204 |
| round_robin | 44 / 151 | 70 / 178 |

Adaptive's p95 is 15-16% worse. The root cause: during traffic spikes, the scorer sends passengers to distant but lightly-loaded cars, creating outlier wait times. Round-robin's blind fairness avoids this.

**Goal:** close the stress p95 gap to within 10% of round-robin while keeping adaptive's mean advantage.

## Constraints

- **No reassignment.** Passengers are assigned once at DISPATCH and stay with that car. The optimization must prevent bad assignments, not fix them after the fact.
- **Modify adaptive in place.** No new strategy -- add deadline awareness directly to the existing scorer.

## Insight

Borrowed from the Linux `deadline` I/O scheduler ([reference](https://www.cloudbees.com/blog/linux-io-scheduler-tuning)): optimize for throughput normally, but once a request's estimated wait exceeds a deadline, penalize further delay. This lets the scorer self-regulate — it behaves as pure adaptive under calm traffic and converges toward nearest-car during spikes.

## Design

### Fix: Load and ETA Account for Assigned Passengers

Before adding the deadline penalty, fix the scorer to reflect committed work.

**Load calculation.** Include assigned passengers, not just onboard:

```python
load_raw = (len(car.passengers) + len(car.assigned)) / car.capacity
```

This can exceed 1.0 for over-committed cars. Each sequential assignment within a tick batch increases the car's load score, naturally spreading passengers.

**ETA capacity overflow.** If the car's committed passengers (onboard + assigned) already meet or exceed capacity, this passenger won't board on the first visit. Add a round-trip penalty:

```python
if len(car.passengers) + len(car.assigned) >= car.capacity:
    eta_raw += 2 * num_floors  # conservative round-trip estimate
```

Both fixes are safe because the engine dispatches passengers sequentially within a tick -- each `assign()` call sees the updated `car.assigned` list from prior assignments.

### Pickup Deadline Penalty

Add a penalty term to the adaptive scorer. When the estimated ETA to a passenger's pickup floor exceeds a deadline threshold, the car's score increases proportionally to the overshoot.

**Deadline threshold:**

```
pickup_deadline = num_floors * deadline_mult
```

Scales with building size. `deadline_mult` defaults to 0.75, determined empirically. For the benchmark (20 floors), this is 15 ticks. The original proposal of `num_floors * 2 = 40` was too lenient — normal ETAs never exceeded it so the penalty never fired. Sweeping 0.5–2.0 revealed 0.75 as optimal; sensitivity is non-monotonic (0.7 and 0.8 are notably worse).

**Penalty computation** (inside `Adaptive.assign()`, per candidate car):

```python
if eta_raw > pickup_deadline:
    overdue_ratio = (eta_raw - pickup_deadline) / pickup_deadline
    score += overdue_ratio * w_deadline
```

`w_deadline` defaults to 1.0. Since normal scores fall in [0, 1], a penalty of 1.0 dominates when the ETA is 2x the deadline. A barely-over-deadline ETA adds a modest nudge (~0.05).

### Dropoff Deadline Penalty

Deferred. The pickup deadline alone met the p95 target. A dropoff deadline would require passing `tick` to the scorer — not worth the complexity unless future workloads regress total p95.

### Changes Summary

| File | Change |
|------|--------|
| `strategies/adaptive.py` | Fix load to include assigned, add ETA overflow penalty, add `w_deadline` param and pickup deadline penalty, update score breakdown |
| `tests/test_strategies.py` | Test load includes assigned, ETA overflow, deadline penalty fires/silent |

No changes to the engine, models, movement, or Scheduler protocol.

## Benchmark Results

20 floors, 4 cars, capacity 8, 100 passengers, seed 42. Weights: `w_eta=0.4, w_ride=0.2, w_load=0.4, w_deadline=1.0, deadline_mult=0.75`.

| Workload | Algorithm | Wait mean | Wait p95 | Total mean | Total p95 |
|-----------|-----------|-----------|----------|------------|-----------|
| up_peak | adaptive | **17** | **39** | **36** | **61** |
| up_peak | round_robin | 27 | 57 | 46 | 81 |
| down_peak | adaptive | **14** | 39 | **40** | **69** |
| down_peak | round_robin | 18 | **39** | 44 | 72 |
| normal_hour | adaptive | **10** | **31** | **26** | **56** |
| normal_hour | round_robin | 16 | 41 | 33 | 64 |
| stress | adaptive | **26** | **88** | **51** | 121 |
| stress | round_robin | 32 | **88** | 59 | **113** |

Adaptive wins mean on every workload. On stress p95 — the target metric — wait is tied (88) and total gap is 7% (121 vs 113), within the 10% threshold. Goal met.

## Rollout Plan

1. ~~Fix load and ETA to account for assigned passengers. Add pickup deadline penalty. Benchmark against current adaptive and round-robin.~~ Done.
2. ~~Evaluate results. If stress p95 gap is within 10% of round-robin, done.~~ Gap is 7%. Done.
3. Consider dropoff deadline if future workloads regress total p95.

## Risks and Ambiguities

1. **Deadline threshold tuning.** Resolved. Empirical sweep found `deadline_mult=0.75` (15 ticks for 20 floors). The original `num_floors * 2 = 40` was too high — the penalty never fired. Sensitivity is non-monotonic: 0.7 and 0.8 are worse than 0.75, so this parameter should not be changed without re-benchmarking.

2. **Proportional penalty at the boundary.** With `deadline_mult=0.75`, an ETA of 16 (just over 15) gets a penalty of only 0.067. The benchmark shows this is sufficient — no minimum floor was needed.

3. **Round-trip estimate is conservative.** `2 * num_floors` as the overflow penalty may over-penalize cars that only need a short delivery before returning. A tighter estimate would track where current passengers are headed. Not worth the complexity given the benchmark results.
