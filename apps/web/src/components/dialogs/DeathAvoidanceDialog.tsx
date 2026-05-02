import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useGameStore, usePendingStore } from "../../stores";
import { useDeadlineUrgency } from "../../hooks/useDeadlineUrgency";
import type { DeathAvoidanceChoice } from "../../types";

interface Props {
  onSubmit: (pendingId: string, choice: DeathAvoidanceChoice) => void;
}

export default function DeathAvoidanceDialog({ onSubmit }: Props) {
  const { t } = useTranslation();
  const request = usePendingStore((s) => s.deathAvoidanceRequest);
  const { gameState } = useGameStore();
  const [choice, setChoice] = useState<DeathAvoidanceChoice>("avoid_death");
  const [secondsLeft, setSecondsLeft] = useState(0);

  const target = gameState?.characters.find(
    (c) => c.id === request?.target_character_id,
  );
  const katashiroHeld = target?.inventory["katashiro"] ?? 0;
  const hasEnough = katashiroHeld >= (request?.katashiro_required ?? 2);

  useEffect(() => {
    if (!request) return;
    setSecondsLeft(request.deadline_seconds);
    setChoice(hasEnough ? "avoid_death" : "accept_death");

    const id = setInterval(
      () => setSecondsLeft((s) => Math.max(0, s - 1)),
      1000,
    );
    return () => clearInterval(id);
  }, [request, hasEnough]);

  const urgency = useDeadlineUrgency(secondsLeft, request !== null);

  if (!request) return null;

  const handleSubmit = () => {
    if (urgency.isExpired) return;
    onSubmit(request.pending_id, choice);
  };

  const n = request.katashiro_required;

  const borderClass = urgency.isExpired
    ? "border-gray-500 opacity-80"
    : urgency.isCritical
      ? "border-red-500 animate-pulse"
      : "border-red-500";
  const timerClass = urgency.isExpired
    ? "text-gray-400"
    : urgency.isCritical
      ? "text-red-400 font-bold animate-pulse"
      : urgency.isWarning
        ? "text-orange-400 font-semibold"
        : "text-yellow-400";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div
        data-testid="death-avoidance-dialog"
        className={`bg-gray-900 border rounded-lg p-6 w-96 text-white ${borderClass}`}
      >
        <h2 className="text-lg font-bold text-red-400 mb-4">
          💀 {t("room.deathAvoidance.title")}
        </h2>

        <div className="space-y-2 mb-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">
              {t("room.deathAvoidance.incomingDamage")}
            </span>
            <span className="text-red-300 font-bold">
              {request.incoming_damage}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">
              {t("room.deathAvoidance.currentHp")}
            </span>
            <span>{target?.hp ?? "?"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">
              {t("room.deathAvoidance.katashiroRemaining")}
            </span>
            <span>{katashiroHeld}枚</span>
          </div>
          <div className="flex justify-between">
            <span
              data-testid="death-avoidance-timer"
              className={timerClass}
              aria-live={urgency.isCritical ? "assertive" : "polite"}
            >
              {urgency.isExpired
                ? t("room.deathAvoidance.expired")
                : t("room.deathAvoidance.timeLeft", { s: secondsLeft })}
            </span>
          </div>
        </div>

        <div className="space-y-2 mb-5">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="death-choice"
              value="avoid_death"
              checked={choice === "avoid_death"}
              onChange={() => setChoice("avoid_death")}
              disabled={!hasEnough}
              className="mt-0.5"
            />
            <span className={!hasEnough ? "text-gray-500" : ""}>
              {t("room.deathAvoidance.avoidDeath", { n })}
              {!hasEnough && (
                <span className="ml-1 text-red-400 text-xs">
                  ({t("room.deathAvoidance.noKatashiro")})
                </span>
              )}
            </span>
          </label>

          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="death-choice"
              value="respawn"
              checked={choice === "respawn"}
              onChange={() => setChoice("respawn")}
              disabled={!hasEnough}
              className="mt-0.5"
            />
            <span className={!hasEnough ? "text-gray-500" : ""}>
              {t("room.deathAvoidance.respawn", { n })}
              {!hasEnough && (
                <span className="ml-1 text-red-400 text-xs">
                  ({t("room.deathAvoidance.noKatashiro")})
                </span>
              )}
            </span>
          </label>

          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="death-choice"
              value="accept_death"
              checked={choice === "accept_death"}
              onChange={() => setChoice("accept_death")}
              className="mt-0.5"
            />
            <span className="text-red-300">{t("room.deathAvoidance.accept")}</span>
          </label>
        </div>

        <button
          onClick={handleSubmit}
          disabled={urgency.isExpired}
          className="w-full bg-red-700 hover:bg-red-600 text-white rounded py-2 font-semibold disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed"
        >
          {t("room.deathAvoidance.submit")}
        </button>
      </div>
    </div>
  );
}
