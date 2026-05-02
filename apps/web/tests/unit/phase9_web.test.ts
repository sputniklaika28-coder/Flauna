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
import { useTurnStartSe } from "../../src/hooks/useTurnStartSe";
import type { Character, GamePhase, GameState } from "../../src/types";

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

describe("Phase 9 web: useTurnStartSe hook", () => {
  function makeChar(over: Partial<Character> & Pick<Character, "id">): Character {
    return {
      id: over.id,
      name: over.name ?? over.id,
      player_id: over.player_id ?? null,
      faction: over.faction ?? "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 3,
      evasion_dice: 2,
      max_evasion_dice: 2,
      position: [0, 0],
      equipped_weapons: [],
      equipped_jacket: null,
      armor_value: 0,
      inventory: {},
      skills: [],
      arts: [],
      status_effects: [],
      has_acted_this_turn: false,
      movement_used_this_turn: 0,
      first_move_mode: null,
    };
  }

  function makeState(
    over: Partial<GameState> & Pick<GameState, "characters" | "turn_order">,
  ): GameState {
    return {
      room_id: "r",
      version: 1,
      seed: 1,
      phase: "combat",
      machine_state: over.machine_state ?? "IDLE",
      turn_order: over.turn_order,
      current_turn_index: over.current_turn_index ?? 0,
      round_number: 1,
      characters: over.characters,
      map_size: [10, 10],
      obstacles: [],
      current_turn_summary: null,
      pending_actions: [],
    };
  }

  function TurnHarness({
    gameState,
    myPlayerId,
  }: {
    gameState: GameState | null;
    myPlayerId: string | null;
  }) {
    useTurnStartSe(gameState, myPlayerId);
    return null;
  }

  beforeEach(() => {
    useAudioStore.setState({ muted: false, volume: 0.6 });
  });

  it("plays your_turn SE on the transition into the local player's turn", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });

    const me = makeChar({ id: "c1", player_id: "p1" });
    const enemy = makeChar({ id: "e1", faction: "enemy" });
    const stateEnemyTurn = makeState({
      characters: [me, enemy],
      turn_order: ["e1", "c1"],
      current_turn_index: 0,
    });
    const stateMyTurn = makeState({
      characters: [me, enemy],
      turn_order: ["e1", "c1"],
      current_turn_index: 1,
    });

    const { rerender } = render(
      React.createElement(TurnHarness, {
        gameState: stateEnemyTurn,
        myPlayerId: "p1",
      }),
    );
    // First render establishes baseline; no SE yet.
    expect(playSeSpy).not.toHaveBeenCalled();

    rerender(
      React.createElement(TurnHarness, {
        gameState: stateMyTurn,
        myPlayerId: "p1",
      }),
    );
    expect(playSeSpy).toHaveBeenCalledTimes(1);
    expect(playSeSpy).toHaveBeenCalledWith("your_turn", 0.6);
  });

  it("does not replay the SE on consecutive states where it is still my turn", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });

    const me = makeChar({ id: "c1", player_id: "p1" });
    const stateEnemy = makeState({
      characters: [me],
      turn_order: ["x", "c1"],
      current_turn_index: 0,
    });
    const stateMine = makeState({
      characters: [me],
      turn_order: ["x", "c1"],
      current_turn_index: 1,
    });

    const { rerender } = render(
      React.createElement(TurnHarness, {
        gameState: stateEnemy,
        myPlayerId: "p1",
      }),
    );
    rerender(
      React.createElement(TurnHarness, {
        gameState: stateMine,
        myPlayerId: "p1",
      }),
    );
    rerender(
      React.createElement(TurnHarness, {
        gameState: { ...stateMine, version: 2 },
        myPlayerId: "p1",
      }),
    );
    expect(playSeSpy).toHaveBeenCalledTimes(1);
  });

  it("does not fire on the initial render even if it is already my turn", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });

    const me = makeChar({ id: "c1", player_id: "p1" });
    const stateMine = makeState({
      characters: [me],
      turn_order: ["c1"],
      current_turn_index: 0,
    });

    render(
      React.createElement(TurnHarness, {
        gameState: stateMine,
        myPlayerId: "p1",
      }),
    );
    expect(playSeSpy).not.toHaveBeenCalled();
  });

  it("does not fire while machine_state is non-IDLE", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });

    const me = makeChar({ id: "c1", player_id: "p1" });
    const stateEnemy = makeState({
      characters: [me],
      turn_order: ["x", "c1"],
      current_turn_index: 0,
    });
    const stateMineResolving = makeState({
      characters: [me],
      turn_order: ["x", "c1"],
      current_turn_index: 1,
      machine_state: "RESOLVING_ACTION",
    });

    const { rerender } = render(
      React.createElement(TurnHarness, {
        gameState: stateEnemy,
        myPlayerId: "p1",
      }),
    );
    rerender(
      React.createElement(TurnHarness, {
        gameState: stateMineResolving,
        myPlayerId: "p1",
      }),
    );
    expect(playSeSpy).not.toHaveBeenCalled();
  });
});
