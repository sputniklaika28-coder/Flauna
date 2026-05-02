import { useEffect, useRef } from "react";
import { playSe } from "../services/audio";

export interface DeadlineUrgency {
  /** True when remaining time has entered the warning band (≤ warnAt). */
  isWarning: boolean;
  /** True when remaining time has entered the critical band (≤ criticalAt). */
  isCritical: boolean;
  /** True once the deadline has elapsed (reached 0). */
  isExpired: boolean;
}

export interface DeadlineUrgencyOptions {
  /** Threshold (in seconds) for the warning band. Default: 10. */
  warnAt?: number;
  /** Threshold (in seconds) for the critical band that ticks each second. Default: 5. */
  criticalAt?: number;
}

/**
 * §16 (アラームタイマー) / §9-2 UX: derive urgency flags from a countdown
 * value and fire the `deadline_tick` SE once per second while in the critical
 * band.
 *
 * The hook is intentionally driven by an externally-managed `secondsLeft`
 * counter so callers keep ownership of the timer (which is reset whenever a
 * new pending arrives). The hook only watches the value and triggers side
 * effects on transitions — it does not run a timer itself.
 *
 * The tick fires only on a *decrement* into the critical band so that
 * remounts or value resets (e.g. dialog reopened with a fresh deadline) do
 * not spam the cue. When `active` is false (no pending dialog), no SE plays
 * regardless of the countdown value.
 */
export function useDeadlineUrgency(
  secondsLeft: number,
  active: boolean,
  options: DeadlineUrgencyOptions = {},
): DeadlineUrgency {
  const warnAt = options.warnAt ?? 10;
  const criticalAt = options.criticalAt ?? 5;
  const prevRef = useRef<number | null>(null);

  useEffect(() => {
    const prev = prevRef.current;
    prevRef.current = secondsLeft;
    if (!active) return;
    if (prev === null) return;
    if (secondsLeft >= prev) return;
    if (secondsLeft > 0 && secondsLeft <= criticalAt) {
      playSe("deadline_tick");
    }
  }, [secondsLeft, active, criticalAt]);

  useEffect(() => {
    if (!active) {
      prevRef.current = null;
    }
  }, [active]);

  return {
    isWarning: active && secondsLeft > 0 && secondsLeft <= warnAt,
    isCritical: active && secondsLeft > 0 && secondsLeft <= criticalAt,
    isExpired: active && secondsLeft <= 0,
  };
}
