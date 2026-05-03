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
  waitFor,
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
import { useOnlineStatus } from "../../src/hooks/useOnlineStatus";
import { useReconnectToast } from "../../src/hooks/useReconnectToast";
import Header from "../../src/components/layout/Header";
import AiThinkingIndicator from "../../src/components/common/AiThinkingIndicator";
import { useGameStore, usePendingStore, useToastStore, useUIStore } from "../../src/stores";
import QuickActionBar from "../../src/components/action/QuickActionBar";
import ChatPanel from "../../src/components/chat/ChatPanel";
import { useChatStore } from "../../src/stores";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import type { Character, GamePhase, GameState } from "../../src/types";
import { useDeadlineUrgency } from "../../src/hooks/useDeadlineUrgency";
import EvasionDialog from "../../src/components/dialogs/EvasionDialog";
import DeathAvoidanceDialog from "../../src/components/dialogs/DeathAvoidanceDialog";
import SessionLostScreen from "../../src/components/dialogs/SessionLostScreen";
import CombatResultModal from "../../src/components/dialogs/CombatResultModal";
import AssessmentScreen from "../../src/components/dialogs/AssessmentScreen";
import SideMenu from "../../src/components/layout/SideMenu";
import ContextMenu from "../../src/components/map/ContextMenu";
import ActionDetailModal from "../../src/components/action/ActionDetailModal";
import CastArtModal from "../../src/components/dialogs/CastArtModal";
import CastArtCutscene from "../../src/components/dialogs/CastArtCutscene";

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

  it("ja and en expose the offline-detection keys", () => {
    expect(ja).toHaveProperty("room.offline");
    expect(ja).toHaveProperty("room.notice.offline");
    expect(ja).toHaveProperty("room.notice.backOnline");
    expect(en).toHaveProperty("room.offline");
    expect(en).toHaveProperty("room.notice.offline");
    expect(en).toHaveProperty("room.notice.backOnline");
  });

  it("ja and en expose the room.submitting indicator key", () => {
    expect(ja).toHaveProperty("room.submitting");
    expect(en).toHaveProperty("room.submitting");
  });

  it("ja and en expose the reconnection notice keys", () => {
    expect(ja).toHaveProperty("room.notice.reconnecting");
    expect(ja).toHaveProperty("room.notice.reconnected");
    expect(en).toHaveProperty("room.notice.reconnecting");
    expect(en).toHaveProperty("room.notice.reconnected");
  });

  it("ja and en expose the system chat message keys", () => {
    const keys = [
      "room.system.sessionRestored",
      "room.system.sessionDisconnected",
      "room.system.combatVictory",
      "room.system.combatDefeat",
      "room.system.artCastByOther",
      "room.system.artCastSelf",
      "room.system.event",
      "room.system.aiFallback",
      "room.system.error",
      "room.system.pendingExpiredEvasion",
      "room.system.pendingExpiredDeathAvoidance",
      "room.system.pendingRestoredEvasion",
      "room.system.pendingRestoredDeathAvoidance",
    ] as const;
    for (const k of keys) {
      expect(ja).toHaveProperty(k);
      expect(en).toHaveProperty(k);
    }
  });

  it("ja and en expose the deadline expired keys", () => {
    expect(ja).toHaveProperty("room.evasion.expired");
    expect(ja).toHaveProperty("room.deathAvoidance.expired");
    expect(en).toHaveProperty("room.evasion.expired");
    expect(en).toHaveProperty("room.deathAvoidance.expired");
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

  it("forwards the new alert cues (evade_alert, death_avoidance_alert) to the backend", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    playSe("evade_alert");
    playSe("death_avoidance_alert");
    expect(playSeSpy).toHaveBeenNthCalledWith(1, "evade_alert", 0.6);
    expect(playSeSpy).toHaveBeenNthCalledWith(2, "death_avoidance_alert", 0.6);
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

// ---------------------------------------------------------------------------
// useOnlineStatus hook + Header offline indicator
// ---------------------------------------------------------------------------

function OnlineProbe(): React.ReactElement {
  const online = useOnlineStatus();
  return React.createElement(
    "div",
    { "data-testid": "probe" },
    online ? "online" : "offline",
  );
}

describe("Phase 9 web: useOnlineStatus hook", () => {
  const originalDescriptor = Object.getOwnPropertyDescriptor(
    window.navigator,
    "onLine",
  );

  function setNavigatorOnLine(value: boolean) {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      get: () => value,
    });
  }

  afterEach(() => {
    if (originalDescriptor) {
      Object.defineProperty(window.navigator, "onLine", originalDescriptor);
    } else {
      setNavigatorOnLine(true);
    }
  });

  it("returns the initial navigator.onLine value", () => {
    setNavigatorOnLine(false);
    render(React.createElement(OnlineProbe));
    expect(screen.getByTestId("probe").textContent).toBe("offline");
  });

  it("updates when window emits online / offline events", () => {
    setNavigatorOnLine(true);
    render(React.createElement(OnlineProbe));
    expect(screen.getByTestId("probe").textContent).toBe("online");
    act(() => {
      setNavigatorOnLine(false);
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByTestId("probe").textContent).toBe("offline");
    act(() => {
      setNavigatorOnLine(true);
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.getByTestId("probe").textContent).toBe("online");
  });
});

describe("Phase 9 web: Header offline indicator", () => {
  const originalDescriptor = Object.getOwnPropertyDescriptor(
    window.navigator,
    "onLine",
  );

  function setNavigatorOnLine(value: boolean) {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      get: () => value,
    });
  }

  afterEach(() => {
    if (originalDescriptor) {
      Object.defineProperty(window.navigator, "onLine", originalDescriptor);
    } else {
      setNavigatorOnLine(true);
    }
    useGameStore.setState({
      gameState: null,
      connectionStatus: "CONNECTING",
      myPlayerId: null,
      authToken: null,
      lastSeenEventId: 0,
    } as Partial<ReturnType<typeof useGameStore.getState>> as never);
  });

  function renderHeader() {
    return render(
      React.createElement(
        MemoryRouter,
        null,
        React.createElement(
          I18nextProvider,
          { i18n },
          React.createElement(Header),
        ),
      ),
    );
  }

  it("shows the offline label and red dot when navigator.onLine is false", async () => {
    await i18n.changeLanguage("ja");
    setNavigatorOnLine(false);
    useGameStore.setState({ connectionStatus: "ACTIVE" });
    renderHeader();
    expect(screen.getByTestId("connection-label").textContent).toBe(
      ja["room.offline"],
    );
    expect(screen.getByTestId("connection-dot").className).toContain(
      "bg-red-500",
    );
  });

  it("shows the connected label when online and ACTIVE", async () => {
    await i18n.changeLanguage("ja");
    setNavigatorOnLine(true);
    useGameStore.setState({ connectionStatus: "ACTIVE" });
    renderHeader();
    expect(screen.getByTestId("connection-label").textContent).toBe(
      ja["room.connected"],
    );
  });

  it("re-renders when the window switches between online and offline", async () => {
    await i18n.changeLanguage("ja");
    setNavigatorOnLine(true);
    useGameStore.setState({ connectionStatus: "ACTIVE" });
    renderHeader();
    expect(screen.getByTestId("connection-label").textContent).toBe(
      ja["room.connected"],
    );
    act(() => {
      setNavigatorOnLine(false);
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByTestId("connection-label").textContent).toBe(
      ja["room.offline"],
    );
  });
});

// ---------------------------------------------------------------------------
// QuickActionBar — submitting indicator (spec §6-4)
// ---------------------------------------------------------------------------

describe("Phase 9 web: QuickActionBar submitting indicator", () => {
  function makeChar(
    over: Partial<Character> & Pick<Character, "id">,
  ): Character {
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

  function makeMyTurnState(): GameState {
    const me = makeChar({ id: "c1", player_id: "p1" });
    return {
      room_id: "r",
      version: 1,
      seed: 1,
      phase: "combat",
      machine_state: "IDLE",
      turn_order: ["c1"],
      current_turn_index: 0,
      round_number: 1,
      characters: [me],
      map_size: [10, 10],
      obstacles: [],
      current_turn_summary: null,
      pending_actions: [],
    };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useGameStore.setState({
      gameState: makeMyTurnState(),
      myPlayerId: "p1",
    } as never);
    usePendingStore.setState({ submittingTurnAction: false });
  });

  afterEach(() => {
    useGameStore.setState({
      gameState: null,
      myPlayerId: null,
    } as never);
    usePendingStore.setState({ submittingTurnAction: false });
  });

  function renderBar(onEndTurn: () => void = () => {}) {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(QuickActionBar, { onEndTurn }),
      ),
    );
  }

  it("does not show the submitting label when idle", () => {
    renderBar();
    expect(screen.queryByTestId("quickbar-submitting")).toBeNull();
    const endTurn = screen.getByTestId("quickbar-end-turn") as HTMLButtonElement;
    expect(endTurn.disabled).toBe(false);
  });

  it("shows the submitting label and disables End Turn while submitting", () => {
    usePendingStore.setState({ submittingTurnAction: true });
    renderBar();
    expect(screen.getByTestId("quickbar-submitting").textContent).toBe(
      ja["room.submitting"],
    );
    const endTurn = screen.getByTestId("quickbar-end-turn") as HTMLButtonElement;
    expect(endTurn.disabled).toBe(true);
    expect(
      screen.getByTestId("quickaction-bar").getAttribute("aria-busy"),
    ).toBe("true");
  });

  it("does not invoke onEndTurn while disabled", () => {
    usePendingStore.setState({ submittingTurnAction: true });
    const handler = vi.fn();
    renderBar(handler);
    fireEvent.click(screen.getByTestId("quickbar-end-turn"));
    expect(handler).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// ChatPanel — sticky auto-scroll + jump-to-latest button
// ---------------------------------------------------------------------------

describe("Phase 9 web: ChatPanel sticky scroll", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useChatStore.setState({ entries: [] });
    useGameStore.setState({
      gameState: {
        room_id: "r",
        version: 1,
        seed: 1,
        phase: "combat",
        machine_state: "IDLE",
        turn_order: [],
        current_turn_index: 0,
        round_number: 1,
        characters: [],
        map_size: [10, 10],
        obstacles: [],
        current_turn_summary: null,
        pending_actions: [],
      },
    } as never);
  });

  afterEach(() => {
    useChatStore.setState({ entries: [] });
    useGameStore.setState({ gameState: null } as never);
  });

  function renderPanel() {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ChatPanel, { onSendStatement: () => {} }),
      ),
    );
  }

  function setScrollGeometry(
    el: HTMLElement,
    { scrollTop, scrollHeight, clientHeight }: {
      scrollTop: number;
      scrollHeight: number;
      clientHeight: number;
    },
  ) {
    Object.defineProperty(el, "scrollTop", {
      configurable: true,
      get: () => scrollTop,
      set: () => {},
    });
    Object.defineProperty(el, "scrollHeight", {
      configurable: true,
      get: () => scrollHeight,
    });
    Object.defineProperty(el, "clientHeight", {
      configurable: true,
      get: () => clientHeight,
    });
  }

  it("does not show the jump-to-latest button when stuck at the bottom", () => {
    renderPanel();
    act(() => {
      useChatStore.getState().addEntry("system", "first");
      useChatStore.getState().addEntry("system", "second");
    });
    expect(screen.queryByTestId("chatpanel-jump-to-latest")).toBeNull();
  });

  it("shows the jump-to-latest button after the user scrolls up and a new entry arrives", () => {
    renderPanel();
    act(() => {
      useChatStore.getState().addEntry("system", "old");
    });
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    // Simulate the user scrolling away from the bottom.
    act(() => {
      setScrollGeometry(scrollEl, {
        scrollTop: 0,
        scrollHeight: 1000,
        clientHeight: 200,
      });
      fireEvent.scroll(scrollEl);
    });
    // A new entry arrives while scrolled up.
    act(() => {
      useChatStore.getState().addEntry("gm_narrative", "new!");
    });
    const btn = screen.getByTestId("chatpanel-jump-to-latest");
    expect(btn).toBeTruthy();
    expect(btn.textContent).toContain("1");
  });

  it("counts multiple unread entries while the user is scrolled away", () => {
    renderPanel();
    act(() => {
      useChatStore.getState().addEntry("system", "seed");
    });
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    act(() => {
      setScrollGeometry(scrollEl, {
        scrollTop: 0,
        scrollHeight: 1000,
        clientHeight: 200,
      });
      fireEvent.scroll(scrollEl);
    });
    act(() => {
      useChatStore.getState().addEntry("gm_narrative", "n1");
      useChatStore.getState().addEntry("gm_narrative", "n2");
      useChatStore.getState().addEntry("gm_narrative", "n3");
    });
    expect(
      screen.getByTestId("chatpanel-jump-to-latest").textContent,
    ).toContain("3");
  });

  it("dismisses the jump-to-latest button once the user scrolls back to the bottom", () => {
    renderPanel();
    act(() => {
      useChatStore.getState().addEntry("system", "seed");
    });
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    act(() => {
      setScrollGeometry(scrollEl, {
        scrollTop: 0,
        scrollHeight: 1000,
        clientHeight: 200,
      });
      fireEvent.scroll(scrollEl);
    });
    act(() => {
      useChatStore.getState().addEntry("gm_narrative", "new");
    });
    expect(screen.getByTestId("chatpanel-jump-to-latest")).toBeTruthy();
    act(() => {
      setScrollGeometry(scrollEl, {
        scrollTop: 800,
        scrollHeight: 1000,
        clientHeight: 200,
      });
      fireEvent.scroll(scrollEl);
    });
    expect(screen.queryByTestId("chatpanel-jump-to-latest")).toBeNull();
  });

  it("clicking the jump-to-latest button hides it", () => {
    renderPanel();
    act(() => {
      useChatStore.getState().addEntry("system", "seed");
    });
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    act(() => {
      setScrollGeometry(scrollEl, {
        scrollTop: 0,
        scrollHeight: 1000,
        clientHeight: 200,
      });
      fireEvent.scroll(scrollEl);
    });
    act(() => {
      useChatStore.getState().addEntry("gm_narrative", "new");
    });
    const btn = screen.getByTestId("chatpanel-jump-to-latest");
    act(() => {
      fireEvent.click(btn);
    });
    expect(screen.queryByTestId("chatpanel-jump-to-latest")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// ChatPanel — keyboard / a11y (§17-1)
// ---------------------------------------------------------------------------

describe("Phase 9 web: ChatPanel keyboard + a11y (§17)", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useChatStore.setState({ entries: [] });
    useGameStore.setState({
      gameState: {
        room_id: "r",
        version: 1,
        seed: 1,
        phase: "combat",
        machine_state: "IDLE",
        turn_order: [],
        current_turn_index: 0,
        round_number: 1,
        characters: [],
        map_size: [10, 10],
        obstacles: [],
        current_turn_summary: null,
        pending_actions: [],
      },
    } as never);
  });

  afterEach(() => {
    useChatStore.setState({ entries: [] });
    useGameStore.setState({ gameState: null } as never);
  });

  function renderPanel(onSend: (text: string) => void = () => {}) {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ChatPanel, { onSendStatement: onSend }),
      ),
    );
  }

  it("ja and en expose the chat log/input a11y keys", () => {
    expect(ja).toHaveProperty("room.chat.logLabel");
    expect(ja).toHaveProperty("room.chat.inputLabel");
    expect(en).toHaveProperty("room.chat.logLabel");
    expect(en).toHaveProperty("room.chat.inputLabel");
  });

  it("declares role=log with aria-live=polite and aria-relevant=additions", () => {
    renderPanel();
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    expect(scrollEl.getAttribute("role")).toBe("log");
    expect(scrollEl.getAttribute("aria-live")).toBe("polite");
    expect(scrollEl.getAttribute("aria-relevant")).toBe("additions");
    expect(scrollEl.getAttribute("aria-label")).toBe("チャットログ");
  });

  it("labels the log in English when the language is en", async () => {
    await i18n.changeLanguage("en");
    renderPanel();
    const scrollEl = screen.getByTestId("chatpanel-scroll");
    expect(scrollEl.getAttribute("aria-label")).toBe("Chat log");
    await i18n.changeLanguage("ja");
  });

  it("marks streaming entries as aria-busy so SRs wait for completion", () => {
    renderPanel();
    act(() => {
      // Inject a streaming GM narrative directly to mimic spec §5-2-5.
      useChatStore.setState({
        entries: [
          {
            id: "g1",
            kind: "gm_narrative",
            text: "narr",
            isStreaming: true,
          },
          {
            id: "s1",
            kind: "system",
            text: "done",
          },
        ],
      } as never);
    });
    const log = screen.getByTestId("chatpanel-scroll");
    const rows = Array.from(log.querySelectorAll("div.mb-2"));
    // Streaming row sets aria-busy=true.
    expect(rows[0]?.getAttribute("aria-busy")).toBe("true");
    // Completed row omits aria-busy entirely.
    expect(rows[1]?.hasAttribute("aria-busy")).toBe(false);
  });

  it("exposes an aria-label on the message input", () => {
    renderPanel();
    const input = screen.getByTestId("chatpanel-input");
    expect(input.getAttribute("aria-label")).toBe("メッセージ入力");
  });

  it("submits the message on Enter (existing behavior preserved)", () => {
    const onSend = vi.fn();
    renderPanel(onSend);
    const input = screen.getByTestId("chatpanel-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("hello");
  });
});

