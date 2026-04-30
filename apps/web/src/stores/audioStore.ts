import { create } from "zustand";

const STORAGE_KEY = "flauna.audio";

export interface AudioSettings {
  muted: boolean;
  /** Master volume 0..1 */
  volume: number;
}

interface AudioStore extends AudioSettings {
  setMuted: (muted: boolean) => void;
  toggleMuted: () => void;
  setVolume: (volume: number) => void;
}

const DEFAULT: AudioSettings = { muted: false, volume: 0.6 };

function loadInitial(): AudioSettings {
  if (typeof window === "undefined") return DEFAULT;
  try {
    const raw = window.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT;
    const parsed = JSON.parse(raw) as Partial<AudioSettings>;
    return {
      muted: typeof parsed.muted === "boolean" ? parsed.muted : DEFAULT.muted,
      volume:
        typeof parsed.volume === "number"
          ? Math.min(1, Math.max(0, parsed.volume))
          : DEFAULT.volume,
    };
  } catch {
    return DEFAULT;
  }
}

function persist(state: AudioSettings): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage?.setItem(
      STORAGE_KEY,
      JSON.stringify({ muted: state.muted, volume: state.volume }),
    );
  } catch {
    // ignore (private mode etc.)
  }
}

export const useAudioStore = create<AudioStore>()((set, get) => ({
  ...loadInitial(),
  setMuted: (muted) => {
    set({ muted });
    persist(get());
  },
  toggleMuted: () => {
    set({ muted: !get().muted });
    persist(get());
  },
  setVolume: (volume) => {
    const v = Math.min(1, Math.max(0, volume));
    set({ volume: v });
    persist(get());
  },
}));

export const __AUDIO_STORAGE_KEY = STORAGE_KEY;
