import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import "../setup";
import "../../src/i18n/index";
import Lobby from "../../src/routes/Lobby";

describe("Lobby", () => {
  it("renders lobby heading", () => {
    render(
      <MemoryRouter>
        <Lobby />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("ロビー");
  });

  it("renders create and join sections", () => {
    render(
      <MemoryRouter>
        <Lobby />
      </MemoryRouter>,
    );
    expect(screen.getByText("ルームを作成")).toBeTruthy();
    expect(screen.getByText("ルームに参加")).toBeTruthy();
  });
});
