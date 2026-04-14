"""Diagnostic plots for workload generators."""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from liftos.simulator.workloads import up_peak, down_peak, normal_hour, stress

NUM_PASSENGERS = 500
NUM_FLOORS = 20
SEED = 42
OUTPUT = Path("logs/workload_diagnostics")


def plot_workload(name: str, requests: list, ax_row: list) -> None:
    times = [r.time for r in requests]
    sources = [r.source for r in requests]
    dests = [r.dest for r in requests]

    # Arrival rate over time (rolling window count)
    counts, bin_edges = np.histogram(times, bins=50)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    ax_row[0].plot(bin_centers, counts, linewidth=1.5)
    ax_row[0].fill_between(bin_centers, counts, alpha=0.2)
    ax_row[0].set_title(f"{name}: Arrival Rate Over Time")
    ax_row[0].set_xlabel("Tick")
    ax_row[0].set_ylabel("Passengers")

    # Source floor distribution
    floors = range(1, NUM_FLOORS + 1)
    src_counts = [sources.count(f) for f in floors]
    ax_row[1].plot(list(floors), src_counts, marker="o", markersize=4, linewidth=1.5)
    ax_row[1].fill_between(list(floors), src_counts, alpha=0.2)
    ax_row[1].set_title(f"{name}: Source Floors")
    ax_row[1].set_xlabel("Floor")
    ax_row[1].set_ylabel("Count")
    ax_row[1].set_xticks(range(1, NUM_FLOORS + 1, 2))

    # Destination floor distribution
    dst_counts = [dests.count(f) for f in floors]
    ax_row[2].plot(list(floors), dst_counts, marker="o", markersize=4, linewidth=1.5)
    ax_row[2].fill_between(list(floors), dst_counts, alpha=0.2)
    ax_row[2].set_title(f"{name}: Dest Floors")
    ax_row[2].set_xlabel("Floor")
    ax_row[2].set_ylabel("Count")
    ax_row[2].set_xticks(range(1, NUM_FLOORS + 1, 2))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    workloads = {
        "UpPeak": up_peak(NUM_PASSENGERS, NUM_FLOORS, SEED),
        "DownPeak": down_peak(NUM_PASSENGERS, NUM_FLOORS, SEED),
        "NormalHour": normal_hour(NUM_PASSENGERS, NUM_FLOORS, SEED),
        "Stress": stress(NUM_PASSENGERS, NUM_FLOORS, SEED),
    }

    fig, axes = plt.subplots(4, 3, figsize=(18, 20))

    for i, (name, reqs) in enumerate(workloads.items()):
        plot_workload(name, reqs, axes[i])

    fig.tight_layout(pad=3.0)
    out_path = OUTPUT / "workload_diagnostics.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved to {out_path}")

    # Print summary stats
    for name, reqs in workloads.items():
        times = [r.time for r in reqs]
        sources = [r.source for r in reqs]
        ground_pct = sum(1 for s in sources if s == 1) / len(sources) * 100
        dest_1_pct = sum(1 for r in reqs if r.dest == 1) / len(reqs) * 100
        print(f"\n{name}:")
        print(f"  Tick range: {min(times)}–{max(times)}")
        print(f"  Source floor 1: {ground_pct:.1f}%")
        print(f"  Dest floor 1:   {dest_1_pct:.1f}%")


if __name__ == "__main__":
    main()
