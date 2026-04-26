import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createRoom, joinRoom } from "../services/api";

export default function Lobby() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [playerName, setPlayerName] = useState("");
  const [scenarioId, setScenarioId] = useState("first_mission");
  const [roomId, setRoomId] = useState("");
  const [creating, setCreating] = useState(false);
  const [joining, setJoining] = useState(false);

  async function handleCreate() {
    setCreating(true);
    try {
      const result = await createRoom(scenarioId, playerName);
      sessionStorage.setItem("room_id", result.room_id);
      sessionStorage.setItem("master_token", result.master_token);
      void navigate(`/room/${result.room_id}`);
    } finally {
      setCreating(false);
    }
  }

  async function handleJoin() {
    setJoining(true);
    try {
      const result = await joinRoom(roomId, playerName);
      sessionStorage.setItem("room_id", roomId);
      sessionStorage.setItem("player_id", result.player_id);
      sessionStorage.setItem("player_token", result.player_token);
      void navigate(`/room/${roomId}`);
    } finally {
      setJoining(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
      <div className="max-w-md w-full p-8 space-y-8">
        <h1 className="text-4xl font-bold text-center">{t("lobby.title")}</h1>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">{t("lobby.newRoom")}</h2>
          <input
            className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-600"
            placeholder={t("lobby.playerName")}
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
          />
          <input
            className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-600"
            placeholder={t("lobby.scenarioId")}
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
          />
          <button
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded font-semibold"
            onClick={() => void handleCreate()}
            disabled={creating || !playerName}
          >
            {creating ? t("lobby.creating") : t("lobby.create")}
          </button>
        </section>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">{t("lobby.joinRoom")}</h2>
          <input
            className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-600"
            placeholder={t("lobby.playerName")}
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
          />
          <input
            className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-600"
            placeholder={t("lobby.roomId")}
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          />
          <button
            className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded font-semibold"
            onClick={() => void handleJoin()}
            disabled={joining || !playerName || !roomId}
          >
            {joining ? t("lobby.joining") : t("lobby.join")}
          </button>
        </section>
      </div>
    </div>
  );
}
