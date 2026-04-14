import { useDataStore } from "../stores/data-store";
import { usePlaybackStore } from "../stores/playback-store";

const FLOOR_HEIGHT = 28;
const SHAFT_WIDTH = 44;
const SHAFT_GAP = 4;
const CAR_WIDTH = 36;
const CAR_HEIGHT = 22;
const LABEL_WIDTH = 32;
const WAITING_WIDTH = 50;
const PAD_Y = 16;

export function BuildingView() {
  const scenario = useDataStore((s) => s.scenario);
  const currentTick = usePlaybackStore((s) => s.currentTick);

  if (!scenario) {
    return <div className="building-empty">Select a run to begin</div>;
  }

  const snapshot = scenario.tickSnapshots[currentTick];
  if (!snapshot) return null;

  const numFloors = scenario.manifest.config.floors;
  const numCars = scenario.carIds.length;
  const capacity = scenario.manifest.config.capacity;

  const totalWidth =
    LABEL_WIDTH + numCars * (SHAFT_WIDTH + SHAFT_GAP) + WAITING_WIDTH;
  const totalHeight = numFloors * FLOOR_HEIGHT + PAD_Y * 2;

  const floorY = (floor: number) =>
    (numFloors - floor) * FLOOR_HEIGHT + PAD_Y;

  const shaftX = (carIdx: number) =>
    LABEL_WIDTH + carIdx * (SHAFT_WIDTH + SHAFT_GAP);

  const floors = Array.from({ length: numFloors }, (_, i) => i + 1);

  return (
    <svg
      viewBox={`0 0 ${totalWidth} ${totalHeight}`}
      width={totalWidth}
      height={totalHeight}
      style={{ display: "block" }}
    >
      {/* Floor lines and labels */}
      {floors.map((f) => {
        const y = floorY(f);
        return (
          <g key={`floor-${f}`}>
            <line
              x1={LABEL_WIDTH}
              x2={totalWidth - WAITING_WIDTH}
              y1={y}
              y2={y}
              stroke="#2a2a4a"
              strokeWidth={0.5}
            />
            <text
              x={LABEL_WIDTH - 6}
              y={y + 4}
              textAnchor="end"
              fill="#666"
              fontSize={10}
            >
              {f}
            </text>
          </g>
        );
      })}

      {/* Shaft backgrounds */}
      {scenario.carIds.map((_, i) => (
        <rect
          key={`shaft-${i}`}
          x={shaftX(i)}
          y={PAD_Y}
          width={SHAFT_WIDTH}
          height={numFloors * FLOOR_HEIGHT}
          fill="#12122a"
          stroke="#1a1a3a"
          strokeWidth={0.5}
          rx={2}
        />
      ))}

      {/* Car labels at bottom */}
      {scenario.carIds.map((id, i) => (
        <text
          key={`label-${id}`}
          x={shaftX(i) + SHAFT_WIDTH / 2}
          y={totalHeight - 2}
          textAnchor="middle"
          fill="#666"
          fontSize={9}
        >
          {id}
        </text>
      ))}

      {/* Elevator cars */}
      {snapshot.cars.map((car, i) => {
        const x = shaftX(i) + (SHAFT_WIDTH - CAR_WIDTH) / 2;
        const y = floorY(car.floor) - CAR_HEIGHT / 2;
        const loadRatio = car.passenger_count / capacity;
        const fillColor =
          car.passenger_count === 0
            ? "#2a2a4a"
            : loadRatio >= 0.75
              ? "#8b3a3a"
              : "#4a6fa5";
        const borderColor =
          car.direction === "up"
            ? "#4ade80"
            : car.direction === "down"
              ? "#f59e0b"
              : "#555";

        return (
          <g
            key={car.car_id}
            style={{
              transition: "transform 150ms ease",
              transform: `translate(${x}px, ${y}px)`,
            }}
          >
            <rect
              width={CAR_WIDTH}
              height={CAR_HEIGHT}
              rx={3}
              fill={fillColor}
              stroke={borderColor}
              strokeWidth={1.5}
            />
            {/* Passenger count */}
            <text
              x={CAR_WIDTH / 2}
              y={CAR_HEIGHT / 2 + 4}
              textAnchor="middle"
              fill="#fff"
              fontSize={11}
              fontWeight={600}
            >
              {car.passenger_count}
            </text>
            {/* Direction arrow */}
            {car.direction === "up" && (
              <polygon
                points={`${CAR_WIDTH / 2 - 4},-2 ${CAR_WIDTH / 2 + 4},-2 ${CAR_WIDTH / 2},-7`}
                fill={borderColor}
              />
            )}
            {car.direction === "down" && (
              <polygon
                points={`${CAR_WIDTH / 2 - 4},${CAR_HEIGHT + 2} ${CAR_WIDTH / 2 + 4},${CAR_HEIGHT + 2} ${CAR_WIDTH / 2},${CAR_HEIGHT + 7}`}
                fill={borderColor}
              />
            )}
          </g>
        );
      })}

      {/* Waiting passengers */}
      {floors.map((f) => {
        const count = snapshot.waitingByFloor.get(f) ?? 0;
        if (count === 0) return null;
        const y = floorY(f);
        const x = totalWidth - WAITING_WIDTH + 8;
        return (
          <g key={`wait-${f}`}>
            <circle cx={x} cy={y} r={4} fill="#e74c3c" opacity={0.8} />
            <text x={x + 10} y={y + 4} fill="#e74c3c" fontSize={10}>
              {count}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
