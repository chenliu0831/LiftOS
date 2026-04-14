import { useDataStore } from "../stores/data-store";
import { usePlaybackStore } from "../stores/playback-store";

export function StatsBar() {
  const scenario = useDataStore((s) => s.scenario);
  const currentTick = usePlaybackStore((s) => s.currentTick);

  if (!scenario) return null;

  const snap = scenario.tickSnapshots[currentTick];
  if (!snap) return null;

  const s = snap.stats;
  const capacity = scenario.manifest.config.capacity;

  return (
    <div className="stats-bar">
      <Stat label="Tick" value={`${currentTick}`} />
      <Sep />
      <Stat label="Served" value={`${s.served}/${s.totalPassengers}`} />
      <Stat label="Waiting" value={`${s.waiting}`} />
      <Stat label="In-Transit" value={`${s.inTransit}`} />
      <Sep />
      {s.served > 0 ? (
        <>
          <Stat
            label="Wait"
            value={`${s.waitMean.toFixed(1)} (p95: ${s.waitP95})`}
          />
          <Stat
            label="Total"
            value={`${s.totalMean.toFixed(1)} (p95: ${s.totalP95})`}
          />
        </>
      ) : (
        <span className="stat">
          <span className="stat-label">No completions yet</span>
        </span>
      )}
      <Sep />
      {snap.cars.map((car) => (
        <Stat
          key={car.car_id}
          label={car.car_id}
          value={`${car.passenger_count}/${capacity}`}
        />
      ))}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </span>
  );
}

function Sep() {
  return <span className="stat-sep" />;
}
