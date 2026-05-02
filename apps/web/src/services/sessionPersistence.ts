export const PLAYER_NAME_KEY = "flauna.playerName";
export const SESSION_KEY_PREFIX = "flauna.session.";

export interface PersistedSession {
  player_id: string;
  player_token: string;
  player_name: string;
}

function safeLocalStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

function safeSessionStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function loadPlayerName(): string | null {
  const ls = safeLocalStorage();
  if (!ls) return null;
  const v = ls.getItem(PLAYER_NAME_KEY);
  return v && v.length > 0 ? v : null;
}

export function savePlayerName(name: string): void {
  const ls = safeLocalStorage();
  if (!ls) return;
  const trimmed = name.trim();
  if (trimmed.length === 0) return;
  ls.setItem(PLAYER_NAME_KEY, trimmed);
}

function sessionKey(roomId: string): string {
  return `${SESSION_KEY_PREFIX}${roomId}`;
}

export function loadSession(roomId: string): PersistedSession | null {
  const ss = safeSessionStorage();
  if (!ss) return null;
  const raw = ss.getItem(sessionKey(roomId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedSession>;
    if (
      typeof parsed.player_id === "string" &&
      typeof parsed.player_token === "string" &&
      typeof parsed.player_name === "string"
    ) {
      return parsed as PersistedSession;
    }
  } catch {
    // fallthrough
  }
  return null;
}

export function saveSession(roomId: string, session: PersistedSession): void {
  const ss = safeSessionStorage();
  if (!ss) return;
  ss.setItem(sessionKey(roomId), JSON.stringify(session));
}

export function clearSession(roomId: string): void {
  const ss = safeSessionStorage();
  if (!ss) return;
  ss.removeItem(sessionKey(roomId));
}