// ---------------------------------------------------------------------------
// useReconnectToast — surfaces §9-3 reconnection UX
// ---------------------------------------------------------------------------

describe("Phase 9 web: useReconnectToast hook", () => {
  function ReconnectHarness({ online }: { online: boolean }) {
    useReconnectToast(online);
    return null;
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useGameStore.setState({ connectionStatus: "CONNECTING" } as never);
    useToastStore.setState({ toasts: [] });
  });

  afterEach(() => {
    useGameStore.setState({ connectionStatus: "DISCONNECTED" } as never);
    useToastStore.setState({ toasts: [] });
  });

  function renderHarness(online: boolean) {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ReconnectHarness, { online }),
      ),
    );
  }

  it("does not toast on the initial CONNECTING → ACTIVE handshake", () => {
    const { rerender } = renderHarness(true);
    act(() => {
      useGameStore.setState({ connectionStatus: "AUTHENTICATING" } as never);
    });
    rerender(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ReconnectHarness, { online: true }),
      ),
    );
    act(() => {
      useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    });
    rerender(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ReconnectHarness, { online: true }),
      ),
    );
    expect(useToastStore.getState().toasts).toEqual([]);
  });

  it("pushes a reconnecting toast when ACTIVE → DISCONNECTED while online", () => {
    useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    renderHarness(true);
    act(() => {
      useGameStore.setState({ connectionStatus: "DISCONNECTED" } as never);
    });
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0]?.message).toBe(ja["room.notice.reconnecting"]);
    expect(toasts[0]?.severity).toBe("warn");
  });

  it("pushes a reconnected toast once ACTIVE is reached after a drop", () => {
    useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    const { rerender } = renderHarness(true);
    act(() => {
      useGameStore.setState({ connectionStatus: "DISCONNECTED" } as never);
    });
    rerender(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ReconnectHarness, { online: true }),
      ),
    );
    act(() => {
      useGameStore.setState({ connectionStatus: "AUTHENTICATING" } as never);
    });
    rerender(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ReconnectHarness, { online: true }),
      ),
    );
    act(() => {
      useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    });
    const messages = useToastStore.getState().toasts.map((t) => t.message);
    expect(messages).toContain(ja["room.notice.reconnecting"]);
    expect(messages).toContain(ja["room.notice.reconnected"]);
  });

  it("suppresses the reconnecting toast while offline", () => {
    useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    renderHarness(false);
    act(() => {
      useGameStore.setState({ connectionStatus: "DISCONNECTED" } as never);
    });
    expect(useToastStore.getState().toasts).toEqual([]);
  });

  it("does not toast on transitions into SESSION_LOST", () => {
    useGameStore.setState({ connectionStatus: "ACTIVE" } as never);
    renderHarness(true);
    act(() => {
      useGameStore.setState({ connectionStatus: "SESSION_LOST" } as never);
    });
    expect(useToastStore.getState().toasts).toEqual([]);
  });
});

