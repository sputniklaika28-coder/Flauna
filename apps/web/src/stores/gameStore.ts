import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { ConnectionStatus, GameState } from "../types";

interface GameStore {
  gameState: GameState | null;
  connectionStatus: ConnectionStatus;
  lastSeenEventId: number;
  myPlayerId: string | null;
  myToken: string | null;

  setGameState: (state: GameState) => void;
  applyStateFull: (state: GameState) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setLastSeenEventId: (id: number) => void;
  setAuth: (playerId: string, token: string) => void;
}

export const useGameStore = create<GameStore>()(
  devtools(
    (set) => ({
      gameState: null,
      connectionStatus: "DISCONNECTED",
      lastSeenEventId: 0,
      myPlayerId: null,
      myToken: null,

      setGameState: (state) => set({ gameState: state }),
      applyStateFull: (state) =>
        set({ gameState: state, lastSeenEventId: state.version }),
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setLastSeenEventId: (id) => set({ lastSeenEventId: id }),
      setAuth: (playerId, token) =>
        set({ myPlayerId: playerId, myToken: token }),
    }),
    { name: "gameStore" },
  ),
);
