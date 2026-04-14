# LiftOS — System Design (V1)

## Overview

LiftOS is a destination-dispatch elevator system with a discrete-event simulation harness. Two components:

- **LiftOS Core** — receives passenger requests, assigns each to a car, and drives car movement tick-by-tick.
- **Lift Simulator** — generates workloads, feeds them through Core, and produces comparison charts.

Both live in a single Python package (`liftos`). Separation is at the module level; the simulator imports from core, never the reverse.

---

## Domain Model

```
Direction  = Literal["up", "down", "idle"]

Request    { id: str, source: int, dest: int, time: int }
Passenger  { request: Request, pickup_tick: int | None, dropoff_tick: int | None, car_id: str }
Car        { id: str, floor: int, direction: Direction,
             passengers: list[Passenger],          # on board
             assigned: list[Passenger],             # waiting at their source floor
             capacity: int, stop_remaining: int }
Building   { num_floors: int, cars: list[Car] }
```

Floors are 1-indexed. A 10-floor building has floors 1–10, where 1 is ground.

---

## Tick Processing

Every tick executes this sequence for the entire building. Order matters.

```
1. INSERT   — All requests whose time == current_tick become Passengers.
              Requests with source == dest are silently dropped.

2. DISPATCH — The active Scheduler assigns each new Passenger to a Car.
              The car's `assigned` list gains the passenger.

3. MERGE (for each car, in car-id order):
   a. If stop_remaining > 0:
        Decrement stop_remaining.
        If stop_remaining == 0 (stop just finished):
          - ALIGHT: passengers on board whose dest == car.floor exit.
                    Record dropoff_tick.
          - BOARD:  assigned passengers whose source == car.floor board,
                    up to remaining capacity, in assignment order.
                    Record pickup_tick. Move from `assigned` → `passengers`.
        → done for this tick.

   b. Else (car is not stopped):
        If car.floor is a target floor (has alighting or boardable passengers):
          - Set stop_remaining = 2.
          → done for this tick (stop begins; no movement).
        Else:
          - MOVE: advance one floor per the movement algorithm (§ below).

4. FINISH   — Write one JSONL entry per car for this tick.
```

A "target floor" is any floor where the car has a reason to stop: a passenger on board whose destination is this floor, or an assigned passenger whose source is this floor.

**Consequence:** arriving at a target floor costs 1 (travel) + 2 (stop) = 3 ticks total. The stop cost applies even when the car is already at the floor (e.g., a passenger assigned to an idle car at the same floor still pays the 2-tick door cost).

---

## Car Movement

Cars follow the **LOOK algorithm**: continue in the current direction while there are target floors ahead. When none remain ahead, reverse. When there are no targets at all, the car is **idle**.

### Idle Redistribution

When a car becomes idle it repositions toward the floor with the highest historical request rate (measured by source-floor frequency over the simulation so far). Constraint: no more than 50% of total cars may be idle at the same floor (assumes a fleet of 5+ cars). If the top-demand floor is at capacity, try the next-highest, and so on. If all candidate floors are at capacity the car stays put.

### Direction on First Assignment

An idle car receiving its first assignment sets its direction toward the assigned passenger's source floor.

---

## Scheduling Strategies

All strategies implement a shared interface via `typing.Protocol` — Python's structural ("duck") typing mechanism. Any class with a matching `assign` method satisfies the interface; no explicit inheritance required.

```python
class Scheduler(Protocol):
    def assign(self, request: Request, building: Building) -> Car: ...
```

Swapping algorithms means passing a different `Scheduler` instance to the engine. No other code changes.

### 1. RoundRobin

Assigns to cars in cyclic order (car 0, car 1, ..., car N-1, car 0, ...). Ignores position, load, and direction.

### 2. NearestCar

Assigns to the car with the smallest floor distance to the passenger's source. Ties broken by lowest car id.

### 3. Adaptive (weighted scorer)

Scores every car; lowest score wins. The score estimates the passenger's **total trip time**, not just pickup time.

```
score(car, request) =
    w_eta   * eta(car, request.source)
  + w_ride  * ride_estimate(car, request.source, request.dest)
  + w_load  * load_factor(car)
```

