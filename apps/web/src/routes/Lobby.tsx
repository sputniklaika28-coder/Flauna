import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

interface CreateRoomResponse {
  room_id: string;
  master_token: string;
  scenario_title: string;
}

interface JoinRoomResponse {
  player_id: string;
  player_token: string;
  room_info: { room_id: string; title: string };
}

export default function Lobby() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [scenarioId, setScenarioId] = useState("first_mission");
  const [playerName, setPlayerName] = useState("");
  const [joinRoomId, setJoinRoomId] = useState("");
  const [joinPlayerName, setJoinPlayerName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/rooms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: scenarioId, player_name: playerName }),
      });
      if (!res.ok) throw new Error(t("errors.connectionFailed"));
      const data: CreateRoomResponse = await res.json();
      sessionStorage.setItem(`token:${data.room_id}`, data.master_token);
      navigate(`/room/${data.room_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.unknown"));
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/rooms/${joinRoomId}/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_name: joinPlayerName }),
      });
      if (res.status === 404) throw new Error(t("errors.roomNotFound"));
      if (!res.ok) throw new Error(t("errors.connectionFailed"));
      const data: JoinRoomResponse = await res.json();
      sessionStorage.setItem(`token:${joinRoomId}`, data.player_token);
      sessionStorage.setItem(`playerId:${joinRoomId}`, data.player_id);
      navigate(`/room/${joinRoomId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.unknown"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ padding: "2rem", maxWidth: 480, margin: "0 auto" }}>
      <h1>{t("lobby.title")}</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}

      <section>
        <h2>{t("lobby.createRoom")}</h2>
        <form onSubmit={handleCreate}>
          <div>
            <label>
              {t("lobby.scenarioId")}
              <input
                value={scenarioId}
                onChange={(e) => setScenarioId(e.target.value)}
                required
              />
            </label>
          </div>
          <div>
            <label>
              {t("lobby.playerName")}
              <input
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                required
              />
            </label>
          </div>
          <button type="submit" disabled={busy}>
            {busy ? t("lobby.creating") : t("lobby.submit")}
          </button>
        </form>
      </section>

      <hr />

      <section>
        <h2>{t("lobby.joinRoom")}</h2>
        <form onSubmit={handleJoin}>
          <div>
            <label>
              {t("lobby.roomId")}
              <input
                value={joinRoomId}
                onChange={(e) => setJoinRoomId(e.target.value)}
                required
              />
            </label>
          </div>
          <div>
            <label>
              {t("lobby.playerName")}
              <input
                value={joinPlayerName}
                onChange={(e) => setJoinPlayerName(e.target.value)}
                required
              />
            </label>
          </div>
          <button type="submit" disabled={busy}>
            {busy ? t("lobby.joining") : t("lobby.submit")}
          </button>
        </form>
      </section>
    </main>
  );
}
