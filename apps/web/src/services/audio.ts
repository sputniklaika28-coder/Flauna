/**
 * Lightweight audio service for SE / BGM playback.
 *
 * Phase 9: thin wrapper over HTMLAudioElement so the rest of the app can fire
 * named cues (`playSe("damage")`) without caring about implementation details.
 * Audio assets are not yet bundled — calls are no-ops when the cue is unknown
 * or when the host environment lacks Audio support (jsdom, SSR).
 */

import { useAudioStore } from "../stores/audioStore";

export type SeCue =
  | "damage"
  | "victory"
  | "defeat"
  | "cast_art"
  | "escalation"
  | "your_turn"
  | "evade_alert"
  | "death_avoidance_alert"
  | "deadline_tick";

export type BgmCue = "combat" | "exploration";

interface AudioBackend {
  playSe(cue: SeCue, volume: number): void;
  playBgm(cue: BgmCue, volume: number): void;
  stopBgm(): void;
}

/** Map of cue → asset URL. Empty values mean "no asset bundled yet". */
const SE_URLS: Record<SeCue, string> = {
  damage: "",
  victory: "",
  defeat: "",
  cast_art: "",
  escalation: "",
  your_turn: "",
  evade_alert: "",
  death_avoidance_alert: "",
  deadline_tick: "",
};

const BGM_URLS: Record<BgmCue, string> = {
  combat: "",
  exploration: "",
};

class HtmlAudioBackend implements AudioBackend {
  private bgm: HTMLAudioElement | null = null;
  private currentBgmCue: BgmCue | null = null;

  playSe(cue: SeCue, volume: number): void {
    const url = SE_URLS[cue];
    if (!url || typeof Audio === "undefined") return;
    try {
      const a = new Audio(url);
      a.volume = volume;
      void a.play().catch(() => {
        // Autoplay blocked or asset missing — silent fail.
      });
    } catch {
      // ignore
    }
  }

  playBgm(cue: BgmCue, volume: number): void {
    const url = BGM_URLS[cue];
    if (!url || typeof Audio === "undefined") return;
    if (this.currentBgmCue === cue && this.bgm) {
      this.bgm.volume = volume;
      return;
    }
    this.stopBgm();
    try {
      const a = new Audio(url);
      a.loop = true;
      a.volume = volume;
      void a.play().catch(() => {
        /* ignore */
      });
      this.bgm = a;
      this.currentBgmCue = cue;
    } catch {
      // ignore
    }
  }

  stopBgm(): void {
    if (this.bgm) {
      try {
        this.bgm.pause();
      } catch {
        // ignore
      }
    }
    this.bgm = null;
    this.currentBgmCue = null;
  }
}

let backend: AudioBackend = new HtmlAudioBackend();

/** Test seam: swap the backend (e.g. with a spy in unit tests). */
export function setAudioBackend(b: AudioBackend): void {
  backend = b;
}

function effectiveVolume(): number {
  const { muted, volume } = useAudioStore.getState();
  return muted ? 0 : volume;
}

export function playSe(cue: SeCue): void {
  const v = effectiveVolume();
  if (v <= 0) return;
  backend.playSe(cue, v);
}

export function playBgm(cue: BgmCue): void {
  const v = effectiveVolume();
  // Always tell the backend so it can update volume / restart on unmute.
  backend.playBgm(cue, v);
}

export function stopBgm(): void {
  backend.stopBgm();
}
