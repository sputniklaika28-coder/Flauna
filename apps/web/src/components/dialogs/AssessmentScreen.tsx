import { useTranslation } from "react-i18next";
import { useGameStore } from "../../stores";
import type { Grade, SessionScore } from "../../types";

interface Props {
  onBackToLobby: () => void;
}

const GRADE_COLOR: Record<Grade, string> = {
  S: "text-yellow-300 border-yellow-400",
  A: "text-amber-300 border-amber-400",
  B: "text-emerald-300 border-emerald-400",
  C: "text-sky-300 border-sky-400",
  D: "text-gray-300 border-gray-500",
};

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between py-1 border-b border-gray-700 last:border-b-0 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="font-mono text-white">{value}</span>
    </div>
  );
}

export default function AssessmentScreen({ onBackToLobby }: Props) {
  const { t } = useTranslation();
  const { gameState } = useGameStore();

  if (!gameState || gameState.phase !== "assessment") return null;
  const score: SessionScore | null | undefined = gameState.assessment_result;
  if (!score) return null;

  const isVictory = score.outcome === "victory";
  const gradeColor = GRADE_COLOR[score.grade];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
      data-testid="assessment-screen"
    >
      <div className="bg-gray-900 rounded-xl p-8 w-[28rem] shadow-2xl border-2 border-gray-700">
        <div className="text-center mb-6">
          <p className="text-xs text-gray-500 uppercase tracking-widest">
            {t("room.assessment.title")}
          </p>
          <h2
            className={`text-2xl font-bold mt-1 ${
              isVictory ? "text-yellow-300" : "text-red-400"
            }`}
          >
            {isVictory
              ? t("room.assessment.outcomeVictory")
              : t("room.assessment.outcomeDefeat")}
          </h2>
        </div>

        <div className="flex justify-center mb-6">
          <div
            className={`w-28 h-28 rounded-full border-4 flex items-center justify-center text-6xl font-black bg-gray-950 ${gradeColor}`}
            data-testid="assessment-grade"
          >
            {score.grade}
          </div>
        </div>

        <div className="bg-gray-950/60 rounded p-3 mb-6">
          <StatRow
            label={t("room.assessment.rounds")}
            value={score.rounds_taken}
          />
          <StatRow
            label={t("room.assessment.pcsAlive")}
            value={`${score.pcs_alive} / ${score.pcs_total}`}
          />
          <StatRow
            label={t("room.assessment.enemiesDefeated")}
            value={`${score.enemies_defeated} / ${score.enemies_total}`}
          />
          <StatRow
            label={t("room.assessment.grade")}
            value={t(`room.assessment.gradeLabel.${score.grade}`)}
          />
        </div>

        <button
          onClick={onBackToLobby}
          className="w-full bg-gray-700 hover:bg-gray-600 text-white rounded py-2 font-semibold"
          data-testid="assessment-back"
        >
          {t("room.assessment.backToLobby")}
        </button>
      </div>
    </div>
  );
}
