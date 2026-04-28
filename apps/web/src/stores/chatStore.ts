import { create } from "zustand";
import { nanoid } from "nanoid";
import type { ChatEntry, ChatKind } from "../types";

interface ChatStore {
  entries: ChatEntry[];
  addEntry: (kind: ChatKind, text: string, timestamp?: string, isStreaming?: boolean) => void;
  updateLastNarrative: (text: string, isStreaming: boolean) => void;
  clear: () => void;
}

export const useChatStore = create<ChatStore>()((set, get) => ({
  entries: [],

  addEntry: (kind, text, timestamp, isStreaming) =>
    set((s) => ({
      entries: [
        ...s.entries,
        {
          id: nanoid(),
          kind,
          text,
          timestamp: timestamp ?? new Date().toISOString(),
          isStreaming,
        },
      ],
    })),

  updateLastNarrative: (text, isStreaming) => {
    const entries = get().entries;
    const last = entries[entries.length - 1];
    if (last?.kind === "gm_narrative" && last.isStreaming) {
      set({
        entries: [
          ...entries.slice(0, -1),
          { ...last, text, isStreaming },
        ],
      });
    } else {
      get().addEntry("gm_narrative", text, undefined, isStreaming);
    }
  },

  clear: () => set({ entries: [] }),
}));
