from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from liftos.models import Passenger


def _compute_stats(passengers: list[Passenger]) -> dict[str, dict[str, float]]:
    """Compute wait_time and total_time stats from completed passengers."""
    wait_times = []
    total_times = []
    for p in passengers:
        if p.pickup_tick is not None and p.dropoff_tick is not None:
            wait = p.pickup_tick - p.request.time
            total = p.dropoff_tick - p.request.time
            wait_times.append(wait)
            total_times.append(total)

    def stats(values: list[float]) -> dict[str, float]:
        if not values:
            return {"min": 0, "max": 0, "mean": 0, "p95": 0}
        arr = sorted(values)
        return {
            "min": arr[0],
            "max": arr[-1],
            "mean": sum(arr) / len(arr),
            "p95": arr[int(len(arr) * 0.95)],
        }

    return {"wait_time": stats(wait_times), "total_time": stats(total_times)}


def generate_charts(
    results: dict[tuple[str, str], list[Passenger]],
    output_dir: Path,
) -> None:
    """Generate a combined comparison chart with wait_time and total_time side by side.

    Args:
        results: mapping of (workload_name, algorithm_name) -> passenger list
        output_dir: directory to write PNG file into
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    workloads = sorted({wl for wl, _ in results})
    algorithms = sorted({alg for _, alg in results})

    all_stats: dict[tuple[str, str], dict] = {}
    for key, passengers in results.items():
        all_stats[key] = _compute_stats(passengers)

    fig, axes = plt.subplots(
        2, 2,
        figsize=(max(16, len(workloads) * 6), 13),
        gridspec_kw={"height_ratios": [3, 1]},
    )

    for col, metric in enumerate(("wait_time", "total_time")):
        _plot_metric(axes[0][col], metric, workloads, algorithms, all_stats)
        _stats_table(axes[1][col], metric, workloads, algorithms, all_stats)

    fig.tight_layout(pad=3.0)
    fig.savefig(output_dir / "results.png", dpi=150)
    plt.close(fig)


def _y_cap(all_maxs: list[float]) -> float | None:
    """Return a y-axis cap if an outlier would compress the chart, else None."""
    if len(all_maxs) < 2:
        return None
    top, second = sorted(all_maxs)[-1], sorted(all_maxs)[-2]
    if second > 0 and top > second * 2.5:
        return second * 1.5
    return None


def _plot_metric(
    ax: plt.Axes,
    metric: str,
    workloads: list[str],
    algorithms: list[str],
    all_stats: dict[tuple[str, str], dict],
) -> None:
    x = np.arange(len(workloads))
    num_algs = len(algorithms)
    width = 0.8 / num_algs

    # Pre-scan for outliers to determine y-axis cap
    all_maxs = [
        all_stats.get((wl, alg), {}).get(metric, {}).get("max", 0)
        for alg in algorithms
        for wl in workloads
    ]
    cap = _y_cap(all_maxs)

    for i, alg in enumerate(algorithms):
        means = []
        p95s = []
        mins = []
        maxs = []
        for wl in workloads:
            s = all_stats.get((wl, alg), {}).get(metric, {})
            means.append(s.get("mean", 0))
            p95s.append(s.get("p95", 0))
            mins.append(s.get("min", 0))
            maxs.append(s.get("max", 0))

        offset = (i - num_algs / 2 + 0.5) * width
        pos = x + offset

        # Mean bars
        ax.bar(pos, means, width * 0.9, label=alg)

        # P95 markers (clamp to visible area if capped)
        vis_p95 = [min(p, cap) if cap else p for p in p95s]
        ax.scatter(pos, vis_p95, marker="D", s=40, zorder=5, color=f"C{i}")

        # Min/max whiskers (clamp top to cap)
        for j in range(len(workloads)):
            vis_max = min(maxs[j], cap) if cap else maxs[j]
            ax.plot([pos[j], pos[j]], [mins[j], vis_max], color=f"C{i}", linewidth=1.5)

    if cap:
        ax.set_ylim(0, cap * 1.08)

    title = metric.replace("_", " ").title()
    ax.set_ylabel(f"{title} (ticks)")
    ax.set_title(f"{title} by Algorithm and Workload")
    ax.set_xticks(x)
    ax.set_xticklabels(workloads)
    ax.legend(title="Algorithm (bars=mean, \u25c6=P95)")
    ax.grid(axis="y", alpha=0.3)


def _stats_table(
    ax: plt.Axes,
    metric: str,
    workloads: list[str],
    algorithms: list[str],
    all_stats: dict[tuple[str, str], dict],
) -> None:
    """Render a table with separate mean and p95 columns, winners highlighted."""
    cell_text = []
    row_colors = []
    means_grid: list[list[float]] = []
    p95s_grid: list[list[float]] = []
    for i, alg in enumerate(algorithms):
        row = []
        means_row = []
        p95s_row = []
        for wl in workloads:
            s = all_stats.get((wl, alg), {}).get(metric, {})
            mean = s.get("mean", 0)
            p95 = s.get("p95", 0)
            row.extend([f"{mean:.0f}", f"{p95:.0f}"])
            means_row.append(mean)
            p95s_row.append(p95)
        cell_text.append(row)
        means_grid.append(means_row)
        p95s_grid.append(p95s_row)
        row_colors.append(f"C{i}")

    # Column headers: paired mean/p95 under each workload
    col_labels = []
    for wl in workloads:
        col_labels.extend([f"{wl}\nmean", f"{wl}\np95"])

    ax.axis("off")
    table = ax.table(
        cellText=cell_text,
        rowLabels=algorithms,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)

    # Color row labels to match chart legend
    for i, color in enumerate(row_colors):
        table[i + 1, -1].set_text_props(color=color, fontweight="bold")

    # Highlight best (lowest) per column — mean and p95 independently
    for wl_idx in range(len(workloads)):
        mean_col = wl_idx * 2
        p95_col = wl_idx * 2 + 1

        col_means = [means_grid[r][wl_idx] for r in range(len(algorithms))]
        best_mean = col_means.index(min(col_means))
        table[best_mean + 1, mean_col].set_facecolor("#d4edda")
        table[best_mean + 1, mean_col].set_text_props(fontweight="bold")

        col_p95s = [p95s_grid[r][wl_idx] for r in range(len(algorithms))]
        best_p95 = col_p95s.index(min(col_p95s))
        table[best_p95 + 1, p95_col].set_facecolor("#d4edda")
        table[best_p95 + 1, p95_col].set_text_props(fontweight="bold")

    title = metric.replace("_", " ").title()
    ax.set_title(f"{title} (ticks)", fontsize=10, pad=8)
