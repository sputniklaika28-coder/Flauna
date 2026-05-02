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
import { useToastStore } from "../../src/stores/toastStore";
import ToastContainer from "../../src/components/common/ToastContainer";
import {
  actionForError,
  messageForError,
} from "../../src/utils/errorToast";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  useToastStore.setState({ toasts: [] });
  vi.useRealTimers();
});

describe("Phase 9 web: toastStore", () => {
  it("pushes toasts and assigns ids", () => {
    const id = useToastStore
      .getState()
      .pushToast({ message: "hi", severity: "info" });
    expect(typeof id).toBe("string");
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({ id, message: "hi", severity: "info" });
  });

  it("respects an explicit id when provided", () => {
    const id = useToastStore
      .getState()
      .pushToast({ id: "fixed", message: "hi", severity: "warn" });
    expect(id).toBe("fixed");
    expect(useToastStore.getState().toasts[0]?.id).toBe("fixed");
  });

  it("dismisses a toast by id", () => {
    const id = useToastStore
      .getState()
      .pushToast({ message: "x", severity: "error" });
    useToastStore.getState().dismissToast(id);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("clears all toasts", () => {
    useToastStore.getState().pushToast({ message: "a", severity: "info" });
    useToastStore.getState().pushToast({ message: "b", severity: "warn" });
    useToastStore.getState().clearToasts();
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });
});

describe("Phase 9 web: ToastContainer", () => {
  it("renders nothing when there are no toasts", () => {
    render(React.createElement(ToastContainer));
    expect(screen.queryByTestId("toast-container")).toBeNull();
  });

  it("renders one item per toast with severity-based testid", () => {
    useToastStore.getState().pushToast({ message: "a", severity: "warn" });
    useToastStore.getState().pushToast({ message: "b", severity: "error" });
    render(React.createElement(ToastContainer));
    expect(screen.getByTestId("toast-container")).toBeTruthy();
    expect(screen.getByTestId("toast-warn").textContent).toContain("a");
    expect(screen.getByTestId("toast-error").textContent).toContain("b");
  });

  it("dismisses on close-button click", async () => {
    useToastStore.getState().pushToast({ message: "bye", severity: "info" });
    render(React.createElement(ToastContainer));
    const btn = screen.getByLabelText("dismiss");
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("auto-dismisses after the timeout", async () => {
    vi.useFakeTimers();
    useToastStore.getState().pushToast({ message: "auto", severity: "info" });
    render(React.createElement(ToastContainer));
    expect(useToastStore.getState().toasts).toHaveLength(1);
    await act(async () => {
      vi.advanceTimersByTime(4100);
    });
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });
});

describe("Phase 9 web: error → action mapping", () => {
  it("classifies player-action errors as toast/warn", () => {
    expect(actionForError("OUT_OF_TURN")).toEqual({
      kind: "toast",
      severity: "warn",
    });
    expect(actionForError("INVALID_PATH")).toEqual({
      kind: "toast",
      severity: "warn",
    });
    expect(actionForError("INSUFFICIENT_MP")).toEqual({
      kind: "toast",
      severity: "warn",
    });
  });

  it("classifies auth and room-not-found errors as navigate/error", () => {
    expect(actionForError("AUTH_INVALID_TOKEN")).toEqual({
      kind: "navigate",
      severity: "error",
    });
    expect(actionForError("ROOM_NOT_FOUND")).toEqual({
      kind: "navigate",
      severity: "error",
    });
  });

  it("classifies AI_FALLBACK as informational", () => {
    expect(actionForError("AI_FALLBACK")).toEqual({
      kind: "toast",
      severity: "info",
    });
  });

  it("classifies VERSION_MISMATCH and DUPLICATE_REQUEST as silent", () => {
    expect(actionForError("VERSION_MISMATCH").kind).toBe("silent");
    expect(actionForError("DUPLICATE_REQUEST").kind).toBe("silent");
  });

  it("falls back to error/toast for unknown codes", () => {
    expect(actionForError("WHO_KNOWS")).toEqual({
      kind: "toast",
      severity: "error",
    });
  });
});

describe("Phase 9 web: error i18n", () => {
  it("ja and en both expose the error keys", () => {
    expect(ja).toHaveProperty("room.error.OUT_OF_TURN");
    expect(ja).toHaveProperty("room.error.INSUFFICIENT_MP");
    expect(ja).toHaveProperty("room.error.INVALID_PATH");
    expect(ja).toHaveProperty("room.error.AUTH_INVALID_TOKEN");
    expect(ja).toHaveProperty("room.error.AI_FALLBACK");
    expect(en).toHaveProperty("room.error.OUT_OF_TURN");
    expect(en).toHaveProperty("room.error.AUTH_INVALID_TOKEN");
    expect(en).toHaveProperty("room.error.generic");
  });

  it("ja and en still have identical key sets", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(ja).sort());
  });

  it("messageForError returns the localized string for known codes", async () => {
    await i18n.changeLanguage("ja");
    expect(messageForError(i18n.t.bind(i18n), "OUT_OF_TURN")).toBe(
      "あなたの番ではありません",
    );
    await i18n.changeLanguage("en");
    expect(messageForError(i18n.t.bind(i18n), "OUT_OF_TURN")).toBe(
      "It's not your turn",
    );
  });

  it("messageForError falls back to a generic template for unknown codes", async () => {
    await i18n.changeLanguage("ja");
    const msg = messageForError(i18n.t.bind(i18n), "MYSTERIOUS_FAILURE");
    expect(msg).toContain("MYSTERIOUS_FAILURE");
  });
});
