from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

from liftos.engine import Engine, EngineRunResult, Loggers
from liftos.logger import DispatchLogger, ElevatorLogger, PassengerLogger
from liftos.models import Building, Car
from liftos.movement import Look
from liftos.simulator.charts import generate_charts
from liftos.simulator.workloads import WORKLOADS
from liftos.strategies import STRATEGIES


def _get_commit_id() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def _make_run_dir(base: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = base / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_manifest(
    run_dir: Path,
    floors: int,
    elevators: int,
    capacity: int,
    workloads: tuple[str, ...],
    algorithms: tuple[str, ...],
    passengers: int,
    seed: int,
    max_ticks: int,
) -> None:
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": _get_commit_id(),
        "config": {
            "floors": floors,
            "elevators": elevators,
            "capacity": capacity,
            "workloads": list(workloads),
            "algorithms": list(algorithms),
            "passengers": passengers,
            "seed": seed,
            "max_ticks": max_ticks,
        },
    }
    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


@click.command()
@click.option("--floors", type=int, required=True, help="Number of floors.")
@click.option("--elevators", type=int, required=True, help="Number of elevator cars.")
@click.option("--capacity", type=int, default=8, help="Max passengers per car.")
@click.option(
    "--workload",
    "workloads",
    type=click.Choice(list(WORKLOADS)),
    multiple=True,
    required=True,
    help="Workload type (repeatable).",
)
@click.option(
    "--algorithm",
    "algorithms",
    type=click.Choice(list(STRATEGIES)),
    multiple=True,
    required=True,
    help="Scheduling algorithm (repeatable).",
)
@click.option("--passengers", type=int, required=True, help="Number of passengers.")
@click.option(
    "--seed", type=int, default=42, help="Random seed for workload generation."
)
@click.option(
    "--max-ticks", type=int, default=2500, help="Safety bound on simulation ticks."
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("./logs"),
    help="Base output directory.",
)
def main(
    floors: int,
    elevators: int,
    capacity: int,
    workloads: tuple[str, ...],
    algorithms: tuple[str, ...],
    passengers: int,
    seed: int,
    max_ticks: int,
    output: Path,
) -> None:
    """LiftOS — smart elevator simulation."""
    run_dir = _make_run_dir(output)
    click.echo(f"Output: {run_dir}")

    _write_manifest(
        run_dir,
        floors,
        elevators,
        capacity,
        workloads,
        algorithms,
        passengers,
        seed,
        max_ticks,
    )

    multi_mode = len(workloads) > 1 or len(algorithms) > 1
    all_results: dict[tuple[str, str], list] = {}

    for wl_name in workloads:
        requests = WORKLOADS[wl_name](passengers, floors, seed)

        for alg_name in algorithms:
            click.echo(f"Running {wl_name} x {alg_name}...", nl=False)

            building = Building(
                num_floors=floors,
                cars=[
                    Car(id=f"C{i}", floor=1, capacity=capacity)
                    for i in range(elevators)
                ],
            )
            scheduler = STRATEGIES[alg_name]()

            combo_dir = run_dir / wl_name / alg_name
            combo_dir.mkdir(parents=True, exist_ok=True)

            loggers = Loggers(
                elevator=ElevatorLogger(combo_dir / "elevator_log.jsonl"),
                passenger=PassengerLogger(combo_dir / "passenger_log.jsonl"),
                dispatch=DispatchLogger(combo_dir / "dispatch_log.jsonl"),
            )

            result = Engine(building, scheduler, Look(), loggers).run(
                requests, max_ticks
            )
            all_results[(wl_name, alg_name)] = result.passengers

            _print_summary(result)

    if multi_mode:
        click.echo(f"\nGenerating charts in {run_dir}/")
        generate_charts(all_results, run_dir)

    click.echo("Done.")


def _print_summary(result: EngineRunResult) -> None:
    served = [p for p in result.passengers if p.dropoff_tick is not None]
    unserved = result.unserved

    if not served:
        click.echo(f" no passengers served in {result.ticks} ticks.")
        return

    wait_times = [p.pickup_tick - p.request.time for p in served]
    total_times = [p.dropoff_tick - p.request.time for p in served]

    def p95(vals: list[int]) -> float:
        s = sorted(vals)
        return s[int(len(s) * 0.95)]

    click.echo(
        f" {len(served)} served, {len(unserved)} unserved, {result.ticks} ticks | "
        f"wait mean={sum(wait_times) / len(wait_times):.1f} p95={p95(wait_times)} | "
        f"total mean={sum(total_times) / len(total_times):.1f} p95={p95(total_times)}"
    )

    if unserved:
        click.echo(f"  WARNING: {len(unserved)} passengers unserved!")
        for p in unserved[:5]:
            click.echo(
                f"    {p.request.id}: source={p.request.source} dest={p.request.dest} car={p.car_id}"
            )
