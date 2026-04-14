# LiftOS Design Intake — Open Questions

Questions grouped by topic. Where I have a leaning, I've marked it with *default assumption*. Push back or confirm and we can move on.

---

## 1. Simulation Mechanics

**1a. Stop cost when already stopped.**
If an elevator is already idle at floor 5 and a newly-assigned passenger is also on floor 5, does it still pay the 2-tick stop cost to board them?
*Default assumption:* Yes — the 2-tick cost represents door-open/close and is always paid. 

**1b. Capacity overflow.**
A car arrives at a floor where an assigned passenger is waiting, but it's full. What happens?
- The passenger waits at the floor until the same car returns with room?
- The passenger is re-assigned to another car?

*Default assumption:* Passenger waits for their assigned car. Re-assignment is V2. 

**1c. Idle behavior.**
When a car has no pending stops, should it: stay in place, return to ground, or park at a configured "home" floor?
*Default assumption:* Stay in place.

**Answer**: Stay in place is a safe default. Let's support a simple heuristic to return a floor of the most demand and make sure no more than 30% of the cars are idle at the same floor. 

**1d. Initial positions.**
Where do elevators start at tick 0? All at ground floor, or configurable per-car?
*Default assumption:* All at floor 1.

---

## 2. Scheduling & Assignment

**2a. Re-assignment.**
The spec says assignment is immediate. Can the system later re-assign a waiting (not yet picked up) passenger to a different car, or is assignment permanent?
*Default assumption:* Permanent. Simpler to reason about and log.

**2b. Baseline strategies.**
"Nearest-car" and "round-robin" are listed as examples. Should we treat those as the two required baselines, or pick different ones?
*Default assumption:* Use exactly those two.

**2c. Adaptive strategy — scope.**
How smart should the adaptive algorithm be? Options range from a simple weighted scorer (distance + load + direction alignment) to something like a look-ahead cost estimator. The spec says "uses global state" which suggests a scorer, not a planner.
*Default assumption:* Weighted scorer considering direction alignment, distance, and current load. No combinatorial search.

**Answer**: Let's use a weighted scorer apporach with a bias to minimize total trip time (not just pickup time).

**2d. Invalid requests.**
Should we guard against `source == dest` requests, or assume workload generators won't produce them?
*Default assumption:* Silently drop them in the core; never generate them in the simulator.

**Answer**: Yes this should not happen. 

---

## 3. Floor Numbering

**3a.** Is the ground floor `0` or `1`?
*Default assumption:* `1`. A 10-floor building has floors 1–10.

---

## 4. Workloads

**4a. Stress workload — "two arrival patterns".**
The spec says Stress "uses one of the two arrival patterns below" but only describes SpikeLoadGenerator. What's the second pattern? Possibilities:
- A sustained high-rate (no spike, just constant overload).
- A periodic burst (multiple spikes).

*Default assumption:* Implement SpikeLoadGenerator only. Add the second if you have something specific in mind.

**4b. Poisson rates.**
Are base arrival rates (λ) configurable per workload, or should we pick sensible defaults?
*Default assumption:* Ship sensible defaults, expose as CLI overrides.

**4c. Destination distributions.**
- UpPeak: what fraction of passengers originate at ground? 80%? 90%? Or just "heavily weighted"?
- DownPeak: are origin floors uniformly distributed?
- NormalHour: uniform random source and dest?

*Default assumption:* UpPeak ~80% ground origin, DownPeak uniform origin → ground, NormalHour uniform random. All tunable.

**Answer**: Looks good to me.

**4d. Reproducibility.**
Should workload generation accept a random seed for deterministic replay?
*Default assumption:* Yes — required for meaningful algorithm comparison.

---

## 5. CLI & Output

**5a. CLI parameters.**
The spec mentions "configurable floor count and passenger count." Should we also expose:
- Number of elevators?
- Capacity?
- Algorithm selection?
- Workload type?
- Output directory?

*Default assumption:* All of the above.

**5b. Chart output.**
Save to files (PNG) or display interactively, or both?
*Default assumption:* Save to the output directory as PNGs. No interactive display.

**5c. Comparison mode.**
Should the CLI support running multiple algorithms against the same workload in one invocation (for side-by-side charts)?
*Default assumption:* Yes — this is the main value of the simulator.

---

## 6. Log Formats

**6a. Elevator log schema.**
Proposed: `tick,car_id,floor,direction,passenger_count`
Anything else needed for the future visualizer?

**6b. Passenger log schema.**
Proposed: `id,source,dest,request_tick,pickup_tick,dropoff_tick,wait_time,total_time,car_id`
The derived fields (`wait_time`, `total_time`) are redundant but convenient. Include them?
*Default assumption:* Yes, include for convenience.

**Answer**: No, do not include the derived fields.

**6c. File format.**
CSV for both logs?
*Default assumption:* Yes.

**Answer**: Use JSON Lines (JSONL) format.

---

## 7. V2 Guardrails

**7a.** The visualizer will need to replay from logs. Does the proposed elevator log schema (6a) have enough state, or do we need to also log door-open/close events, passenger board/alight events?
*Default assumption:* The V1 log is enough. We can enrich it in V2 without breaking the V1 format if we only append columns.

**Answer**: I don't think we need them.
---

**Next step:** Once we've settled these, I'll draft `design.md`.
