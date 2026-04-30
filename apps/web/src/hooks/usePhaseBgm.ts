import { useEffect } from "react";
import { playBgm, stopBgm } from "../services/audio";
import type { GamePhase } from "../types";

/**
 * Drive BGM cues from the current GamePhase. Combat plays the combat BGM,
 * briefing/exploration plays the exploration BGM, assessment stops BGM, and
 * the cue is also stopped on unmount.
 */
export function usePhaseBgm(phase: GamePhase | undefined): void {
  useEffect(() => {
    if (!phase) return;
    if (phase === "combat") {
      playBgm("combat");
    } else if (phase === "briefing" || phase === "exploration") {
      playBgm("exploration");
    } else if (phase === "assessment") {
      stopBgm();
    }
  }, [phase]);

  useEffect(() => {
    return () => {
      stopBgm();
    };
  }, []);
}
