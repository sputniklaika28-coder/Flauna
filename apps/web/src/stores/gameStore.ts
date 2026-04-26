import { create } from "zustand";

import type { ConnectionStatus, GameState } from "../types/server";

interface GameStore {
  gameState: GameState | null;
  connectionStatus: ConnectionStatus;
  lastSeenEventId: number;
  setGameState: (state: GameState) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setLastSeenEventId: (id: number) => void;
}

export const useGameStore = create<GameStore>((set) => ({
  gameState: null,
  connectionStatus: "DISCONNECTED",
  lastSeenEventId: 0,
  setGameState: (gameState) => set({ gameState }),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setLastSeenEventId: (lastSeenEventId) => set({ lastSeenEventId }),
}));
