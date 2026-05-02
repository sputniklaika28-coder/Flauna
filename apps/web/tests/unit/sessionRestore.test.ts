import { describe, it, expect, vi } from "vitest";
import {
  applySessionRestorePendings,
  deadlineSecondsFrom,
  type ApplyDeps,
  type SessionRestoreLike,
} from "../../src/services/sessionRestore";

function makeDeps(overrides: Partial<ApplyDeps> = {}): ApplyDeps & {
  setEvasionRequest: ReturnType<typeof vi.fn>;
  setDeathAvoidanceRequest: ReturnType<typeof vi.fn>;
  addSystemEntry: ReturnType<typeof vi.fn>;
  t: ReturnType<typeof vi.fn>;
  playSe: ReturnType<typeof vi.fn>;
} {
  return {
    myPlayerId: "p1",
    now: () => 1_700_000_000_000,
    setEvasionRequest: vi.fn(),
    setDeathAvoidanceRequest: vi.fn(),
    addSystemEntry: vi.fn(),
    t: vi.fn((key: string) => key),
    playSe: vi.fn(),
    ...overrides,
  } as ApplyDeps & {
    setEvasionRequest: ReturnType<typeof vi.fn>;
    setDeathAvoidanceRequest: ReturnType<typeof vi.fn>;
    addSystemEntry: ReturnType<typeof vi.fn>;
    t: ReturnType<typeof vi.fn>;
    playSe: ReturnType<typeof vi.fn>;
  };
}

describe("deadlineSecondsFrom", () => {
  it("returns the floored remaining seconds", () => {
    const now = () => 1_700_000_000_000;
    expect(deadlineSecondsFrom("2023-11-14T22:13:30Z", now)).toBeGreaterThan(0);
  });

  it("clamps negative deltas to 0", () => {
    const now = () => 1_700_000_000_000;
    const earlier = new Date(1_700_000_000_000 - 5000).toISOString();
    expect(deadlineSecondsFrom(earlier, now)).toBe(0);
  });

  it("returns 0 for unparseable strings", () => {
    expect(deadlineSecondsFrom("not-a-date")).toBe(0);
  });
});

describe("applySessionRestorePendings", () => {
  const baseEvasion = {
    type: "evasion_request" as const,
    pending_id: "pe-1",
    target_character_id: "char-1",
    target_player_id: "p1",
    deadline_at: new Date(1_700_000_000_000 + 30_000).toISOString(),
    incoming_attacks: [{ attacker_id: "enemy-1" }],
  };
  const baseDeath = {
    type: "death_avoidance_request" as const,
    pending_id: "pd-1",
    target_character_id: "char-1",
    target_player_id: "p1",
    incoming_damage: 12,
    damage_type: "physical",
    katashiro_required: 1,
    katashiro_remaining: 2,
    deadline_at: new Date(1_700_000_000_000 + 60_000).toISOString(),
  };

  it("re-opens an evasion dialog targeting me and plays the alert SE", () => {
    const deps = makeDeps();
    const msg: SessionRestoreLike = { pending_for_you: [baseEvasion] };
    applySessionRestorePendings(msg, deps);
    expect(deps.setEvasionRequest).toHaveBeenCalledWith({
      pending_id: "pe-1",
      attacker_id: "enemy-1",
      target_id: "char-1",
      deadline_seconds: 30,
    });
    expect(deps.addSystemEntry).toHaveBeenCalledWith(
      "room.system.pendingRestoredEvasion",
    );
    expect(deps.playSe).toHaveBeenCalledWith("evade_alert");
  });

  it("re-opens a death-avoidance dialog targeting me and plays its alert SE", () => {
    const deps = makeDeps();
    const msg: SessionRestoreLike = { pending_for_you: [baseDeath] };
    applySessionRestorePendings(msg, deps);
    expect(deps.setDeathAvoidanceRequest).toHaveBeenCalledWith({
      pending_id: "pd-1",
      target_character_id: "char-1",
      target_player_id: "p1",
      incoming_damage: 12,
      damage_type: "physical",
      katashiro_required: 1,
      katashiro_remaining: 2,
      deadline_seconds: 60,
    });
    expect(deps.addSystemEntry).toHaveBeenCalledWith(
      "room.system.pendingRestoredDeathAvoidance",
    );
    expect(deps.playSe).toHaveBeenCalledWith("death_avoidance_alert");
  });

  it("does not play an alert SE when the pending targets another player", () => {
    const deps = makeDeps({ myPlayerId: "p2" });
    const msg: SessionRestoreLike = {
      pending_for_you: [baseEvasion, baseDeath],
    };
    applySessionRestorePendings(msg, deps);
    expect(deps.setEvasionRequest).toHaveBeenCalled();
    expect(deps.setDeathAvoidanceRequest).toHaveBeenCalled();
    expect(deps.playSe).not.toHaveBeenCalled();
  });

  it("logs expired pendings via the system chat with reason interpolation", () => {
    const deps = makeDeps();
    const msg: SessionRestoreLike = {
      expired_pending: [
        {
          pending_id: "pe-1",
          type: "evasion_request",
          auto_choice: "0_dice_evasion",
          reason: "timeout_during_disconnection",
        },
        {
          pending_id: "pd-1",
          type: "death_avoidance_request",
          auto_choice: "accept_death",
        },
      ],
    };
    applySessionRestorePendings(msg, deps);
    expect(deps.t).toHaveBeenCalledWith(
      "room.system.pendingExpiredEvasion",
      { reason: "timeout_during_disconnection" },
    );
    expect(deps.t).toHaveBeenCalledWith(
      "room.system.pendingExpiredDeathAvoidance",
      { reason: "accept_death" },
    );
    expect(deps.addSystemEntry).toHaveBeenCalledTimes(2);
  });

  it("is a no-op when neither field is present", () => {
    const deps = makeDeps();
    applySessionRestorePendings({}, deps);
    expect(deps.setEvasionRequest).not.toHaveBeenCalled();
    expect(deps.setDeathAvoidanceRequest).not.toHaveBeenCalled();
    expect(deps.addSystemEntry).not.toHaveBeenCalled();
    expect(deps.playSe).not.toHaveBeenCalled();
  });
});
