import { describe, it, expect, beforeAll, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import SessionLostScreen from "../../src/components/dialogs/SessionLostScreen";
import { useGameStore } from "../../src/stores/gameStore";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  useGameStore.setState({
    gameState: null,
    connectionStatus: "DISCONNECTED",
    lastSeenEventId: 0,
    myPlayerId: null,
    myToken: null,
  });
});

describe("SessionLostScreen", () => {
  it("ja and en both expose the session-lost dialog keys", () => {
    expect(ja).toHaveProperty("room.sessionLost.title");
    expect(ja).toHaveProperty("room.sessionLost.message");
    expect(ja).toHaveProperty("room.sessionLost.backToLobby");
    expect(en).toHaveProperty("room.sessionLost.title");
    expect(en).toHaveProperty("room.sessionLost.message");
    expect(en).toHaveProperty("room.sessionLost.backToLobby");
  });

  it("ja and en still have identical key sets", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ja).sort());
  });

  it("renders nothing when connection is not SESSION_LOST", () => {
    useGameStore.setState({ connectionStatus: "ACTIVE" });
    const { container } = render(
      <I18nextProvider i18n={i18n}>
        <SessionLostScreen onBackToLobby={() => {}} />
      </I18nextProvider>,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the dialog and fires onBackToLobby when SESSION_LOST", () => {
    useGameStore.setState({ connectionStatus: "SESSION_LOST" });
    const onBack = vi.fn();
    render(
      <I18nextProvider i18n={i18n}>
        <SessionLostScreen onBackToLobby={onBack} />
      </I18nextProvider>,
    );
    expect(screen.getByTestId("session-lost-screen")).toBeTruthy();
    expect(screen.getByText(ja["room.sessionLost.title"])).toBeTruthy();

    fireEvent.click(screen.getByText(ja["room.sessionLost.backToLobby"]));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("renders English copy after switching language", async () => {
    useGameStore.setState({ connectionStatus: "SESSION_LOST" });
    await i18n.changeLanguage("en");
    render(
      <I18nextProvider i18n={i18n}>
        <SessionLostScreen onBackToLobby={() => {}} />
      </I18nextProvider>,
    );
    expect(screen.getByText(en["room.sessionLost.title"])).toBeTruthy();
    expect(screen.getByText(en["room.sessionLost.backToLobby"])).toBeTruthy();
    await i18n.changeLanguage("ja");
  });
});
