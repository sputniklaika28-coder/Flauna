import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createRoom, joinRoom } from "../../src/services/api";

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function makeResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// createRoom
// ---------------------------------------------------------------------------

describe("createRoom", () => {
  it("posts to /api/v1/rooms and returns response", async () => {
    const mockBody = {
      room_id: "room-abc123",
      master_token: "tok-xyz",
      scenario_title: "最初の任務",
    };
    mockFetch.mockResolvedValueOnce(makeResponse(200, mockBody));

    const result = await createRoom({ scenario_id: "first_mission", player_name: "GM" });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/rooms");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      scenario_id: "first_mission",
      player_name: "GM",
    });
    expect(result).toEqual(mockBody);
  });

  it("throws on HTTP error with status and body", async () => {
    mockFetch.mockResolvedValueOnce(
      makeResponse(422, { detail: [{ msg: "field required" }] }),
    );

    await expect(createRoom({ scenario_id: "", player_name: "" })).rejects.toMatchObject({
      message: "HTTP 422",
      status: 422,
    });
  });

  it("throws on 500 error", async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(500, {}));

    await expect(
      createRoom({ scenario_id: "first_mission", player_name: "GM" }),
    ).rejects.toMatchObject({ message: "HTTP 500" });
  });

  it("includes content-type header", async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(200, { room_id: "r", master_token: "t", scenario_title: "s" }));
    await createRoom({ scenario_id: "s", player_name: "n" });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["content-type"]).toBe("application/json");
  });
});

// ---------------------------------------------------------------------------
// joinRoom
// ---------------------------------------------------------------------------

describe("joinRoom", () => {
  it("posts to /api/v1/rooms/{room_id}/join and returns response", async () => {
    const mockBody = {
      player_id: "player-xyz",
      player_token: "ptok-abc",
      room_info: { room_id: "room-abc123", title: "最初の任務" },
    };
    mockFetch.mockResolvedValueOnce(makeResponse(200, mockBody));

    const result = await joinRoom("room-abc123", { player_name: "Alice" });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/rooms/room-abc123/join");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ player_name: "Alice" });
    expect(result).toEqual(mockBody);
  });

  it("throws 404 when room not found", async () => {
    mockFetch.mockResolvedValueOnce(
      makeResponse(404, { detail: { error: { code: "ROOM_NOT_FOUND" } } }),
    );

    await expect(joinRoom("room-nonexistent", { player_name: "Bob" })).rejects.toMatchObject({
      message: "HTTP 404",
      status: 404,
    });
  });

  it("body is attached to thrown error", async () => {
    const errorBody = { detail: { error: { code: "ROOM_NOT_FOUND" } } };
    mockFetch.mockResolvedValueOnce(makeResponse(404, errorBody));

    let caught: unknown;
    try {
      await joinRoom("room-x", { player_name: "Bob" });
    } catch (e) {
      caught = e;
    }
    expect((caught as { body: unknown }).body).toEqual(errorBody);
  });
});