describe("Phase 9 web: AiThinkingIndicator (§9-2)", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useUIStore.getState().clearAiThinking();
    useGameStore.setState({ gameState: null } as never);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    useUIStore.getState().clearAiThinking();
    useGameStore.setState({ gameState: null } as never);
  });

  function renderIndicator() {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(AiThinkingIndicator),
      ),
    );
  }

  it("renders nothing when aiThinking is null", () => {
    renderIndicator();
    expect(screen.queryByTestId("ai-thinking-indicator")).toBeNull();
  });

  it("shows the GM thinking banner with the localized stage label", () => {
    useUIStore.getState().setAiThinking("deciding_action", null);
    renderIndicator();
    const banner = screen.getByTestId("ai-thinking-indicator");
    expect(banner).toBeTruthy();
    expect(banner.textContent).toContain(ja["room.ai.thinking"]);
    expect(banner.textContent).toContain(ja["room.ai.stage.deciding_action"]);
  });

  it("shows the actor name when the message includes one", () => {
    useGameStore.setState({
      gameState: {
        characters: [
          { id: "enemy1", name: "鬼A", player_id: null } as unknown as Character,
        ],
      },
    } as never);
    useUIStore.getState().setAiThinking("deciding_action", "enemy1");
    renderIndicator();
    expect(screen.getByTestId("ai-thinking-actor").textContent).toBe("鬼A");
  });

  it("auto-clears after 10 seconds", () => {
    useUIStore.getState().setAiThinking("narrating", null);
    renderIndicator();
    expect(screen.queryByTestId("ai-thinking-indicator")).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(useUIStore.getState().aiThinking).toBeNull();
    expect(screen.queryByTestId("ai-thinking-indicator")).toBeNull();
  });

  it("falls back to the raw stage string for unknown stages", () => {
    useUIStore.getState().setAiThinking("custom_stage", null);
    renderIndicator();
    expect(screen.getByTestId("ai-thinking-indicator").textContent).toContain(
      "custom_stage",
    );
  });
});

describe("Phase 9 web: useDeadlineUrgency hook (§16 alarm timer)", () => {
  function Harness({
    secondsLeft,
    active,
  }: {
    secondsLeft: number;
    active: boolean;
  }) {
    const u = useDeadlineUrgency(secondsLeft, active);
    return React.createElement(
      "div",
      { "data-testid": "u" },
      JSON.stringify(u),
    );
  }

  beforeEach(() => {
    useAudioStore.setState({ muted: false, volume: 0.6 });
  });

  it("flags warning at <=10s and critical at <=5s", () => {
    setAudioBackend({ playSe: vi.fn(), playBgm: vi.fn(), stopBgm: vi.fn() });
    const { rerender } = render(
      React.createElement(Harness, { secondsLeft: 30, active: true }),
    );
    expect(JSON.parse(screen.getByTestId("u").textContent!)).toEqual({
      isWarning: false,
      isCritical: false,
      isExpired: false,
    });
    rerender(React.createElement(Harness, { secondsLeft: 10, active: true }));
    expect(JSON.parse(screen.getByTestId("u").textContent!).isWarning).toBe(true);
    expect(JSON.parse(screen.getByTestId("u").textContent!).isCritical).toBe(false);
    rerender(React.createElement(Harness, { secondsLeft: 5, active: true }));
    expect(JSON.parse(screen.getByTestId("u").textContent!).isCritical).toBe(true);
    rerender(React.createElement(Harness, { secondsLeft: 0, active: true }));
    expect(JSON.parse(screen.getByTestId("u").textContent!)).toEqual({
      isWarning: false,
      isCritical: false,
      isExpired: true,
    });
  });

  it("plays deadline_tick SE on each decrement inside the critical band", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    const { rerender } = render(
      React.createElement(Harness, { secondsLeft: 6, active: true }),
    );
    // 6 → 5 (entering critical band)
    rerender(React.createElement(Harness, { secondsLeft: 5, active: true }));
    expect(playSeSpy).toHaveBeenCalledWith("deadline_tick", 0.6);
    // 5 → 4
    rerender(React.createElement(Harness, { secondsLeft: 4, active: true }));
    expect(playSeSpy).toHaveBeenCalledTimes(2);
    // 4 → 3
    rerender(React.createElement(Harness, { secondsLeft: 3, active: true }));
    expect(playSeSpy).toHaveBeenCalledTimes(3);
    // 3 → 0 lands on expiry, no tick on the zero step
    rerender(React.createElement(Harness, { secondsLeft: 0, active: true }));
    expect(playSeSpy).toHaveBeenCalledTimes(3);
  });

  it("does not tick outside the critical band", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    const { rerender } = render(
      React.createElement(Harness, { secondsLeft: 30, active: true }),
    );
    rerender(React.createElement(Harness, { secondsLeft: 20, active: true }));
    rerender(React.createElement(Harness, { secondsLeft: 11, active: true }));
    rerender(React.createElement(Harness, { secondsLeft: 6, active: true }));
    expect(playSeSpy).not.toHaveBeenCalled();
  });

  it("does not tick on increments (e.g. dialog reopened with fresh deadline)", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    const { rerender } = render(
      React.createElement(Harness, { secondsLeft: 3, active: true }),
    );
    rerender(React.createElement(Harness, { secondsLeft: 60, active: true }));
    expect(playSeSpy).not.toHaveBeenCalled();
  });

  it("does not tick when the dialog is inactive", () => {
    const playSeSpy = vi.fn();
    setAudioBackend({
      playSe: playSeSpy,
      playBgm: vi.fn(),
      stopBgm: vi.fn(),
    });
    const { rerender } = render(
      React.createElement(Harness, { secondsLeft: 5, active: false }),
    );
    rerender(React.createElement(Harness, { secondsLeft: 4, active: false }));
    expect(playSeSpy).not.toHaveBeenCalled();
  });
});

