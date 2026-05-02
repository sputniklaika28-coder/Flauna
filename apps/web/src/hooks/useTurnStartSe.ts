import { useEffect, useRef } from "react";
import { playSe } from "../services/audio";
import type { GameState } from "../types";

/**
 * Phase 9 UX: fire the `your_turn` SE the moment the local player gains
 * control (turn_order rotates onto one of their characters and the machine
 * settles back to IDLE). The cue intentionally does not fire on the very
 * first state load — only on transitions, so reconnects don't replay it.
 */
export function useTurnStartSe(
  gameState: GameState | null | undefined,
  myPlayerId: string | null,
): void {
  const prevIsMyTurnRef = useRef<boolean | null>(null);

  useEffect(() => {
    if (!gameState || !myPlayerId) {
      prevIsMyTurnRef.current = null;
      return;
    }

    const { turn_order, current_turn_index, characters, machine_state } =
      gameState;
    const currentActorId =
      turn_order.length > 0
        ? turn_order[current_turn_index % turn_order.length]
        : null;
    const currentActor = characters.find((c) => c.id === currentActorId);
    const isMyTurn =
      currentActor?.player_id === myPlayerId && machine_state === "IDLE";

    const prev = prevIsMyTurnRef.current;
    if (prev === false && isMyTurn) {
      playSe("your_turn");
    }
    prevIsMyTurnRef.current = isMyTurn;
  }, [gameState, myPlayerId]);
}
