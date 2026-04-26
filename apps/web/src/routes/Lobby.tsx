import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { createRoom } from "../services/api";

export default function Lobby() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [scenarioId, setScenarioId] = useState("first_mission");
  const [playerName, setPlayerName] = useState("");
  const [joinRoomId, setJoinRoomId] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    // Phase 1: wire up createRoom
    const res = await createRoom({ scenario_id: scenarioId, player_name: playerName });
    navigate(`/room/${res.room_id}`);
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-3xl font-bold">{t("app.name")}</h1>
      <h2 className="text-xl">{t("lobby.title")}</h2>

      <form onSubmit={handleCreate} className="flex flex-col gap-4 w-full max-w-sm">
        <label className="flex flex-col gap-1">
          <span>{t("lobby.scenarioId")}</span>
          <input
            className="border rounded px-2 py-1"
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>{t("lobby.playerName")}</span>
          <input
            className="border rounded px-2 py-1"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            required
          />
        </label>
        <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2">
          {t("lobby.createRoom")}
        </button>
      </form>

      <div className="flex flex-col gap-2 w-full max-w-sm">
        <label className="flex flex-col gap-1">
          <span>{t("lobby.roomId")}</span>
          <input
            className="border rounded px-2 py-1"
            value={joinRoomId}
            onChange={(e) => setJoinRoomId(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="bg-green-600 text-white rounded px-4 py-2"
          onClick={() => joinRoomId && navigate(`/room/${joinRoomId}`)}
        >
          {t("lobby.joinRoom")}
        </button>
      </div>
    </main>
  );
}