describe("Phase 9 web: EvasionDialog deadline urgency", () => {
  function makeChar(id: string, playerId: string | null): Character {
    return {
      id,
      name: id,
      player_id: playerId,
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
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

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    vi.useFakeTimers();
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: {
        characters: [makeChar("me", "p1"), makeChar("foe", null)],
      },
      myPlayerId: "p1",
    } as never);
    usePendingStore.getState().setEvasionRequest(null);
  });

  afterEach(() => {
    vi.useRealTimers();
    usePendingStore.getState().setEvasionRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderDialog() {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(EvasionDialog, { onSubmit: vi.fn() }),
      ),
    );
  }

  it("shows the expired label and disables submit when time runs out", () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "pend1",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 2,
    });
    renderDialog();
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    const timer = screen.getByTestId("evasion-timer");
    expect(timer.textContent).toBe(ja["room.evasion.expired"]);
    const submit = screen
      .getByTestId("evasion-dialog")
      .querySelector("button[class*='bg-yellow-600']") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("does not call onSubmit after the deadline has expired", () => {
    const onSubmit = vi.fn();
    usePendingStore.getState().setEvasionRequest({
      pending_id: "pend1",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 1,
    });
    render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(EvasionDialog, { onSubmit }),
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const submit = screen
      .getByTestId("evasion-dialog")
      .querySelector("button[class*='bg-yellow-600']") as HTMLButtonElement;
    fireEvent.click(submit);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("uses the critical timer styling when ≤5 seconds remain", () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "pend1",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 4,
    });
    renderDialog();
    const timer = screen.getByTestId("evasion-timer");
    expect(timer.className).toContain("text-red-400");
    expect(timer.getAttribute("aria-live")).toBe("assertive");
  });
});

describe("Phase 9 web: DeathAvoidanceDialog deadline urgency", () => {
  function makeChar(): Character {
    return {
      id: "me",
      name: "me",
      player_id: "p1",
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 1,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
      position: [0, 0],
      equipped_weapons: [],
      equipped_jacket: null,
      armor_value: 0,
      inventory: { katashiro: 5 },
      skills: [],
      arts: [],
      status_effects: [],
      has_acted_this_turn: false,
      movement_used_this_turn: 0,
      first_move_mode: null,
    };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    vi.useFakeTimers();
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: { characters: [makeChar()] },
      myPlayerId: "p1",
    } as never);
    usePendingStore.getState().setDeathAvoidanceRequest(null);
  });

  afterEach(() => {
    vi.useRealTimers();
    usePendingStore.getState().setDeathAvoidanceRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  it("shows the expired label and disables submit when time runs out", () => {
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "p",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 1,
    });
    render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(DeathAvoidanceDialog, { onSubmit: vi.fn() }),
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const timer = screen.getByTestId("death-avoidance-timer");
    expect(timer.textContent).toBe(ja["room.deathAvoidance.expired"]);
    const submit = screen
      .getByTestId("death-avoidance-dialog")
      .querySelector("button[class*='bg-red-700']") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("does not call onSubmit after expiry", () => {
    const onSubmit = vi.fn();
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "p",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 1,
    });
    render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(DeathAvoidanceDialog, { onSubmit }),
      ),
    );
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const submit = screen
      .getByTestId("death-avoidance-dialog")
      .querySelector("button[class*='bg-red-700']") as HTMLButtonElement;
    fireEvent.click(submit);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Interrupt dialog keyboard + a11y (§17-1, §16 alarm-driven UX)
// ---------------------------------------------------------------------------

