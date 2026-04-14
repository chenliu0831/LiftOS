# LiftOS — Implementation Plan

Tasks are ordered so each builds on the last. Each task states what it produces and how to verify it. Tests focus on functional/behavioral correctness — no excessive unit tests for trivial getters or data containers. Each task is a reviewable increment; wait for approval before proceeding.

---

## Phase 1: Scaffold & Domain Model

### 1.1 Project setup

- `pyproject.toml` with `uv`, Python 3.12+, `matplotlib`, `click` deps.
- `src/liftos/` package skeleton (empty `__init__.py` files for all subpackages).
- `tests/` directory.
- Verify: `uv sync` succeeds, `uv run python -c "import liftos"` works.

### 1.2 Domain model (`models.py`)

- `Direction` literal type.
- `Request` dataclass: `id`, `source`, `dest`, `time`.
- `Passenger` dataclass: `request`, `pickup_tick`, `dropoff_tick`, `car_id`, plus optional `scores` dict.
- `Car` dataclass: `id`, `floor`, `direction`, `passengers`, `assigned`, `capacity`, `stop_remaining`. Methods: `is_idle`, `target_floors`, `remaining_capacity`.
- `Building` dataclass: `num_floors`, `cars`. Method to query global state (all positions, idle cars, etc.).
- `test_models.py`: construction, `target_floors` correctness, capacity math.

### 1.3 Scheduler protocol (`scheduler.py`)

- `Scheduler` typing protocol with single method: `assign(request, building) -> Car`.
- No tests needed — it's a type signature.

---

## Phase 2: Core Engine (minimal vertical slice)

Goal: a running simulation with RoundRobin on a trivial workload. This validates the tick loop end-to-end before adding complexity.

### 2.1 RoundRobin strategy (`strategies/round_robin.py`)

- Cyclic assignment by car index.
- `test_strategies.py`: assigns in cycle, wraps around correctly.

### 2.2 LOOK movement (`movement.py`)

- `next_move(car, building) -> Action` where Action is move-up, move-down, or idle.
- Continue in current direction while targets exist ahead; reverse when none; idle when no targets at all.
- Direction-on-first-assignment: idle car sets direction toward its first assigned passenger.
- **No idle redistribution yet** — idle cars stay put.
- `test_movement.py`: direction continuation, reversal, idle detection, first-assignment direction.

### 2.3 JSONL logger (`logger.py`)

- `ElevatorLogger`: writes one `{"tick", "car_id", "floor", "direction", "passenger_count"}` line per car per tick.
- `PassengerLogger`: writes one `{"id", "source", "dest", "request_tick", "pickup_tick", "dropoff_tick", "car_id"}` line per completed passenger. Includes optional `"scores"` key when present.
- Both write to file paths given at construction.
- `test_logger.py`: round-trip write → read, verify JSONL structure.

### 2.4 Engine tick loop (`engine.py`)

The core of the system. Implements the four phases per tick:

1. **INSERT** — convert due requests to passengers, drop `source == dest`.
2. **DISPATCH** — call `scheduler.assign()` for each new passenger.
3. **MERGE** — for each car: handle stop countdown, alight/board, detect new stops, or move.
4. **FINISH** — write elevator log entries.

Also: write passenger log entry at dropoff. Track simulation tick counter.

- `test_engine.py`: hand-crafted scenario — 2 cars, 5 floors, 3–4 requests with known expected pickup/dropoff ticks. Assert exact tick values.

### 2.5 Completeness validation

- After tick loop ends (all requests inserted and all passengers dropped off, or `max_ticks` reached): check every passenger has `dropoff_tick`.
- Report unserved passengers with details. Return non-zero exit status on failure.
- Add to engine test: scenario that deliberately exceeds `max_ticks` with 1 car, many passengers → verify failure report.

---

## Phase 3: Remaining Strategies

Can be built in parallel. Each is independent of the others.

### 3.1 NearestCar (`strategies/nearest_car.py`)

- Assign to car with smallest `|car.floor - request.source|`. Ties broken by lowest car id.
- `test_strategies.py` (extend): equidistant tie-breaking, correct selection.

### 3.2 Adaptive scorer (`strategies/adaptive.py`)

