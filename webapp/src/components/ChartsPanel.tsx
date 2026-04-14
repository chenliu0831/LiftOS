import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useDataStore } from "../stores/data-store";
import { usePlaybackStore } from "../stores/playback-store";

const COLORS = [
  "#4a90d9",
  "#e74c3c",
  "#27ae60",
  "#f39c12",
  "#8e44ad",
  "#e07b39",
];
const MAX_POINTS = 300;

function sample<T>(arr: T[], maxPoints: number): T[] {
  if (arr.length <= maxPoints) return arr;
  const step = Math.ceil(arr.length / maxPoints);
  const result: T[] = [];
  for (let i = 0; i < arr.length; i += step) result.push(arr[i]!);
  // Always include last point
  if (result[result.length - 1] !== arr[arr.length - 1])
    result.push(arr[arr.length - 1]!);
  return result;
}

export function ChartsPanel() {
  const scenario = useDataStore((s) => s.scenario);
  const currentTick = usePlaybackStore((s) => s.currentTick);

  if (!scenario) return null;

  return (
    <>
      <WaitTimeChart scenario={scenario} currentTick={currentTick} />
      <TotalTimeChart scenario={scenario} currentTick={currentTick} />
      <OccupancyChart scenario={scenario} currentTick={currentTick} />
      <ThroughputChart scenario={scenario} currentTick={currentTick} />
    </>
  );
}

interface ChartProps {
  scenario: NonNullable<ReturnType<typeof useDataStore.getState>["scenario"]>;
  currentTick: number;
}

function WaitTimeChart({ scenario, currentTick }: ChartProps) {
  const data = useMemo(() => {
    const raw: { tick: number; mean: number; p95: number }[] = [];
    for (let i = 0; i <= currentTick && i < scenario.tickSnapshots.length; i++) {
      const s = scenario.tickSnapshots[i]!.stats;
      if (s.served > 0) raw.push({ tick: i, mean: +s.waitMean.toFixed(1), p95: s.waitP95 });
    }
    return sample(raw, MAX_POINTS);
  }, [scenario, currentTick]);

  return (
    <div className="chart-container">
      <div className="chart-title">Wait Time</div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="mean"
              stroke="#4a90d9"
              dot={false}
              strokeWidth={1.5}
              name="Mean"
            />
            <Line
              type="monotone"
              dataKey="p95"
              stroke="#f39c12"
              dot={false}
              strokeWidth={1.5}
              name="P95"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TotalTimeChart({ scenario, currentTick }: ChartProps) {
  const data = useMemo(() => {
    const raw: { tick: number; mean: number; p95: number }[] = [];
    for (let i = 0; i <= currentTick && i < scenario.tickSnapshots.length; i++) {
      const s = scenario.tickSnapshots[i]!.stats;
      if (s.served > 0) raw.push({ tick: i, mean: +s.totalMean.toFixed(1), p95: s.totalP95 });
    }
    return sample(raw, MAX_POINTS);
  }, [scenario, currentTick]);

  return (
    <div className="chart-container">
      <div className="chart-title">Total Time</div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="mean"
              stroke="#27ae60"
              dot={false}
              strokeWidth={1.5}
              name="Mean"
            />
            <Line
              type="monotone"
              dataKey="p95"
              stroke="#e74c3c"
              dot={false}
              strokeWidth={1.5}
              name="P95"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function OccupancyChart({ scenario, currentTick }: ChartProps) {
  const data = useMemo(() => {
    const raw: Record<string, number>[] = [];
    for (let i = 0; i <= currentTick && i < scenario.tickSnapshots.length; i++) {
      const snap = scenario.tickSnapshots[i]!;
      const row: Record<string, number> = { tick: i };
      snap.stats.carOccupancy.forEach((occ, j) => {
        row[scenario.carIds[j]!] = occ;
      });
      raw.push(row);
    }
    return sample(raw, MAX_POINTS);
  }, [scenario, currentTick]);

  return (
    <div className="chart-container">
      <div className="chart-title">Car Occupancy</div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            {scenario.carIds.map((id, i) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                stroke={COLORS[i % COLORS.length]}
                dot={false}
                strokeWidth={1.5}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ThroughputChart({ scenario, currentTick }: ChartProps) {
  const data = useMemo(() => {
    const raw: { tick: number; pickups: number; dropoffs: number }[] = [];
    for (let i = 0; i <= currentTick && i < scenario.tickSnapshots.length; i++) {
      const s = scenario.tickSnapshots[i]!.stats;
      raw.push({ tick: i, pickups: s.pickupsInWindow, dropoffs: s.dropoffsInWindow });
    }
    return sample(raw, MAX_POINTS);
  }, [scenario, currentTick]);

  return (
    <div className="chart-container">
      <div className="chart-title">Throughput (per 20 ticks)</div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="pickups"
              stroke="#27ae60"
              dot={false}
              strokeWidth={1.5}
              name="Pickups"
            />
            <Line
              type="monotone"
              dataKey="dropoffs"
              stroke="#4a90d9"
              dot={false}
              strokeWidth={1.5}
              name="Dropoffs"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
