import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useGameStore, usePendingStore } from "../../stores";

interface Props {
  onSubmit: (pendingId: string, diceResult: number) => void;
}

export default function EvasionDialog({ onSubmit }: Props) {
  const { t } = useTranslation();
  const evasionRequest = usePendingStore((s) => s.evasionRequest);
  const { gameState, myPlayerId } = useGameStore();
  const [usedDice, setUsedDice] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const myChar = gameState?.characters.find((c) => c.player_id === myPlayerId);

  useEffect(() => {
    if (!evasionRequest) return;
    setSecondsLeft(evasionRequest.deadline_seconds);
    setUsedDice(0);

    const id = setInterval(
      () => setSecondsLeft((s) => Math.max(0, s - 1)),
      1000,
    );
    return () => clearInterval(id);
  }, [evasionRequest]);

  if (!evasionRequest) return null;

  const maxDice = myChar?.evasion_dice ?? 0;
  const attacker = gameState?.characters.find(
    (c) => c.id === evasionRequest.attacker_id,
  );

  const handleSubmit = () => {
    onSubmit(evasionRequest.pending_id, usedDice);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-gray-900 border border-yellow-500 rounded-lg p-6 w-80 text-white">
        <h2 className="text-lg font-bold text-yellow-400 mb-4">
          {t("room.evasion.title")}
        </h2>

        <div className="space-y-2 mb-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">{t("room.evasion.attacker")}</span>
            <span>{attacker?.name ?? evasionRequest.attacker_id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">
              {t("room.evasion.remainingDice")}
            </span>
            <span>{maxDice}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">
              {t("room.evasion.timeLeft", { s: secondsLeft })}
            </span>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-sm text-gray-400">
            {t("room.evasion.useDice")}: {usedDice}
          </label>
          <input
            type="range"
            min={0}
            max={maxDice}
            value={usedDice}
            onChange={(e) => setUsedDice(Number(e.target.value))}
            className="w-full mt-1"
          />
        </div>

        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setUsedDice(Math.ceil(maxDice / 2))}
            className="flex-1 bg-gray-700 hover:bg-gray-600 rounded py-1 text-sm"
          >
            {t("room.evasion.auto")}
          </button>
          <button
            onClick={() => setUsedDice(maxDice)}
            className="flex-1 bg-gray-700 hover:bg-gray-600 rounded py-1 text-sm"
          >
            {t("room.evasion.allOut")}
          </button>
          <button
            onClick={() => setUsedDice(0)}
            className="flex-1 bg-gray-700 hover:bg-gray-600 rounded py-1 text-sm"
          >
            {t("room.evasion.abandon")}
          </button>
        </div>

        <button
          onClick={handleSubmit}
          className="w-full bg-yellow-600 hover:bg-yellow-500 text-white rounded py-2 font-semibold"
        >
          {t("room.evasion.submit")}
        </button>
      </div>
    </div>
  );
}
