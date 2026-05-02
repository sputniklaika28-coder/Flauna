import { describe, it, expect, beforeEach } from "vitest";
import { useGameStore } from "../../src/stores/gameStore";
import { useChatStore } from "../../src/stores/chatStore";
import { useUIStore } from "../../src/stores/uiStore";
import { usePendingStore } from "../../src/stores/pendingStore";
import { useDraftStore } from "../../src/stores/draftStore";
import type { GameState, EvasionPending } from "../../src/types";

const makeGameState = (overrides: Partial<GameState> = {}): GameState => ({
  room_id: "room-1",
  version: 1,
  seed: 42,
  phase: "combat",
  machine_state: "IDLE",
  turn_order: ["char-1", "char-2"],
  current_turn_index: 0,
  round_number: 1,
  characters: [],
  map_size: [10, 10],
  obstacles: [],
  current_turn_summary: null,
  pending_actions: [],
  ...overrides,
});

describe("useGameStore", () => {
  beforeEach(() => {
    useGameStore.setState({
      gameState: null,
      connectionStatus: "DISCONNECTED",
      lastSeenEventId: 0,
      myPlayerId: null,
      myToken: null,
    });
  });

  it("setGameState updates gameState", () => {
    const state = makeGameState();
    useGameStore.getState().setGameState(state);
    expect(useGameStore.getState().gameState?.room_id).toBe("room-1");
  });

  it("applyStateFull sets gameState and lastSeenEventId from version", () => {
    const state = makeGameState({ version: 5 });
    useGameStore.getState().applyStateFull(state);
    expect(useGameStore.getState().gameState?.version).toBe(5);
    expect(useGameStore.getState().lastSeenEventId).toBe(5);
  });

  it("setConnectionStatus updates status", () => {
    useGameStore.getState().setConnectionStatus("ACTIVE");
    expect(useGameStore.getState().connectionStatus).toBe("ACTIVE");
  });

  it("setAuth stores playerId and token", () => {
    useGameStore.getState().setAuth("p1", "tok123");
    expect(useGameStore.getState().myPlayerId).toBe("p1");
    expect(useGameStore.getState().myToken).toBe("tok123");
  });
});

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.getState().clear();
  });

  it("addEntry appends a message", () => {
    useChatStore.getState().addEntry("gm_narrative", "Hello!");
    const entries = useChatStore.getState().entries;
    expect(entries).toHaveLength(1);
    expect(entries[0]?.text).toBe("Hello!");
    expect(entries[0]?.kind).toBe("gm_narrative");
  });

  it("updateLastNarrative updates streaming narrative in-place", () => {
    useChatStore.getState().addEntry("gm_narrative", "start…", undefined, true);
    useChatStore.getState().updateLastNarrative("full text", false);
    const entries = useChatStore.getState().entries;
    expect(entries).toHaveLength(1);
    expect(entries[0]?.text).toBe("full text");
    expect(entries[0]?.isStreaming).toBe(false);
  });

  it("updateLastNarrative adds new entry if last is not streaming", () => {
    useChatStore.getState().addEntry("gm_narrative", "done", undefined, false);
    useChatStore.getState().updateLastNarrative("new narrative", true);
    const entries = useChatStore.getState().entries;
    expect(entries).toHaveLength(2);
  });

  it("clear empties entries", () => {
    useChatStore.getState().addEntry("system", "x");
    useChatStore.getState().clear();
    expect(useChatStore.getState().entries).toHaveLength(0);
  });
});

describe("useUIStore", () => {
  beforeEach(() => {
    useUIStore.setState({
      mapZoom: 40,
      selectedCharId: null,
      contextMenuCharId: null,
      contextMenuPos: null,
      activeModal: null,
    });
  });

  it("setMapZoom clamps to [30, 64]", () => {
    useUIStore.getState().setMapZoom(10);
    expect(useUIStore.getState().mapZoom).toBe(30);
    useUIStore.getState().setMapZoom(100);
    expect(useUIStore.getState().mapZoom).toBe(64);
    useUIStore.getState().setMapZoom(50);
    expect(useUIStore.getState().mapZoom).toBe(50);
  });

  it("openContextMenu sets char and position", () => {
    useUIStore.getState().openContextMenu("char-1", { x: 100, y: 200 });
    expect(useUIStore.getState().contextMenuCharId).toBe("char-1");
    expect(useUIStore.getState().contextMenuPos).toEqual({ x: 100, y: 200 });
  });

  it("closeContextMenu clears context menu", () => {
    useUIStore.getState().openContextMenu("char-1", { x: 10, y: 20 });
    useUIStore.getState().closeContextMenu();
    expect(useUIStore.getState().contextMenuCharId).toBeNull();
    expect(useUIStore.getState().contextMenuPos).toBeNull();
  });

  it("openModal / closeModal toggle activeModal", () => {
    useUIStore.getState().openModal("evasion");
    expect(useUIStore.getState().activeModal).toBe("evasion");
    useUIStore.getState().closeModal();
    expect(useUIStore.getState().activeModal).toBeNull();
  });
});

describe("usePendingStore", () => {
  beforeEach(() => {
    usePendingStore.setState({
      evasionRequest: null,
      submittingTurnAction: false,
    });
  });

  it("setEvasionRequest stores and clears request", () => {
    const req: EvasionPending = {
      pending_id: "p1",
      attacker_id: "a1",
      target_id: "t1",
      deadline_seconds: 60,
    };
    usePendingStore.getState().setEvasionRequest(req);
    expect(usePendingStore.getState().evasionRequest?.pending_id).toBe("p1");
    usePendingStore.getState().setEvasionRequest(null);
    expect(usePendingStore.getState().evasionRequest).toBeNull();
  });

  it("submittingTurnAction defaults to false and toggles via setter", () => {
    expect(usePendingStore.getState().submittingTurnAction).toBe(false);
    usePendingStore.getState().setSubmittingTurnAction(true);
    expect(usePendingStore.getState().submittingTurnAction).toBe(true);
    usePendingStore.getState().setSubmittingTurnAction(false);
    expect(usePendingStore.getState().submittingTurnAction).toBe(false);
  });
});

describe("useDraftStore", () => {
  beforeEach(() => {
    useDraftStore.getState().clearDraft();
  });

  it("setDraft and clearDraft work correctly", () => {
    useDraftStore.getState().setDraft({ end_turn: true });
    expect(useDraftStore.getState().draft?.end_turn).toBe(true);
    useDraftStore.getState().clearDraft();
    expect(useDraftStore.getState().draft).toBeNull();
  });
});
