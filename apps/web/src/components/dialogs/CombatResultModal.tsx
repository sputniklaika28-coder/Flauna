import { useTranslation } from "react-i18next";
import { useUIStore } from "../../stores";

interface Props {
  onBackToLobby: () => void;
}

export default function CombatResultModal({ onBackToLobby }: Props) {
  const { t } = useTranslation();
  const { combatResult, setCombatResult } = useUIStore();

  if (!combatResult) return null;

  const isVictory = combatResult === "victory";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div
        className={`rounded-xl p-8 w-80 text-center shadow-2xl border-2 ${
          isVictory
            ? "bg-gray-900 border-yellow-400"
            : "bg-gray-900 border-red-600"
        }`}
      >
        <div className={`text-5xl mb-4 ${isVictory ? "text-yellow-400" : "text-red-500"}`}>
          {isVictory ? "⚔" : "💀"}
        </div>
        <h2
          className={`text-2xl font-bold mb-2 ${isVictory ? "text-yellow-300" : "text-red-400"}`}
        >
          {isVictory ? t("combat.victory") : t("combat.defeat")}
        </h2>
        <p className="text-gray-400 text-sm mb-6">
          {isVictory ? t("combat.victoryMsg") : t("combat.defeatMsg")}
        </p>
        <button
          onClick={() => {
            setCombatResult(null);
            onBackToLobby();
          }}
          className="w-full bg-gray-700 hover:bg-gray-600 text-white rounded py-2 font-semibold"
        >
          {t("combat.backToLobby")}
        </button>
      </div>
    </div>
  );
}
