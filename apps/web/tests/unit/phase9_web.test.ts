import {
  describe,
  it,
  expect,
  beforeAll,
  beforeEach,
  afterEach,
  vi,
} from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  act,
} from "@testing-library/react";
import React from "react";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import { useAudioStore, __AUDIO_STORAGE_KEY } from "../../src/stores/audioStore";
import {
  playSe,
  playBgm,
  stopBgm,
  setAudioBackend,
} from "../../src/services/audio";
import AudioSettings from "../../src/components/common/AudioSettings";
import { usePhaseBgm } from "../../src/hooks/usePhaseBgm";
import type { GamePhase } from "../../src/types";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  // Reset the store to defaults between tests.
  useAudioStore.setState({ muted: false, volume: 0.6 });
});

describe("Phase 9 web: i18n keys", () => {
  it("ja and en both expose the audio settings keys", () => {
    expect(ja).toHaveProperty("settings.audio.mute");
    expect(ja).toHaveProperty("settings.audio.unmute");
    expect(ja).toHaveProperty("settings.audio.volume");
    expect(en).toHaveProperty("settings.audio.mute");
    expect(en).toHaveProperty("settings.audio.unmute");
    expect(en).toHaveProperty("settings.audio.volume");
  });

  it("ja and en still have identical key sets after Phase 9", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ja).sort());
  });
});

describe("Phase 9 web: audioStore", () => {
  it("clamps volume into [0, 1]", () => {
    useAudioStore.getState().setVolume(2);
    expect(useAudioStore.getState().volume).toBe(1);
    useAudioStore.getState().setVolume(-0.5);
    expect(useAudioStore.getState().volume).toBe(0);
  });

  it("toggleMuted flips the muted flag", () => {
    expect(useAudioStore.getState().muted).toBe(false);
    useAudioStore.getState().toggleMuted();
    expect(useAudioStore.getState().muted).toBe(true);
    useAudioStore.getState().toggleMuted();
    expect(useAudioStore.getState().muted).toBe(false);
  });

  it("persists muted and volume to localStorage", () => {
    useAudioStore.getState().setMuted(true);
    useAudioStore.getState().setVolume(0.25);
    const raw = window.localStorage.getItem(__AUDIO_STORAGE_KEY);
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw as string) as {
      muted: boolean;
      volume: number;
    };
    expect(parsed.muted).toBe(true);
    expect(parsed.volume).toBe(0.25);
  });
});

describe("Phase 9 web: audio service", () => {
  beforeEach(() => {
    useAudioStore.setState({ muted: false, volume: 0.6 });
  });

  it("delegates playSe to the backend with the effective volume", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    useAudioStore.getState().setVolume(0.5);
    playSe("damage");
    expect(playSeSpy).toHaveBeenCalledTimes(1);
    expect(playSeSpy).toHaveBeenCalledWith("damage", 0.5);
  });

  it("does not invoke the backend playSe when muted", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    useAudioStore.getState().setMuted(true);
    playSe("victory");
    expect(playSeSpy).not.toHaveBeenCalled();
  });

  it("forwards playBgm and stopBgm to the backend", () => {
    const playBgmSpy = vi.fn();
    const stopBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: playBgmSpy,
      stopBgm: stopBgmSpy,
    });
    playBgm("combat");
    expect(playBgmSpy).toHaveBeenCalledWith("combat", 0.6);
    stopBgm();
    expect(stopBgmSpy).toHaveBeenCalledTimes(1);
  });
});

describe("Phase 9 web: AudioSettings component", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    useAudioStore.setState({ muted: false, volume: 0.6 });
    await i18n.changeLanguage("ja");
  });

  it("renders mute toggle and volume slider", () => {
    render(React.createElement(AudioSettings));
    expect(screen.getByTestId("audio-mute-toggle")).toBeTruthy();
    expect(screen.getByTestId("audio-volume-slider")).toBeTruthy();
  });

  it("toggles mute when the button is clicked", async () => {
    render(React.createElement(AudioSettings));
    const btn = screen.getByTestId("audio-mute-toggle");
    expect(useAudioStore.getState().muted).toBe(false);
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(useAudioStore.getState().muted).toBe(true);
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(useAudioStore.getState().muted).toBe(false);
  });

  it("updates the store when the slider changes", async () => {
    render(React.createElement(AudioSettings));
    const slider = screen.getByTestId(
      "audio-volume-slider",
    ) as HTMLInputElement;
    await act(async () => {
      fireEvent.change(slider, { target: { value: "30" } });
    });
    expect(useAudioStore.getState().volume).toBeCloseTo(0.3, 5);
  });

  it("disables the slider when muted", async () => {
    useAudioStore.setState({ muted: true });
    render(React.createElement(AudioSettings));
    const slider = screen.getByTestId(
      "audio-volume-slider",
    ) as HTMLInputElement;
    expect(slider.disabled).toBe(true);
  });
});

describe("Phase 9 web: usePhaseBgm hook", () => {
  function PhaseHarness({ phase }: { phase: GamePhase | undefined }) {
    usePhaseBgm(phase);
    return null;
  }

  beforeEach(() => {
    useAudioStore.setState({ muted: false, volume: 0.6 });
  });

  it("plays combat BGM when phase is combat", () => {
    const playBgmSpy = vi.fn();
    const stopBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: playBgmSpy,
      stopBgm: stopBgmSpy,
    });
    render(React.createElement(PhaseHarness, { phase: "combat" }));
    expect(playBgmSpy).toHaveBeenCalledWith("combat", 0.6);
  });

  it("plays exploration BGM when phase is briefing or exploration", () => {
    const playBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: playBgmSpy,
      stopBgm: vi.fn(),
    });
    const { rerender } = render(
      React.createElement(PhaseHarness, { phase: "briefing" }),
    );
    expect(playBgmSpy).toHaveBeenLastCalledWith("exploration", 0.6);
    rerender(React.createElement(PhaseHarness, { phase: "exploration" }));
    expect(playBgmSpy).toHaveBeenLastCalledWith("exploration", 0.6);
  });

  it("stops BGM when phase becomes assessment", () => {
    const stopBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: vi.fn(),
      stopBgm: stopBgmSpy,
    });
    render(React.createElement(PhaseHarness, { phase: "assessment" }));
    expect(stopBgmSpy).toHaveBeenCalled();
  });

  it("stops BGM on unmount", () => {
    const stopBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: vi.fn(),
      stopBgm: stopBgmSpy,
    });
    const { unmount } = render(
      React.createElement(PhaseHarness, { phase: "combat" }),
    );
    stopBgmSpy.mockClear();
    unmount();
    expect(stopBgmSpy).toHaveBeenCalled();
  });

  it("is a no-op when phase is undefined", () => {
    const playBgmSpy = vi.fn();
    const stopBgmSpy = vi.fn();
    setAudioBackend({
      playSe: vi.fn(),
      playBgm: playBgmSpy,
      stopBgm: stopBgmSpy,
    });
    render(React.createElement(PhaseHarness, { phase: undefined }));
    expect(playBgmSpy).not.toHaveBeenCalled();
    expect(stopBgmSpy).not.toHaveBeenCalled();
  });
});
