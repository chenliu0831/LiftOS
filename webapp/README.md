# LiftOS Simulation WebApp

A lightweight replay viewer for LiftOS elevator benchmark runs. Animates elevator movement, shows real-time charts, and lets you compare scheduling algorithms side by side.

## Setup

```bash
cd webapp
npm install
npm run dev
```

Opens at [http://localhost:5173](http://localhost:5173). The dev server automatically serves benchmark data from `../logs/`.

## Usage

1. **Select a run** from the top-bar dropdowns — pick a benchmark run, workload, and algorithm.
2. **Press Play** (or hit Space) to watch the simulation replay.
3. **Scrub** the timeline slider to jump to any tick.
4. **Switch algorithms** mid-replay to compare behavior on the same workload.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Right Arrow | Step forward one tick |
| Left Arrow | Step backward one tick |

### Speed Control

The speed slider goes from 1x to 100x ticks per second. At 100x, a typical 1000-tick run replays in about 10 seconds.

## What You See

### Building View (left panel)

An SVG visualization of the elevator building:

- **Elevator cars** move between floors with smooth transitions
- **Color coding** — empty cars are dark, loaded cars are blue, near-capacity cars are red
- **Direction arrows** — green triangle (up), orange triangle (down), no arrow (idle)
- **Waiting passengers** — red dots with count on each floor where passengers are waiting

### Stats Bar

Live metrics that update with every tick:

- Passengers served / waiting / in-transit
- Wait time mean and p95
- Total trip time mean and p95
- Per-car occupancy (e.g., C0: 3/8)

### Charts (right panel)

Four real-time line charts that grow as the replay advances:

| Chart | Lines | What it shows |
|-------|-------|---------------|
| Wait Time | mean (blue), p95 (orange) | Running wait time stats of completed passengers |
| Total Time | mean (green), p95 (red) | Running total trip time stats |
| Car Occupancy | one line per car | Passenger count in each elevator over time |
| Throughput | pickups (green), dropoffs (blue) | Activity rate in a sliding 20-tick window |

## Architecture

14 source files, 4 runtime dependencies (React, Zustand, Recharts, Vite).

```
src/
  types.ts                  All TypeScript interfaces
  data/
    loader.ts               Fetch and parse JSONL log files via /api/runs
    indexer.ts              Pre-compute tick-indexed snapshots for O(1) playback
  stores/
    data-store.ts           Run/workload/algorithm selection and data loading
    playback-store.ts       Tick state machine (idle/playing/paused/finished)
  components/
    BuildingView.tsx        SVG elevator animation
    ChartsPanel.tsx         4 Recharts line charts
    StatsBar.tsx            Numeric stats bar
    PlaybackControls.tsx    Transport controls + requestAnimationFrame loop
```

### Data Pipeline

1. **Vite plugin** (`vite.config.ts`) serves the `../logs/` directory at `/api/runs` endpoints
2. **Loader** fetches `manifest.json` + 3 JSONL files (elevator, passenger, dispatch logs) in parallel
3. **Indexer** pre-computes a `TickSnapshot` for every tick (car positions, waiting passengers, running stats) in a single forward pass (~10ms for 16K entries)
4. **Playback** reads pre-computed snapshots by index — O(1) per tick, no recomputation during animation

### Data Format

The webapp reads standard LiftOS benchmark output:

```
logs/run_YYYYMMDD_HHMMSS/
  manifest.json                       Run configuration
  {workload}/{algorithm}/
    elevator_log.jsonl                Car state per tick
    passenger_log.jsonl               Passenger lifecycle
    dispatch_log.jsonl                Scheduler assignment decisions
```

Generate benchmark data with:

```bash
uv run liftos --floors 20 --elevators 6 --capacity 8 --passengers 500 \
  --workload up_peak --workload stress \
  --algorithm round_robin --algorithm adaptive \
  --seed 42 --output logs
```