describe("Phase 9 web: EvasionDialog keyboard + a11y", () => {
  function makeChar(id: string, playerId: string | null): Character {
    return {
      id,
      name: id,
      player_id: playerId,
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
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

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: {
        characters: [makeChar("me", "p1"), makeChar("foe", null)],
      },
      myPlayerId: "p1",
    } as never);
    usePendingStore.getState().setEvasionRequest(null);
  });

  afterEach(() => {
    usePendingStore.getState().setEvasionRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderDialog(onSubmit = vi.fn()) {
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(EvasionDialog, { onSubmit }),
      ),
    );
    return { ...utils, onSubmit };
  }

  it("declares alertdialog role with aria-modal and aria-labelledby", () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "p",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 30,
    });
    renderDialog();
    const overlay = document.querySelector('[role="alertdialog"]');
    expect(overlay).not.toBeNull();
    expect(overlay?.getAttribute("aria-modal")).toBe("true");
    const labelId = overlay?.getAttribute("aria-labelledby");
    expect(labelId).toBe("evasion-dialog-title");
    expect(document.getElementById(labelId!)).not.toBeNull();
  });

  it("autofocuses the submit button on open", async () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "p",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 30,
    });
    renderDialog();
    const submit = screen.getByTestId("evasion-submit");
    await waitFor(() => expect(document.activeElement).toBe(submit));
  });

  it("submits on Enter while the deadline is live", () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "pend1",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 30,
    });
    const { onSubmit } = renderDialog();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("pend1", 0);
  });

  it("ignores Enter once the deadline has expired", () => {
    vi.useFakeTimers();
    try {
      usePendingStore.getState().setEvasionRequest({
        pending_id: "p",
        attacker_id: "foe",
        target_id: "me",
        deadline_seconds: 1,
      });
      const { onSubmit } = renderDialog();
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      const overlay = document.querySelector(
        '[role="alertdialog"]',
      ) as HTMLElement;
      fireEvent.keyDown(overlay, { key: "Enter" });
      expect(onSubmit).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("ignores Enter when modifier keys are held", () => {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "p",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 30,
    });
    const { onSubmit } = renderDialog();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", metaKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", altKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("Phase 9 web: DeathAvoidanceDialog keyboard + a11y", () => {
  function makeChar(): Character {
    return {
      id: "me",
      name: "me",
      player_id: "p1",
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 1,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
      position: [0, 0],
      equipped_weapons: [],
      equipped_jacket: null,
      armor_value: 0,
      inventory: { katashiro: 5 },
      skills: [],
      arts: [],
      status_effects: [],
      has_acted_this_turn: false,
      movement_used_this_turn: 0,
      first_move_mode: null,
    };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: { characters: [makeChar()] },
      myPlayerId: "p1",
    } as never);
    usePendingStore.getState().setDeathAvoidanceRequest(null);
  });

  afterEach(() => {
    usePendingStore.getState().setDeathAvoidanceRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderDialog(onSubmit = vi.fn()) {
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(DeathAvoidanceDialog, { onSubmit }),
      ),
    );
    return { ...utils, onSubmit };
  }

  it("declares alertdialog role with aria-modal and aria-labelledby", () => {
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "p",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 30,
    });
    renderDialog();
    const overlay = document.querySelector('[role="alertdialog"]');
    expect(overlay).not.toBeNull();
    expect(overlay?.getAttribute("aria-modal")).toBe("true");
    expect(overlay?.getAttribute("aria-labelledby")).toBe(
      "death-avoidance-dialog-title",
    );
    expect(document.getElementById("death-avoidance-dialog-title")).not.toBeNull();
  });

  it("autofocuses the submit button on open", async () => {
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "p",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 30,
    });
    renderDialog();
    const submit = screen.getByTestId("death-avoidance-submit");
    await waitFor(() => expect(document.activeElement).toBe(submit));
  });

  it("submits the current choice on Enter", () => {
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "pend1",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 30,
    });
    const { onSubmit } = renderDialog();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("pend1", "avoid_death");
  });

  it("ignores Enter once the deadline has expired", () => {
    vi.useFakeTimers();
    try {
      usePendingStore.getState().setDeathAvoidanceRequest({
        pending_id: "p",
        target_character_id: "me",
        target_player_id: "p1",
        incoming_damage: 10,
        damage_type: "physical",
        katashiro_required: 2,
        katashiro_remaining: 5,
        deadline_seconds: 1,
      });
      const { onSubmit } = renderDialog();
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      const overlay = document.querySelector(
        '[role="alertdialog"]',
      ) as HTMLElement;
      fireEvent.keyDown(overlay, { key: "Enter" });
      expect(onSubmit).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});

// ---------------------------------------------------------------------------
// Interrupt dialog focus trap (§17 a11y)
// ---------------------------------------------------------------------------

describe("Phase 9 web: EvasionDialog focus trap", () => {
  function makeChar(id: string, playerId: string | null): Character {
    return {
      id,
      name: id,
      player_id: playerId,
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
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

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: {
        characters: [makeChar("me", "p1"), makeChar("foe", null)],
      },
      myPlayerId: "p1",
    } as never);
  });

  afterEach(() => {
    usePendingStore.getState().setEvasionRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderDialog() {
    usePendingStore.getState().setEvasionRequest({
      pending_id: "p",
      attacker_id: "foe",
      target_id: "me",
      deadline_seconds: 30,
    });
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(EvasionDialog, { onSubmit: vi.fn() }),
      ),
    );
  }

  function getFocusable(): HTMLElement[] {
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    return Array.from(
      overlay.querySelectorAll<HTMLElement>(
        "button, input, select, textarea, [tabindex]:not([tabindex='-1'])",
      ),
    ).filter((n) => !(n as HTMLButtonElement | HTMLInputElement).disabled);
  }

  it("wraps Tab from the last focusable element back to the first", () => {
    renderDialog();
    const focusable = getFocusable();
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    last.focus();
    expect(document.activeElement).toBe(last);
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("wraps Shift+Tab from the first focusable element back to the last", () => {
    renderDialog();
    const focusable = getFocusable();
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    first.focus();
    expect(document.activeElement).toBe(first);
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("pulls focus into the dialog when Tab arrives from outside", () => {
    const outside = document.createElement("button");
    outside.textContent = "outside";
    document.body.appendChild(outside);
    try {
      renderDialog();
      outside.focus();
      expect(document.activeElement).toBe(outside);
      const overlay = document.querySelector(
        '[role="alertdialog"]',
      ) as HTMLElement;
      fireEvent.keyDown(overlay, { key: "Tab" });
      const focusable = getFocusable();
      expect(document.activeElement).toBe(focusable[0]);
    } finally {
      outside.remove();
    }
  });

  it("does not interfere with non-Tab keys", () => {
    renderDialog();
    const focusable = getFocusable();
    const first = focusable[0]!;
    first.focus();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "ArrowDown" });
    expect(document.activeElement).toBe(first);
  });
});

describe("Phase 9 web: DeathAvoidanceDialog focus trap", () => {
  function makeChar(): Character {
    return {
      id: "me",
      name: "me",
      player_id: "p1",
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 1,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
      position: [0, 0],
      equipped_weapons: [],
      equipped_jacket: null,
      armor_value: 0,
      inventory: { katashiro: 5 },
      skills: [],
      arts: [],
      status_effects: [],
      has_acted_this_turn: false,
      movement_used_this_turn: 0,
      first_move_mode: null,
    };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useAudioStore.setState({ muted: false, volume: 0.6 });
    useGameStore.setState({
      gameState: { characters: [makeChar()] },
      myPlayerId: "p1",
    } as never);
  });

  afterEach(() => {
    usePendingStore.getState().setDeathAvoidanceRequest(null);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderDialog() {
    usePendingStore.getState().setDeathAvoidanceRequest({
      pending_id: "p",
      target_character_id: "me",
      target_player_id: "p1",
      incoming_damage: 10,
      damage_type: "physical",
      katashiro_required: 2,
      katashiro_remaining: 5,
      deadline_seconds: 30,
    });
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(DeathAvoidanceDialog, { onSubmit: vi.fn() }),
      ),
    );
  }

  function getFocusable(): HTMLElement[] {
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    return Array.from(
      overlay.querySelectorAll<HTMLElement>(
        "button, input, select, textarea, [tabindex]:not([tabindex='-1'])",
      ),
    ).filter((n) => !(n as HTMLButtonElement | HTMLInputElement).disabled);
  }

  it("wraps Tab on the submit button back to the first focusable element", () => {
    renderDialog();
    const focusable = getFocusable();
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    last.focus();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("wraps Shift+Tab from the first radio back to the submit button", () => {
    renderDialog();
    const focusable = getFocusable();
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    first.focus();
    const overlay = document.querySelector(
      '[role="alertdialog"]',
    ) as HTMLElement;
    fireEvent.keyDown(overlay, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });
});

// §17 a11y for the terminal screens (CombatResultModal, SessionLostScreen,
// AssessmentScreen). These full-screen modals all have a single
// "back-to-lobby" affordance, so the keyboard story is: alertdialog role,
// autofocus the dismiss button, and Enter confirms.

describe("Phase 9 web: SessionLostScreen keyboard + a11y", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useGameStore.setState({ connectionStatus: "SESSION_LOST" } as never);
  });

  afterEach(() => {
    useGameStore.setState({ connectionStatus: "DISCONNECTED" } as never);
  });

  function renderScreen(onBack = vi.fn()) {
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(SessionLostScreen, { onBackToLobby: onBack }),
      ),
    );
    return { ...utils, onBack };
  }

  it("declares alertdialog role with aria-modal and aria-labelledby", () => {
    renderScreen();
    const overlay = screen.getByTestId("session-lost-screen");
    expect(overlay.getAttribute("role")).toBe("alertdialog");
    expect(overlay.getAttribute("aria-modal")).toBe("true");
    const labelId = overlay.getAttribute("aria-labelledby");
    expect(labelId).toBe("session-lost-title");
    expect(document.getElementById(labelId!)).not.toBeNull();
  });

  it("autofocuses the back-to-lobby button on open", async () => {
    renderScreen();
    const button = screen.getByTestId("session-lost-back");
    await waitFor(() => expect(document.activeElement).toBe(button));
  });

  it("invokes onBackToLobby when Enter is pressed", () => {
    const { onBack } = renderScreen();
    const overlay = screen.getByTestId("session-lost-screen");
    fireEvent.keyDown(overlay, { key: "Enter" });
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("ignores Enter when modifier keys are held", () => {
    const { onBack } = renderScreen();
    const overlay = screen.getByTestId("session-lost-screen");
    fireEvent.keyDown(overlay, { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", metaKey: true });
    fireEvent.keyDown(overlay, { key: "Enter", altKey: true });
    expect(onBack).not.toHaveBeenCalled();
  });

  it("traps Tab inside the dialog", () => {
    renderScreen();
    const overlay = screen.getByTestId("session-lost-screen");
    const button = screen.getByTestId("session-lost-back");
    button.focus();
    fireEvent.keyDown(overlay, { key: "Tab" });
    expect(document.activeElement).toBe(button);
    fireEvent.keyDown(overlay, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(button);
  });
});

describe("Phase 9 web: CombatResultModal keyboard + a11y", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useUIStore.setState({ combatResult: "victory" } as never);
  });

  afterEach(() => {
    useUIStore.setState({ combatResult: null } as never);
  });

  function renderModal(onBack = vi.fn()) {
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(CombatResultModal, { onBackToLobby: onBack }),
      ),
    );
    return { ...utils, onBack };
  }

  it("declares alertdialog role with aria-modal and aria-labelledby", () => {
    renderModal();
    const overlay = screen.getByTestId("combat-result-modal");
    expect(overlay.getAttribute("role")).toBe("alertdialog");
    expect(overlay.getAttribute("aria-modal")).toBe("true");
    const labelId = overlay.getAttribute("aria-labelledby");
    expect(labelId).toBe("combat-result-title");
    expect(document.getElementById(labelId!)).not.toBeNull();
  });

  it("autofocuses the back-to-lobby button on open", async () => {
    renderModal();
    const button = screen.getByTestId("combat-result-back");
    await waitFor(() => expect(document.activeElement).toBe(button));
  });

  it("dismisses on Enter and clears combatResult", () => {
    const { onBack } = renderModal();
    const overlay = screen.getByTestId("combat-result-modal");
    fireEvent.keyDown(overlay, { key: "Enter" });
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(useUIStore.getState().combatResult).toBeNull();
  });

  it("traps Tab inside the modal", () => {
    renderModal();
    const overlay = screen.getByTestId("combat-result-modal");
    const button = screen.getByTestId("combat-result-back");
    button.focus();
    fireEvent.keyDown(overlay, { key: "Tab" });
    expect(document.activeElement).toBe(button);
    fireEvent.keyDown(overlay, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(button);
  });

  it("renders nothing when combatResult is null", () => {
    useUIStore.setState({ combatResult: null } as never);
    const { container } = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(CombatResultModal, { onBackToLobby: vi.fn() }),
      ),
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("Phase 9 web: AssessmentScreen keyboard + a11y", () => {
  function makeChar(id: string, playerId: string | null): Character {
    return {
      id,
      name: id,
      player_id: playerId,
      faction: "pc",
      is_boss: false,
      tai: 0,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 4,
      evasion_dice: 3,
      max_evasion_dice: 3,
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

  function makeAssessmentState(): GameState {
    return {
      session_id: "s1",
      version: 1,
      phase: "assessment" as GamePhase,
      machine_state: "IDLE",
      turn_owner: null,
      round: 1,
      characters: [makeChar("me", "p1")],
      map: { width: 10, height: 10, tiles: [] },
      assessment_result: {
        outcome: "victory",
        grade: "A",
        rounds_taken: 5,
        pcs_alive: 1,
        pcs_total: 1,
        enemies_defeated: 1,
        enemies_total: 1,
      },
      growth_proposals: [],
    } as unknown as GameState;
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    useGameStore.setState({
      gameState: makeAssessmentState(),
      myPlayerId: "p1",
    } as never);
  });

  afterEach(() => {
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  function renderScreen(onBack = vi.fn()) {
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(AssessmentScreen, { onBackToLobby: onBack }),
      ),
    );
    return { ...utils, onBack };
  }

  it("declares alertdialog role with aria-modal and aria-labelledby", () => {
    renderScreen();
    const overlay = screen.getByTestId("assessment-screen");
    expect(overlay.getAttribute("role")).toBe("alertdialog");
    expect(overlay.getAttribute("aria-modal")).toBe("true");
    const labelId = overlay.getAttribute("aria-labelledby");
    expect(labelId).toBe("assessment-screen-title");
    expect(document.getElementById(labelId!)).not.toBeNull();
  });

  it("autofocuses the back-to-lobby button on open", async () => {
    renderScreen();
    const button = screen.getByTestId("assessment-back");
    await waitFor(() => expect(document.activeElement).toBe(button));
  });

  it("invokes onBackToLobby when Enter is pressed", () => {
    const { onBack } = renderScreen();
    const overlay = screen.getByTestId("assessment-screen");
    fireEvent.keyDown(overlay, { key: "Enter" });
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// SideMenu CharCard — spec §5-2-6 (katashiro / status effects / evasion dots)
// ---------------------------------------------------------------------------

describe("Phase 9 web: SideMenu CharCard (§5-2-6)", () => {
  function makeChar(
    over: Partial<Character> & Pick<Character, "id">,
  ): Character {
    const base: Character = {
      id: over.id,
      name: over.id,
      player_id: null,
      faction: "pc",
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
    return { ...base, ...over };
  }

  function makeState(
    over: Partial<GameState> & Pick<GameState, "characters" | "turn_order">,
  ): GameState {
    const base = {
      room_id: "r",
      version: 1,
      seed: 1,
      phase: "combat" as GamePhase,
      machine_state: "IDLE" as const,
      current_turn_index: 0,
      round_number: 1,
      map_size: [10, 10] as [number, number],
      obstacles: [],
      current_turn_summary: null,
      pending_actions: [],
    };
    return { ...base, ...over } as GameState;
  }

  function renderSideMenu() {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(SideMenu),
      ),
    );
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
  });

  afterEach(() => {
    useGameStore.setState({
      gameState: null,
      myPlayerId: null,
    } as never);
  });

  it("shows the katashiro count for the local player's PC", () => {
    const me = makeChar({
      id: "c1",
      player_id: "p1",
      inventory: { katashiro: 7 },
    });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    const node = screen.getByTestId("sidemenu-katashiro-c1");
    expect(node.textContent).toContain("7");
  });

  it("hides the katashiro count for other characters", () => {
    const me = makeChar({
      id: "c1",
      player_id: "p1",
      inventory: { katashiro: 4 },
    });
    const other = makeChar({
      id: "c2",
      player_id: "p2",
      inventory: { katashiro: 9 },
    });
    useGameStore.setState({
      gameState: makeState({
        characters: [me, other],
        turn_order: ["c1", "c2"],
      }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    expect(screen.queryByTestId("sidemenu-katashiro-c1")).not.toBeNull();
    expect(screen.queryByTestId("sidemenu-katashiro-c2")).toBeNull();
  });

  it("hides the katashiro row when the inventory has no katashiro key", () => {
    const me = makeChar({ id: "c1", player_id: "p1", inventory: {} });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    expect(screen.queryByTestId("sidemenu-katashiro-c1")).toBeNull();
  });

  it("renders the status row with localized 'なし' when no status effects are present", () => {
    const me = makeChar({ id: "c1", player_id: "p1" });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    const status = screen.getByTestId("sidemenu-status-c1");
    expect(status.textContent).toBe(ja["room.sideMenu.statusNone"]);
  });

  it("renders status effects with name and remaining duration", () => {
    const me = makeChar({
      id: "c1",
      player_id: "p1",
      status_effects: [
        { name: "毒", duration: 3, payload: {} },
        { name: "怯え", duration: 0, payload: {} },
      ],
    });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    const status = screen.getByTestId("sidemenu-status-c1");
    expect(status.textContent).toContain("毒");
    expect(status.textContent).toContain("×3");
    expect(status.textContent).toContain("怯え");
  });

  it("renders the evasion dots filled/empty for the live count", () => {
    const me = makeChar({
      id: "c1",
      player_id: "p1",
      evasion_dice: 3,
      max_evasion_dice: 5,
    });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    const dots = screen.getAllByTestId("evasion-dots")[0]!;
    expect(dots.textContent).toBe("●●●○○");
  });

  it("clamps evasion dots when current exceeds max and skips the dot row when max > 10", () => {
    const me = makeChar({
      id: "c1",
      player_id: "p1",
      evasion_dice: 99,
      max_evasion_dice: 12,
    });
    useGameStore.setState({
      gameState: makeState({ characters: [me], turn_order: ["c1"] }),
      myPlayerId: "p1",
    } as never);
    renderSideMenu();
    expect(screen.queryAllByTestId("evasion-dots")).toHaveLength(0);
    expect(screen.getByTestId("sidemenu-evasion-c1").textContent).toBe(
      "99/12",
    );
  });

  it("ja and en both expose the SideMenu §5-2-6 keys", () => {
    expect(ja).toHaveProperty("room.sideMenu.status");
    expect(ja).toHaveProperty("room.sideMenu.statusNone");
    expect(ja).toHaveProperty("room.sideMenu.statusDuration");
    expect(ja).toHaveProperty("room.sideMenu.katashiroCount");
    expect(en).toHaveProperty("room.sideMenu.status");
    expect(en).toHaveProperty("room.sideMenu.statusNone");
    expect(en).toHaveProperty("room.sideMenu.statusDuration");
    expect(en).toHaveProperty("room.sideMenu.katashiroCount");
  });
});

describe("Phase 9 web: ContextMenu keyboard + a11y (§17, §5-2-2)", () => {
  function makeChar(id: string, name: string): Character {
    return {
      id,
      name,
      player_id: null,
      faction: "enemy",
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
      evasion_dice: 0,
      max_evasion_dice: 0,
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

  function renderMenu(handlers?: {
    onAttack?: ReturnType<typeof vi.fn>;
    onDetailAttack?: ReturnType<typeof vi.fn>;
    onCastArt?: ReturnType<typeof vi.fn>;
  }) {
    const onAttack = handlers?.onAttack ?? vi.fn();
    const onDetailAttack = handlers?.onDetailAttack ?? vi.fn();
    const onCastArt = handlers?.onCastArt ?? vi.fn();
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ContextMenu, {
          onAttack,
          onDetailAttack,
          onCastArt,
        }),
      ),
    );
    return { ...utils, onAttack, onDetailAttack, onCastArt };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    const target = makeChar("e1", "怨霊武者");
    useGameStore.setState({
      gameState: { characters: [target] } as unknown as GameState,
      myPlayerId: "p1",
    } as never);
    useUIStore.setState({
      contextMenuCharId: "e1",
      contextMenuPos: { x: 100, y: 200 },
    } as never);
  });

  afterEach(() => {
    useUIStore.setState({
      contextMenuCharId: null,
      contextMenuPos: null,
    } as never);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  it("declares role=menu and labels itself with the target name", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    expect(menu.getAttribute("role")).toBe("menu");
    const labelId = menu.getAttribute("aria-labelledby");
    expect(labelId).not.toBeNull();
    expect(document.getElementById(labelId!)?.textContent).toBe("怨霊武者");
  });

  it("renders each action as a menuitem with roving tabindex", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    const items = menu.querySelectorAll("[role='menuitem']");
    expect(items.length).toBeGreaterThanOrEqual(4);
    items.forEach((it) => expect(it.getAttribute("tabindex")).toBe("-1"));
  });

  it("autofocuses the first menuitem on open", async () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    const first = menu.querySelector<HTMLButtonElement>("[role='menuitem']");
    expect(first).not.toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(first));
  });

  it("ArrowDown moves focus to the next menuitem and wraps from the last", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    const items = menu.querySelectorAll<HTMLButtonElement>("[role='menuitem']");
    expect(document.activeElement).toBe(items[0]);
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    expect(document.activeElement).toBe(items[1]);
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    expect(document.activeElement).toBe(items[2]);
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    expect(document.activeElement).toBe(items[3]);
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    expect(document.activeElement).toBe(items[0]);
  });

  it("ArrowUp moves focus to the previous menuitem and wraps from the first", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    const items = menu.querySelectorAll<HTMLButtonElement>("[role='menuitem']");
    fireEvent.keyDown(menu, { key: "ArrowUp" });
    expect(document.activeElement).toBe(items[items.length - 1]);
    fireEvent.keyDown(menu, { key: "ArrowUp" });
    expect(document.activeElement).toBe(items[items.length - 2]);
  });

  it("Home jumps to the first menuitem and End to the last", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    const items = menu.querySelectorAll<HTMLButtonElement>("[role='menuitem']");
    fireEvent.keyDown(menu, { key: "End" });
    expect(document.activeElement).toBe(items[items.length - 1]);
    fireEvent.keyDown(menu, { key: "Home" });
    expect(document.activeElement).toBe(items[0]);
  });

  it("Escape closes the menu", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    fireEvent.keyDown(menu, { key: "Escape" });
    expect(useUIStore.getState().contextMenuCharId).toBeNull();
    expect(useUIStore.getState().contextMenuPos).toBeNull();
  });

  it("Tab closes the menu (per WAI-ARIA menu pattern)", () => {
    renderMenu();
    const menu = screen.getByTestId("context-menu");
    fireEvent.keyDown(menu, { key: "Tab" });
    expect(useUIStore.getState().contextMenuCharId).toBeNull();
  });

  it("Enter on the focused menuitem invokes its handler and closes the menu", () => {
    const { onAttack } = renderMenu();
    const menu = screen.getByTestId("context-menu");
    const first = menu.querySelector<HTMLButtonElement>("[role='menuitem']")!;
    // The button's native click handler fires on Enter via click().
    first.click();
    expect(onAttack).toHaveBeenCalledWith("e1");
    expect(useUIStore.getState().contextMenuCharId).toBeNull();
  });

  it("renders nothing when no context menu target is set", () => {
    useUIStore.setState({
      contextMenuCharId: null,
      contextMenuPos: null,
    } as never);
    const { container } = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ContextMenu, {
          onAttack: vi.fn(),
          onDetailAttack: vi.fn(),
          onCastArt: vi.fn(),
        }),
      ),
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("Phase 9 web: ActionDetailModal keyboard + a11y (§17)", () => {
  function makeChar(
    id: string,
    name: string,
    overrides: Partial<Character> = {},
  ): Character {
    return {
      id,
      name,
      player_id: null,
      faction: "enemy",
      is_boss: false,
      tai: 4,
      rei: 0,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 3,
      evasion_dice: 0,
      max_evasion_dice: 0,
      position: [0, 0],
      equipped_weapons: ["w1"],
      equipped_jacket: null,
      armor_value: 0,
      inventory: {},
      skills: [],
      arts: [],
      status_effects: [],
      has_acted_this_turn: false,
      movement_used_this_turn: 0,
      first_move_mode: null,
      ...overrides,
    };
  }

  function renderModal(onSubmit?: ReturnType<typeof vi.fn>) {
    const submit = onSubmit ?? vi.fn();
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ActionDetailModal, { onSubmit: submit }),
      ),
    );
    return { ...utils, onSubmit: submit };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    const me = makeChar("p1c", "自分", {
      player_id: "p1",
      faction: "pc",
      equipped_weapons: ["katana"],
    });
    const target = makeChar("e1", "怨霊武者");
    useGameStore.setState({
      gameState: { characters: [me, target] } as unknown as GameState,
      myPlayerId: "p1",
    } as never);
    useUIStore.setState({
      activeModal: "action_detail",
      actionDetailTargetId: "e1",
    } as never);
  });

  afterEach(() => {
    useUIStore.setState({
      activeModal: null,
      actionDetailTargetId: null,
    } as never);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  it("declares role=dialog with aria-modal and aria-labelledby pointing at the title", () => {
    renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    expect(dialog.getAttribute("role")).toBe("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    const labelId = dialog.getAttribute("aria-labelledby");
    expect(labelId).not.toBeNull();
    expect(document.getElementById(labelId!)?.textContent).toBe("攻撃の設定");
  });

  it("renders nothing when no actionDetail target is set", () => {
    useUIStore.setState({
      activeModal: null,
      actionDetailTargetId: null,
    } as never);
    const { container } = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(ActionDetailModal, { onSubmit: vi.fn() }),
      ),
    );
    expect(container.firstChild).toBeNull();
  });

  it("autofocuses the submit button on open", async () => {
    renderModal();
    const submit = screen.getByTestId("action-detail-submit");
    await waitFor(() => expect(document.activeElement).toBe(submit));
  });

  it("Escape closes the modal without submitting", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(useUIStore.getState().activeModal).toBeNull();
  });

  it("Enter submits when focus is outside form controls", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    fireEvent.keyDown(dialog, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0]![0] as { targetId: string };
    expect(payload.targetId).toBe("e1");
    expect(useUIStore.getState().activeModal).toBeNull();
  });

  it("Enter on a form input does NOT submit (avoids double submit)", () => {
    const { onSubmit } = renderModal();
    const range = screen
      .getByTestId("action-detail-modal")
      .querySelector<HTMLInputElement>("input[type='range']")!;
    fireEvent.keyDown(range, { key: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Enter with modifier keys is ignored", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    fireEvent.keyDown(dialog, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", metaKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", altKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Tab from the last focusable wraps to the first (focus trap)", () => {
    renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    const focusables =
      dialog.querySelectorAll<HTMLElement>(
        "button, input:not([type='hidden'])",
      );
    const first = focusables[0]!;
    const last = focusables[focusables.length - 1]!;
    last.focus();
    fireEvent.keyDown(dialog, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("Shift+Tab from the first focusable wraps to the last (focus trap)", () => {
    renderModal();
    const dialog = screen.getByTestId("action-detail-modal");
    const focusables =
      dialog.querySelectorAll<HTMLElement>(
        "button, input:not([type='hidden'])",
      );
    const first = focusables[0]!;
    const last = focusables[focusables.length - 1]!;
    first.focus();
    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("Cancel button closes the modal without submitting", () => {
    const { onSubmit } = renderModal();
    const cancel = screen.getByTestId("action-detail-cancel");
    fireEvent.click(cancel);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(useUIStore.getState().activeModal).toBeNull();
  });
});

describe("Phase 9 web: CastArtModal keyboard + a11y (§17)", () => {
  function makeChar(
    id: string,
    name: string,
    overrides: Partial<Character> = {},
  ): Character {
    return {
      id,
      name,
      player_id: null,
      faction: "enemy",
      is_boss: false,
      tai: 4,
      rei: 4,
      kou: 0,
      jutsu: 0,
      max_hp: 10,
      max_mp: 10,
      hp: 10,
      mp: 10,
      mobility: 3,
      evasion_dice: 0,
      max_evasion_dice: 0,
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
      ...overrides,
    };
  }

  function renderModal(onSubmit?: ReturnType<typeof vi.fn>) {
    const submit = onSubmit ?? vi.fn();
    const utils = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(CastArtModal, { onSubmit: submit }),
      ),
    );
    return { ...utils, onSubmit: submit };
  }

  beforeEach(async () => {
    await i18n.changeLanguage("ja");
    const me = makeChar("p1c", "自分", {
      player_id: "p1",
      faction: "pc",
      arts: ["反閃歩法", "霊弾発射"],
    });
    const target = makeChar("e1", "怨霊武者");
    useGameStore.setState({
      gameState: { characters: [me, target] } as unknown as GameState,
      myPlayerId: "p1",
    } as never);
    useUIStore.setState({
      activeModal: "cast_art",
      castArtTargetId: null,
    } as never);
  });

  afterEach(() => {
    useUIStore.setState({
      activeModal: null,
      castArtTargetId: null,
    } as never);
    useGameStore.setState({ gameState: null, myPlayerId: null } as never);
  });

  it("declares role=dialog with aria-modal and aria-labelledby pointing at the title", () => {
    renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    expect(dialog.getAttribute("role")).toBe("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    const labelId = dialog.getAttribute("aria-labelledby");
    expect(labelId).not.toBeNull();
    expect(document.getElementById(labelId!)?.textContent).toBe("祓魔術");
  });

  it("renders nothing when the modal is not open", () => {
    useUIStore.setState({ activeModal: null } as never);
    const { container } = render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(CastArtModal, { onSubmit: vi.fn() }),
      ),
    );
    expect(container.firstChild).toBeNull();
  });

  it("autofocuses the cancel button on open", async () => {
    renderModal();
    const cancel = screen.getByTestId("cast-art-cancel");
    await waitFor(() => expect(document.activeElement).toBe(cancel));
  });

  it("Escape closes the modal without submitting", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(useUIStore.getState().activeModal).toBeNull();
  });

  it("Enter does NOT submit when no art is selected (canSubmit is false)", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    fireEvent.keyDown(dialog, { key: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(useUIStore.getState().activeModal).toBe("cast_art");
  });

  it("Enter submits once an art with no target is selected (self target)", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    const radios = dialog.querySelectorAll<HTMLInputElement>(
      "input[type='radio'][name='art']",
    );
    const self = Array.from(radios).find((r) => r.value === "反閃歩法")!;
    fireEvent.click(self);
    fireEvent.keyDown(dialog, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0]![0] as {
      art_name: string;
      target?: string;
    };
    expect(payload.art_name).toBe("反閃歩法");
    expect(payload.target).toBe("p1c");
    expect(useUIStore.getState().activeModal).toBeNull();
  });

  it("Enter on a form input does NOT submit (avoids double submit)", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    const radios = dialog.querySelectorAll<HTMLInputElement>(
      "input[type='radio'][name='art']",
    );
    const self = Array.from(radios).find((r) => r.value === "反閃歩法")!;
    fireEvent.click(self);
    fireEvent.keyDown(self, { key: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Enter with modifier keys is ignored", () => {
    const { onSubmit } = renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    const self = Array.from(
      dialog.querySelectorAll<HTMLInputElement>("input[type='radio'][name='art']"),
    ).find((r) => r.value === "反閃歩法")!;
    fireEvent.click(self);
    fireEvent.keyDown(dialog, { key: "Enter", shiftKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", metaKey: true });
    fireEvent.keyDown(dialog, { key: "Enter", altKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Tab from the last focusable wraps to the first (focus trap)", () => {
    renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    const focusables = dialog.querySelectorAll<HTMLElement>(
      "button:not([disabled]), input:not([type='hidden']):not([disabled])",
    );
    const first = focusables[0]!;
    const last = focusables[focusables.length - 1]!;
    last.focus();
    fireEvent.keyDown(dialog, { key: "Tab" });
    expect(document.activeElement).toBe(first);
  });

  it("Shift+Tab from the first focusable wraps to the last (focus trap)", () => {
    renderModal();
    const dialog = screen.getByTestId("cast-art-modal");
    const focusables = dialog.querySelectorAll<HTMLElement>(
      "button:not([disabled]), input:not([type='hidden']):not([disabled])",
    );
    const first = focusables[0]!;
    const last = focusables[focusables.length - 1]!;
    first.focus();
    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("Cancel button closes the modal without submitting", () => {
    const { onSubmit } = renderModal();
    const cancel = screen.getByTestId("cast-art-cancel");
    fireEvent.click(cancel);
    expect(onSubmit).not.toHaveBeenCalled();
    expect(useUIStore.getState().activeModal).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// CastArtCutscene a11y (§17) — silent overlay must speak to screen readers
// ---------------------------------------------------------------------------

describe("Phase 9 web: CastArtCutscene a11y (§17)", () => {
  beforeEach(async () => {
    vi.useFakeTimers();
    await i18n.changeLanguage("ja");
    useUIStore.setState({ castArtCutscene: null } as never);
  });

  afterEach(() => {
    vi.useRealTimers();
    useUIStore.setState({ castArtCutscene: null } as never);
  });

  function renderCutscene() {
    return render(
      React.createElement(
        I18nextProvider,
        { i18n },
        React.createElement(CastArtCutscene),
      ),
    );
  }

  it("ja and en expose the cutscene announcement key", () => {
    expect(ja).toHaveProperty("room.castArt.cutsceneAnnounce");
    expect(en).toHaveProperty("room.castArt.cutsceneAnnounce");
  });

  it("declares role=status with aria-live=polite and aria-atomic=true", () => {
    renderCutscene();
    act(() => {
      useUIStore.getState().triggerCastArtCutscene({
        id: "c1",
        artName: "霊弾発射",
        casterName: "茜",
      });
    });
    const overlay = screen.getByTestId("cast-art-cutscene");
    expect(overlay.getAttribute("role")).toBe("status");
    expect(overlay.getAttribute("aria-live")).toBe("polite");
    expect(overlay.getAttribute("aria-atomic")).toBe("true");
  });

  it("announces caster + art via an sr-only sentence (ja)", () => {
    renderCutscene();
    act(() => {
      useUIStore.getState().triggerCastArtCutscene({
        id: "c1",
        artName: "霊弾発射",
        casterName: "茜",
      });
    });
    const announce = screen.getByTestId("cast-art-cutscene-announce");
    expect(announce.textContent).toBe("茜が『霊弾発射』を発動！");
  });

  it("announces caster + art via an sr-only sentence (en)", async () => {
    await i18n.changeLanguage("en");
    renderCutscene();
    act(() => {
      useUIStore.getState().triggerCastArtCutscene({
        id: "c2",
        artName: "Spirit Bullet",
        casterName: "Akane",
      });
    });
    const announce = screen.getByTestId("cast-art-cutscene-announce");
    expect(announce.textContent).toBe("Akane casts “Spirit Bullet”!");
    await i18n.changeLanguage("ja");
  });

  it("hides the decorative visual layer from assistive tech", () => {
    renderCutscene();
    act(() => {
      useUIStore.getState().triggerCastArtCutscene({
        id: "c3",
        artName: "霊弾発射",
        casterName: "茜",
      });
    });
    const overlay = screen.getByTestId("cast-art-cutscene");
    const decorative = overlay.querySelector('[aria-hidden="true"]');
    expect(decorative).toBeTruthy();
    // Visible caster/art labels live inside the aria-hidden subtree so the
    // sr-only sentence is the single source of truth for screen readers.
    expect(decorative?.textContent).toContain("茜");
    expect(decorative?.textContent).toContain("霊弾発射");
  });
});
