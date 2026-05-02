import type { TFunction } from "i18next";
import type { ToastSeverity } from "../stores/toastStore";

/**
 * Per spec §10-1: how each ErrorCode should surface to the user.
 *
 * - "toast": pop a transient toast (severity decides color)
 * - "navigate": fatal — surface a toast then drop the user back to the lobby
 * - "silent": handled elsewhere (e.g. VERSION_MISMATCH has its own retry path)
 */
export type ErrorAction =
  | { kind: "toast"; severity: ToastSeverity }
  | { kind: "navigate"; severity: ToastSeverity }
  | { kind: "silent" };

const ERROR_ACTIONS: Record<string, ErrorAction> = {
  // Auth — fatal, return to lobby
  AUTH_INVALID_TOKEN: { kind: "navigate", severity: "error" },
  AUTH_TOKEN_EXPIRED: { kind: "navigate", severity: "error" },
  AUTH_PERMISSION_DENIED: { kind: "navigate", severity: "error" },
  ROOM_NOT_FOUND: { kind: "navigate", severity: "error" },

  // Room-state issues — toast and recover in place
  ROOM_FULL: { kind: "toast", severity: "warn" },
  DUPLICATE_CONNECTION: { kind: "toast", severity: "warn" },
  STATE_LOCK_TIMEOUT: { kind: "toast", severity: "warn" },

  // Player action errors — toast
  OUT_OF_TURN: { kind: "toast", severity: "warn" },
  INVALID_STATE_TRANSITION: { kind: "toast", severity: "warn" },
  INVALID_PATH: { kind: "toast", severity: "warn" },
  OUT_OF_RANGE: { kind: "toast", severity: "warn" },
  UNKNOWN_TARGET: { kind: "toast", severity: "warn" },
  UNKNOWN_CHARACTER: { kind: "toast", severity: "warn" },
  UNKNOWN_WEAPON: { kind: "toast", severity: "warn" },
  INVALID_DICE_DISTRIBUTION: { kind: "toast", severity: "warn" },
  INVALID_ACTION_SEQUENCE: { kind: "toast", severity: "warn" },
  INSUFFICIENT_MP: { kind: "toast", severity: "warn" },
  INSUFFICIENT_KATASHIRO: { kind: "toast", severity: "warn" },
  NO_LINE_OF_SIGHT: { kind: "toast", severity: "warn" },
  PENDING_NOT_FOUND: { kind: "toast", severity: "warn" },
  PENDING_EXPIRED: { kind: "toast", severity: "warn" },

  // AI — only major failures should surface; AI_FALLBACK is informational
  AI_FALLBACK: { kind: "toast", severity: "info" },
  AI_PARSE_ERROR: { kind: "toast", severity: "warn" },
  AI_BACKEND_UNAVAILABLE: { kind: "toast", severity: "error" },

  // Handled by automatic retry / dedup elsewhere
  VERSION_MISMATCH: { kind: "silent" },
  DUPLICATE_REQUEST: { kind: "silent" },
  INVALID_MESSAGE: { kind: "silent" },
};

export function actionForError(code: string): ErrorAction {
  return ERROR_ACTIONS[code] ?? { kind: "toast", severity: "error" };
}

/** Look up a localized message; falls back to the generic "Error: {{code}}". */
export function messageForError(t: TFunction, code: string): string {
  const key = `room.error.${code}`;
  const localized = t(key, { defaultValue: "" });
  if (localized) return localized;
  return t("room.error.generic", { code });
}
