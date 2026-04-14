# LiftOS: An OS for Modern Smart Elevators with Discrete-Event Simulation

This document defines the functional requirements, constraints, and design guidelines for LiftOS, a smart elevator routing system and its companion discrete-event simulation engine.

The system has two components:

1. **LiftOS Core** — assigns passengers to elevators and schedules car movement.
2. **Lift Simulator** — generates traffic workloads and runs them through LiftOS Core.

---

## Time Model

Time is discrete. Every component in the system advances one tick at a time.

| Constraint | Definition |
|---|---|
| **Unit of time** | One tick = one floor of travel (up or down). |
| **Stop cost** | Each floor stop costs 2 ticks for passenger boarding and alighting, regardless of how many passengers board or exit. |
| **No lookahead** | No component may peek at future events. Decisions are made using only current and past state. |
| **Tick-by-tick execution** | The simulation advances exactly one tick per step. |

---

## LiftOS Core (V1)

LiftOS Core takes passenger requests and makes routing decisions for all elevator cars.

### Functional Requirements

1. A passenger submits both origin and destination floor at the time of request.
2. The system immediately assigns the passenger to a specific elevator.
3. Once assigned, the passenger's destination is fixed.
4. The following physical parameters are configurable:
   - Number of elevators
   - Number of floors
   - Maximum passengers per elevator (capacity)

### Scheduling Goals

Listed in priority order:

1. **Completeness** — serve all requests eventually.
2. **Minimize mean total time** per passenger, where `total_time = wait_time + travel_time`.
3. **Minimize P95 total time** — reduce tail latency, not just the average.
4. **Avoid wasteful assignments**, specifically:
   - Assigning a distant car when a closer car is already near the passenger's floor.
   - Assigning a car that already has many pending stops.

### Scheduling Strategy Design

- Implement **two simple baseline strategies** (e.g., nearest-car, round-robin).
- Implement **one adaptive strategy** that uses global state: all cars' positions, directions, load, and pending stops.
- The system must support swapping scheduling algorithms without code changes beyond the algorithm itself.

### Input Data Format

Each passenger request is a record with four fields:

| Field | Type | Description |
|---|---|---|
| `time` | int | Tick when the request is made |
| `id` | string | Unique passenger identifier |
| `source` | int | Origin floor |
| `dest` | int | Destination floor |

### Observability

LiftOS streams two log files to a configurable output directory:

- **Elevator Log** — records every car's position and direction at every tick.
- **Passenger Log** — records each passenger's `wait_time` and `total_time`.

These logs are consumed by the Lift Simulator for statistics (min, max, mean, P95) and by a future visualizer for replay.

---

## Lift Simulator

The Lift Simulator generates traffic workloads, feeds them to LiftOS Core, and produces performance reports.

### Functional Requirements

1. **Workload generation** — produce a list of passenger requests and serialize them to a local folder. File format: one request per line, comma-separated: `time,id,source,dest`.
2. **Performance visualization** — generate charts showing min, max, mean, and P95 for both **wait time** and **total time**. Charts must make it easy to compare algorithms side-by-side. Use matplotlib.
3. **CLI** — provide a command-line interface to run simulations with configurable floor count and passenger count.

### Supported Workloads

All workloads use a Poisson arrival process across floors. The base arrival patterns are:

| Workload | Description |
|---|---|
| **UpPeak** | Models a morning rush (8:30–9:30 AM). Most passengers originate at the ground floor. |
| **DownPeak** | Models an evening rush (5:30–6:30 PM). Passengers from all floors travel to the ground floor. |
| **NormalHour** | Models a typical mid-day period (e.g., Wednesday afternoon). Passengers travel between arbitrary floors. |
| **Stress** | Models unexpected traffic spikes. Uses one of the two arrival patterns below. |

Inspired by [Brooker's simulation](https://github.com/mbrooker/simulator_example/blob/bbfe3946f0459a69f6012737c68fc63b973471be/simple_collapse_sim/sim.py#L8), the Stress workloads could use **SpikeLoadGenerator** — Poisson arrivals at a constant base rate, with a sudden spike to a higher rate for a fixed duration, then an immediate drop back to base.

---

## Implementation Guidelines

1. Use idiomatic modern Python 3 with type annotations throughout.
2. Manage dependencies with `uv` and `pyproject.toml`.
3. Minimize third-party dependencies.
4. Maintain strong separation of concerns. Favor composition over inheritance.

---

## Future Work (V2)

The V1 design should leave room for these extensions, but they are out of scope for now:

- **LiftOS Visualizer** — a browser-based tool that animates a simulation replay.
- **Special elevator modes** — express elevators serving a "sky lobby", or cars that dynamically switch between local and express operating modes.
