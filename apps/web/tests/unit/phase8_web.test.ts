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
  waitFor,
  act,
} from "@testing-library/react";
import React from "react";
import i18n, {
  SUPPORTED_LANGUAGES,
  detectInitialLanguage,
  setLanguage,
} from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import LanguageSwitcher from "../../src/components/common/LanguageSwitcher";
import {
  PLAYER_NAME_KEY,
  SESSION_KEY_PREFIX,
  clearSession,
  loadPlayerName,
  loadSession,
  savePlayerName,
  saveSession,
} from "../../src/services/sessionPersistence";

const STORAGE_KEY = "flauna.lang";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("Phase 8 web: i18n parity & settings keys", () => {
  it("ja and en have identical key sets", () => {
    const jaKeys = Object.keys(ja).sort();
    const enKeys = Object.keys(en).sort();
    expect(enKeys).toEqual(jaKeys);
  });

  it("settings.language exists in both locales", () => {
    expect(ja).toHaveProperty("settings.language");
    expect(en).toHaveProperty("settings.language");
    expect(ja["settings.language"]).not.toBe(en["settings.language"]);
  });

  it("supports ja and en", () => {
    expect(SUPPORTED_LANGUAGES).toEqual(["ja", "en"]);
  });
});

describe("Phase 8 web: detectInitialLanguage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns saved value when localStorage has a supported language", () => {
    window.localStorage.setItem(STORAGE_KEY, "en");
    expect(detectInitialLanguage()).toBe("en");
  });

  it("ignores unsupported saved values and falls back to navigator", () => {
    window.localStorage.setItem(STORAGE_KEY, "fr");
    const spy = vi
      .spyOn(window.navigator, "language", "get")
      .mockReturnValue("en-US");
    expect(detectInitialLanguage()).toBe("en");
    spy.mockRestore();
  });

  it("returns ja by default for non-en navigator", () => {
    const spy = vi
      .spyOn(window.navigator, "language", "get")
      .mockReturnValue("ja-JP");
    expect(detectInitialLanguage()).toBe("ja");
    spy.mockRestore();
  });
});

describe("Phase 8 web: setLanguage persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("changes i18n language and persists to localStorage", async () => {
    await setLanguage("en");
    expect(i18n.language).toBe("en");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("en");
    expect(document.documentElement.lang).toBe("en");

    await setLanguage("ja");
    expect(i18n.language).toBe("ja");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("ja");
    expect(document.documentElement.lang).toBe("ja");
  });
});

describe("Phase 8 web: player name persistence", () => {
  it("returns null when no name is saved", () => {
    expect(loadPlayerName()).toBeNull();
  });

  it("saves and loads a player name", () => {
    savePlayerName("祓魔師A");
    expect(window.localStorage.getItem(PLAYER_NAME_KEY)).toBe("祓魔師A");
    expect(loadPlayerName()).toBe("祓魔師A");
  });

  it("trims whitespace and ignores empty names", () => {
    savePlayerName("  Alice  ");
    expect(loadPlayerName()).toBe("Alice");

    savePlayerName("   ");
    // unchanged
    expect(loadPlayerName()).toBe("Alice");
  });
});

describe("Phase 8 web: session credential persistence", () => {
  const ROOM = "room-123";
  const SESSION = {
    player_id: "p1",
    player_token: "tok-abc",
    player_name: "Alice",
  };

  it("returns null when nothing is saved for the room", () => {
    expect(loadSession(ROOM)).toBeNull();
  });

  it("round-trips a session in sessionStorage", () => {
    saveSession(ROOM, SESSION);
    expect(window.sessionStorage.getItem(`${SESSION_KEY_PREFIX}${ROOM}`)).toBe(
      JSON.stringify(SESSION),
    );
    expect(loadSession(ROOM)).toEqual(SESSION);
  });

  it("clears only the targeted room's session", () => {
    saveSession(ROOM, SESSION);
    saveSession("other", { ...SESSION, player_id: "p2" });
    clearSession(ROOM);
    expect(loadSession(ROOM)).toBeNull();
    expect(loadSession("other")).not.toBeNull();
  });

  it("returns null for malformed JSON", () => {
    window.sessionStorage.setItem(`${SESSION_KEY_PREFIX}${ROOM}`, "{not json");
    expect(loadSession(ROOM)).toBeNull();
  });

  it("returns null when stored payload is missing required fields", () => {
    window.sessionStorage.setItem(
      `${SESSION_KEY_PREFIX}${ROOM}`,
      JSON.stringify({ player_id: "p1" }),
    );
    expect(loadSession(ROOM)).toBeNull();
  });
});

describe("Phase 8 web: LanguageSwitcher component", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    await i18n.changeLanguage("ja");
  });

  it("renders both supported languages as options", () => {
    render(React.createElement(LanguageSwitcher));
    const select = screen.getByRole("combobox");
    const options = Array.from(select.querySelectorAll("option")).map(
      (o) => o.value,
    );
    expect(options).toEqual(["ja", "en"]);
  });

  it("changes language and persists when selecting en", async () => {
    render(React.createElement(LanguageSwitcher));
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("ja");

    await act(async () => {
      fireEvent.change(select, { target: { value: "en" } });
    });
    await waitFor(() => {
      expect(i18n.language).toBe("en");
    });

    expect(i18n.language).toBe("en");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("en");

    await i18n.changeLanguage("ja");
  });
});
