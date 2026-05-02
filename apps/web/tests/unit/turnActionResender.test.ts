import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  rememberSubmit,
  clearLastSubmit,
  getLastSubmit,
  resubmitWithCurrentVersion,
  type TurnActionPayload,
} from "../../src/services/turnActionResender";

function makePayload(version: number): TurnActionPayload {
  return {
    action: "submit_turn_action",
    player_id: "p1",
    room_id: "r1",
    client_request_id: "req-old",
    expected_version: version,
    turn_action: { end_turn: true },
  };
}

beforeEach(() => {
  clearLastSubmit();
});

describe("Phase 9 web: turnActionResender", () => {
  it("remembers the last submitted payload", () => {
    const p = makePayload(3);
    rememberSubmit(p);
    expect(getLastSubmit()).toEqual(p);
  });

  it("clearLastSubmit erases the stored payload", () => {
    rememberSubmit(makePayload(3));
    clearLastSubmit();
    expect(getLastSubmit()).toBeNull();
  });

  it("returns false when there's nothing to resubmit", () => {
    const send = vi.fn();
    const ok = resubmitWithCurrentVersion({
      send,
      getCurrentVersion: () => 5,
      newRequestId: () => "req-new",
    });
    expect(ok).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it("returns false when the current version is not advanced past last send", () => {
    rememberSubmit(makePayload(5));
    const send = vi.fn();
    // Current version equal to last expected_version → still mismatched per
    // server but no fresh state to retry against.
    const ok = resubmitWithCurrentVersion({
      send,
      getCurrentVersion: () => 5,
      newRequestId: () => "req-new",
    });
    expect(ok).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it("returns false when getCurrentVersion is undefined", () => {
    rememberSubmit(makePayload(3));
    const send = vi.fn();
    const ok = resubmitWithCurrentVersion({
      send,
      getCurrentVersion: () => undefined,
      newRequestId: () => "req-new",
    });
    expect(ok).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it("re-sends with a fresh request id and the current version", () => {
    rememberSubmit(makePayload(3));
    const send = vi.fn();
    const ok = resubmitWithCurrentVersion({
      send,
      getCurrentVersion: () => 7,
      newRequestId: () => "req-new",
    });
    expect(ok).toBe(true);
    expect(send).toHaveBeenCalledTimes(1);
    const sent = send.mock.calls[0][0] as TurnActionPayload;
    expect(sent).toMatchObject({
      action: "submit_turn_action",
      player_id: "p1",
      room_id: "r1",
      client_request_id: "req-new",
      expected_version: 7,
      turn_action: { end_turn: true },
    });
  });

  it("updates the remembered payload after a successful resubmit", () => {
    rememberSubmit(makePayload(3));
    const send = vi.fn();
    resubmitWithCurrentVersion({
      send,
      getCurrentVersion: () => 7,
      newRequestId: () => "req-new",
    });
    const stashed = getLastSubmit();
    expect(stashed).not.toBeNull();
    expect(stashed?.expected_version).toBe(7);
    expect(stashed?.client_request_id).toBe("req-new");
  });

  it("supports a chain of VERSION_MISMATCH retries", () => {
    rememberSubmit(makePayload(3));
    const send = vi.fn();
    let id = 0;
    const newRequestId = () => `req-${++id}`;
    // First retry: version 4
    expect(
      resubmitWithCurrentVersion({
        send,
        getCurrentVersion: () => 4,
        newRequestId,
      }),
    ).toBe(true);
    // Second retry: version 5
    expect(
      resubmitWithCurrentVersion({
        send,
        getCurrentVersion: () => 5,
        newRequestId,
      }),
    ).toBe(true);
    expect(send).toHaveBeenCalledTimes(2);
    expect(getLastSubmit()?.expected_version).toBe(5);
    expect(getLastSubmit()?.client_request_id).toBe("req-2");
  });
});