Weights are normalized so they always sum to 1.0. Each component (`eta`, `ride_estimate`, `load_factor`) is also individually normalized to [0, 1] before weighting so the final score is a true weighted average.

| Term | Normalization | Meaning |
|---|---|---|
| `eta` | Divide by `2 * num_floors` (max possible ETA). | Estimated ticks for the car to reach the passenger's source floor, accounting for direction and intermediate stops. |
| `ride_estimate` | Divide by `num_floors + max_stops * 2`. | `\|dest - source\|` + (estimated intermediate stops between source and dest) * 2. |
| `load_factor` | `len(car.passengers) / car.capacity` (already [0, 1]). | Penalizes full cars. |

Default weights: `w_eta = 0.2`, `w_ride = 0.2`, `w_load = 0.6`. Configurable (must sum to 1.0).

The per-component scores and weights for each assignment are recorded in the passenger log (see Logging § below) to support weight tuning.

---

## Workload Generation

All generators produce a `list[Request]` and accept a `seed: int` for deterministic replay.

Arrivals follow a Poisson process: inter-arrival times are drawn from `Exponential(1/λ)` where λ is the mean arrival rate (passengers per tick). λ is configurable per generator; sensible defaults below.

### Generators

| Generator | Source distribution | Dest distribution | Default λ |
|---|---|---|---|
| **UpPeak** | 80% floor 1, 20% uniform other floors | Uniform floors 2–N | 0.5 |
| **DownPeak** | Uniform floors 2–N | Floor 1 | 0.5 |
| **NormalHour** | Uniform all floors | Uniform all floors (excl. source) | 0.3 |
| **Stress (Spike)** | Same as NormalHour | Same as NormalHour | base=0.3, spike=2.0, spike starts at 30% of duration, lasts 20% of duration |

All distributions are tunable via parameters.

### Serialization

Workloads are written to the output directory as `workload.jsonl`, one request per line:

```json
{"time": 5, "id": "p-042", "source": 1, "dest": 7}
```

---

## Logging

Two JSONL files, written to a configurable output directory.

### `elevator_log.jsonl`

One entry per car per tick:

```json
{"tick": 12, "car_id": "C0", "floor": 5, "direction": "up", "passenger_count": 3}
```

### `passenger_log.jsonl`

One entry per passenger, written at dropoff:

```json
{"id": "p-042", "source": 1, "dest": 7, "request_tick": 5, "pickup_tick": 9, "dropoff_tick": 18, "car_id": "C0"}
```

When the adaptive strategy is active, each entry also includes the scoring breakdown at assignment time:

```json
{"id": "p-042", ..., "scores": {"eta": 0.15, "ride": 0.08, "load": 0.42, "total": 0.65}}
```

No derived fields (`wait_time`, `total_time`). Consumers compute those themselves.

---

## CLI

Single command: `liftos run`. Accepts multiple `--workload` and `--algorithm` flags. Runs all combinations (workload x algorithm) against the same seed and produces a single set of comparison charts.

```
liftos run \
  --floors 20 \
  --elevators 6 \
  --capacity 8 \
  --workload up_peak --workload down_peak --workload normal_hour --workload stress \
  --algorithm round_robin --algorithm nearest_car --algorithm adaptive \
  --passengers 500 \
  --seed 42 \
  --max-ticks 2500 \
  --output ./results
```

**Output structure:**

```
results/
  up_peak/
    round_robin/
      elevator_log.jsonl
      passenger_log.jsonl
      workload.jsonl
    nearest_car/
      ...
    adaptive/
      ...
  down_peak/
    ...
  wait_time.png
  total_time.png
```

Each workload is generated once (same seed) and replayed against every algorithm. Per-combination logs are written to `{workload}/{algorithm}/` subdirectories. Charts and a summary are written to the output root.

When a single workload and algorithm are specified, the run produces logs and prints summary stats to stdout (no charts).

### Charts (matplotlib)

Saved as PNGs to the output directory:

