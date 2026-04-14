import { useEffect, useRef, useCallback } from "react";
import { usePlaybackStore } from "../stores/playback-store";

const SPEED_STOPS = [1, 2, 5, 10, 20, 50, 100];

function nearestStop(val: number): number {
  let best = SPEED_STOPS[0]!;
  for (const s of SPEED_STOPS) {
    if (Math.abs(s - val) < Math.abs(best - val)) best = s;
  }
  return best;
}

export function PlaybackControls() {
  const status = usePlaybackStore((s) => s.status);
  const currentTick = usePlaybackStore((s) => s.currentTick);
  const speed = usePlaybackStore((s) => s.speed);
  const maxTick = usePlaybackStore((s) => s.maxTick);
  const play = usePlaybackStore((s) => s.play);
  const pause = usePlaybackStore((s) => s.pause);
  const stepForward = usePlaybackStore((s) => s.stepForward);
  const stepBackward = usePlaybackStore((s) => s.stepBackward);
  const setTick = usePlaybackStore((s) => s.setTick);
  const setSpeed = usePlaybackStore((s) => s.setSpeed);

  // Animation loop
  usePlaybackLoop();

  // Keyboard shortcuts
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        if (status === "playing") pause();
        else play();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        stepForward();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        stepBackward();
      }
    },
    [status, play, pause, stepForward, stepBackward],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  const isPlaying = status === "playing";
  const disabled = maxTick === 0;

  return (
    <div className="playback-bar">
      <div className="playback-buttons">
        <button onClick={stepBackward} disabled={disabled || currentTick === 0} title="Step back">
          &#9664;&#9664;
        </button>
        <button
          onClick={isPlaying ? pause : play}
          disabled={disabled}
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? "\u23F8" : "\u25B6"}
        </button>
        <button
          onClick={stepForward}
          disabled={disabled || currentTick >= maxTick}
          title="Step forward"
        >
          &#9654;&#9654;
        </button>
      </div>

      <input
        type="range"
        className="scrubber"
        min={0}
        max={maxTick}
        value={currentTick}
        onChange={(e) => setTick(Number(e.target.value))}
        disabled={disabled}
      />

      <span className="tick-display">
        Tick {currentTick} / {maxTick}
      </span>

      <div className="speed-control">
        <span>Speed</span>
        <input
          type="range"
          min={0}
          max={SPEED_STOPS.length - 1}
          value={SPEED_STOPS.indexOf(nearestStop(speed))}
          onChange={(e) => setSpeed(SPEED_STOPS[Number(e.target.value)]!)}
        />
        <span className="speed-value">{speed}x</span>
      </div>
    </div>
  );
}

function usePlaybackLoop() {
  const status = usePlaybackStore((s) => s.status);
  const accRef = useRef(0);
  const lastRef = useRef(0);

  useEffect(() => {
    if (status !== "playing") return;

    accRef.current = 0;
    lastRef.current = 0;

    let rafId: number;

    const loop = (timestamp: number) => {
      if (lastRef.current === 0) lastRef.current = timestamp;
      const delta = timestamp - lastRef.current;
      lastRef.current = timestamp;

      const state = usePlaybackStore.getState();
      if (state.status !== "playing") return;

      const msPerTick = 1000 / state.speed;
      accRef.current += delta;

      let steps = 0;
      while (accRef.current >= msPerTick && steps < 10) {
        accRef.current -= msPerTick;
        usePlaybackStore.getState().advanceTick();
        steps++;
        if (usePlaybackStore.getState().status !== "playing") return;
      }
      // Cap accumulator to prevent spiral after tab switch
      if (accRef.current > msPerTick * 2) accRef.current = 0;

      rafId = requestAnimationFrame(loop);
    };

    rafId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafId);
  }, [status]);
}
