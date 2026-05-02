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
import { useOnlineStatus } from "../../src/hooks/useOnlineStatus";
import { useReconnectToast } from "../../src/hooks/useReconnectToast";
import Header from "../../src/components/layout/Header";
import { useGameStore, usePendingStore, useToastStore } from "../../src/stores";
import QuickActionBar from "../../src/components/action/QuickActionBar";
import ChatPanel from "../../src/components/chat/ChatPanel";
import { useChatStore } from "../../src/stores";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
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