- `wait_time.png` — grouped bar chart. X-axis: workloads. Bars: algorithms (color-coded). Each bar shows mean and P95; min/max as error whiskers.
- `total_time.png` — same layout for total time.

---

## Project Layout

```
src/
  liftos/
    __init__.py
    models.py              # Request, Passenger, Car, Direction, Building
    scheduler.py           # Scheduler protocol
    movement.py            # LOOK algorithm + idle redistribution
    logger.py              # JSONL log writers
    engine.py              # Tick loop (insert → dispatch → merge → finish)
    strategies/
      __init__.py          # Strategy registry + re-exports
      round_robin.py
      nearest_car.py
      adaptive.py
    simulator/
      __init__.py
      workloads.py         # UpPeak, DownPeak, NormalHour, Stress generators
      charts.py            # matplotlib chart generation
    cli.py                 # Click/argparse CLI
tests/
  test_models.py
  test_movement.py
  test_strategies.py
  test_engine.py
  test_workloads.py
pyproject.toml
```

Dependencies: Python 3.12+, `matplotlib`, `click` (CLI). Managed with `uv`.

---

## Validation

After the tick loop completes (or `max_ticks` is reached), the engine runs a completeness check:

1. Every passenger in the manifest must have a non-null `dropoff_tick`.
2. Any unserved passengers are reported with their details (`id`, `source`, `dest`, `request_tick`, `car_id`, last known car position).
3. The simulation exit code is non-zero if any passengers remain unserved.

This enforces the top-priority scheduling goal (completeness) and catches bugs in movement or assignment logic early.

---

## Benchmark Configuration

Reference scenario for V1 validation: **500 passengers, 20 floors, 6 elevators, capacity 8**.

| Workload | Default λ | Est. last arrival | Est. last dropoff | Max ticks |
|---|---|---|---|---|
| UpPeak | 0.5 | ~1000 | ~1100 | 1500 |
| DownPeak | 0.5 | ~1000 | ~1100 | 1500 |
| NormalHour | 0.3 | ~1667 | ~1800 | 2500 |
| Stress | 0.3 base / 2.0 spike | ~1200 | ~1350 | 2000 |

Estimates assume average inter-arrival of `1/λ` ticks and worst-case final-passenger travel of ~50 ticks (19 floors + stops). Max ticks adds ~30% headroom as a safety bound. The `--max-ticks` CLI flag defaults to 2500 but should be set per-workload for tighter runs.

---

## Risks & Ambiguities

These areas are most likely to need iteration or clarification during implementation.

### 1. Idle Redistribution Heuristic

"Floor of most demand" is defined as highest historical source-floor frequency, but this metric is cumulative and slow to adapt. In UpPeak the signal is obvious (floor 1), but in NormalHour it may be noisy and the redistribution effectively random. **We should verify that the heuristic actually improves P95 over naive stay-in-place by comparing with and without it in the benchmark runs.**

### 2. Adaptive Scorer Weight Tuning

The default weights (`w_eta=0.2, w_ride=0.2, w_load=0.6`) are initial guesses. The `ride_estimate` term depends on predicting intermediate stops, which is itself an approximation. Poor weights could make the adaptive strategy perform worse than NearestCar. The per-assignment score breakdown in the passenger log exists specifically to support post-hoc weight analysis. **Plan to iterate on weights using the comparison charts and score logs before calling V1 done.**

### 3. Capacity Starvation Under Full Assignment Lock

Assignment is permanent and passengers wait for their assigned car even if it's full. Under Stress workloads with high arrival rates, a car could accumulate many assignments and be perpetually full, starving its later-assigned passengers indefinitely. This would show up as extreme P95 tail latency. **The adaptive scorer's load penalty mitigates this, but we should verify with Stress workloads and consider a V2 re-assignment escape valve if P95 blows up.**

### 4. ETA Estimation Accuracy

The adaptive scorer's `eta` function estimates ticks until a car reaches a floor, accounting for pending stops. Each pending stop adds 2 ticks, but stops may be added or removed as the simulation progresses — the estimate is a snapshot that can go stale immediately. This is inherent to any greedy heuristic and acceptable for V1.