- Score function: `w_eta * norm_eta + w_ride * norm_ride + w_load * norm_load`.
- Normalization: `eta / (2 * num_floors)`, `ride / (num_floors + max_stops * 2)`, `load / capacity`.
- Weights default to `(0.2, 0.2, 0.6)`, configurable, must sum to 1.0.
- `eta()`: estimate ticks to reach source, counting direction and intermediate stops.
- `ride_estimate()`: `|dest - source|` + estimated intermediate stops * 2.
- Attach `scores` dict (`eta`, `ride`, `load`, `total`) to the passenger on assignment.
- `test_strategies.py` (extend): verify score components, normalization bounds [0,1], weight constraint, correct car selection on a known layout.

### 3.3 Strategy registry (`strategies/__init__.py`)

- Dict mapping name → class: `{"round_robin": RoundRobin, "nearest_car": NearestCar, "adaptive": Adaptive}`.
- Lookup function used by CLI.

---

## Phase 4: Idle Redistribution

### 4.1 Demand tracker

- Maintain a per-floor request count (incremented at INSERT).
- Expose `demand_ranking() -> list[int]` returning floors sorted by descending request frequency.

### 4.2 Redistribution logic (extend `movement.py`)

- When a car is idle: pick the highest-demand floor where < 50% of total cars are already idle. Move toward it.
- If no eligible floor, stay put.
- `test_movement.py` (extend): verify redistribution target selection, 50% cap enforcement, fallback to stay-put.

---

## Phase 5: Simulator

### 5.1 Workload generators (`simulator/workloads.py`)

All accept `num_passengers`, `num_floors`, `seed`. Return `list[Request]`.

- **UpPeak**: 80% source=1, 20% uniform other floors. Dest uniform 2–N. λ=0.5.
- **DownPeak**: source uniform 2–N. Dest=1. λ=0.5.
- **NormalHour**: source/dest uniform (excl. source=dest). λ=0.3.
- **Stress**: NormalHour distributions. λ=0.3 base, 2.0 spike (starts 30% in, lasts 20% of duration).
- Serialization: write `workload.jsonl`.
- `test_workloads.py`: verify request count, floor bounds, deterministic output with same seed, Stress spike timing.

### 5.2 Charts (`simulator/charts.py`)

- Input: dict of `{(workload, algorithm): list[PassengerRecord]}`.
- `wait_time.png`: grouped bar chart — workloads on x-axis, algorithms color-coded. Bars show mean + P95. Error whiskers for min/max.
- `total_time.png`: same layout.
- Verify: generate charts from synthetic data, visually inspect.

### 5.3 CLI (`cli.py`)

- `liftos run` with flags: `--floors`, `--elevators`, `--capacity`, `--workload` (repeatable), `--algorithm` (repeatable), `--passengers`, `--seed`, `--max-ticks`, `--output`.
- Single workload + algorithm: run simulation, write logs, print summary stats.
- Multiple: run all combinations (workload generated once per seed, replayed per algorithm). Write logs to `{workload}/{algorithm}/` subdirs. Generate charts at output root.
- Verify: run CLI end-to-end with `--help`, single mode, multi mode.

---

## Phase 6: Benchmark & Tuning

### 6.1 Benchmark run

- Run reference configuration: 500 passengers, 20 floors, 6 elevators, capacity 8, all 4 workloads, all 3 algorithms.
- Verify: all passengers served (completeness check passes), charts generated, no crashes.

### 6.2 Adaptive weight tuning

- Analyze score logs from benchmark. Check whether adaptive beats NearestCar on mean and P95 total time.
- If not, adjust weights and re-run. Iterate until adaptive is competitive.
- This is an exploratory task — outcome is updated default weights.

---

## Dependency Graph

```
1.1 ──→ 1.2 ──→ 1.3 ──→ 2.1 ──→ 2.4 ──→ 2.5
                    │        ↗        ↑
                    ├──→ 2.2 ─────────┤
                    │                  │
                    └──→ 2.3 ─────────┘

2.4 ──→ 3.1 ─┐
         3.2 ─┼──→ 3.3
         3.3 ─┘

2.4 ──→ 4.1 ──→ 4.2

2.5 ──→ 5.1 ──→ 5.3
         5.2 ──→ 5.3
3.3 ──→ 5.3

5.3 ──→ 6.1 ──→ 6.2
```

Phases 3 and 4 can run in parallel once Phase 2 is complete. Phase 5 depends on both.
