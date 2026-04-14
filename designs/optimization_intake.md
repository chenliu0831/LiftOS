# Optimization Intake

Questions to resolve before implementing deadline-aware scoring. Answer inline.

---

### 1. Pickup deadline value

The doc proposes 150 ticks (round-robin's stress p95).

**Should the deadline be configurable per-run (CLI flag), or is a hardcoded default sufficient for now?**

> hardcoded default is good. 

**Should the deadline scale with building size (e.g., `num_floors * N`), or stay absolute?**

> yes let's scale with the building size. `num_floors * 2` can be a reasonble start.

### 2. Penalty magnitude

When a car's estimated ETA exceeds the pickup deadline, its score gets a penalty. The penalty needs to be large enough to steer assignment away from that car, but not so large that it creates new pathologies (e.g., all passengers piling onto one nearby car).

**Should the penalty be a fixed constant (e.g., score += 10.0), or proportional to how far the ETA exceeds the deadline (e.g., `score += overdue_ratio * weight`)?**

> proportional to how far the ETA exceeds the deadline

### 3. Dropoff deadline behavior

The doc says the scorer penalizes cars with onboard passengers nearing dropoff deadline.

**What should the dropoff deadline value be?** Options:
- (a) Same as pickup deadline (150 ticks from request time).
- (b) A multiple of pickup deadline (e.g., 2x, since dropoff includes travel).
- (c) Derived from expected ride time (e.g., `ride_estimate + buffer`).

> Derived from expected ride time

**Should the penalty affect assignment only (don't pile work onto overloaded cars), or also affect movement (car prioritizes overdue dropoffs)?**

> assignment only

### 4. Success criteria

The gap: adaptive stress p95 is 176 wait / 204 total vs. round-robin's 151 / 178.

**What's the target?** Options:
- (a) Match round-robin's stress p95 (~150 wait, ~178 total) while keeping adaptive's mean.
- (b) Close the gap meaningfully (e.g., within 10% of round-robin p95).
- (c) Beat round-robin on both mean and p95 across all workloads.

> (b)

### 5. Rollout scope

The plan is to add deadline penalty to the existing adaptive scorer, not create a new strategy.

**Should this be a new strategy (`deadline_adaptive`) alongside the current `adaptive`, or should we modify `adaptive` in place?** Keeping both lets us A/B compare; modifying in place keeps the strategy list clean.

> Keep it in adaptive.
