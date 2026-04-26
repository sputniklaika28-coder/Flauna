import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import "../../src/i18n";
import Lobby from "../../src/routes/Lobby";

vi.mock("../../src/services/api", () => ({
  createRoom: vi.fn().mockResolvedValue({
    room_id: "room-test",
    master_token: "token",
    scenario_title: "first_mission",
  }),
  joinRoom: vi.fn().mockResolvedValue({
    player_id: "player-test",
    player_token: "ptoken",
    room_info: {},
  }),
}));

describe("Lobby", () => {
  it("renders the title", () => {
    render(
      <MemoryRouter>
        <Lobby />
      </MemoryRouter>
    );
    expect(screen.getByText("TacEx")).toBeDefined();
  });

  it("renders create and join sections", () => {
    render(
      <MemoryRouter>
        <Lobby />
      </MemoryRouter>
    );
    expect(screen.getByText("新しいルームを作成")).toBeDefined();
    expect(screen.getByText("ルームに参加")).toBeDefined();
  });
});
