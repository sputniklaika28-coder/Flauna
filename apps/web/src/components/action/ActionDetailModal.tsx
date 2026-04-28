import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useGameStore, useUIStore } from "../../stores";

type MeleeStyle = "none" | "連撃" | "精密攻撃" | "強攻撃" | "全力攻撃";
type MoveMode = "normal" | "attack_focus" | "tactical_maneuver";

interface AttackPayload {
  targetId: string;
  weaponId: string;
  style: MeleeStyle;
  moveMode: MoveMode;
  diceDistribution: number[];
}

interface Props {
  onSubmit: (payload: AttackPayload) => void;
}

const MELEE_STYLES: MeleeStyle[] = ["none", "連撃", "精密攻撃", "強攻撃", "全力攻撃"];
const MOVE_MODES: MoveMode[] = ["normal", "attack_focus", "tactical_maneuver"];

export default function ActionDetailModal({ onSubmit }: Props) {
  const { t } = useTranslation();
  const { activeModal, actionDetailTargetId, closeModal } = useUIStore();
  const { gameState, myPlayerId } = useGameStore();

  const [style, setStyle] = useState<MeleeStyle>("none");
  const [moveMode, setMoveMode] = useState<MoveMode>("normal");
  const [diceCount, setDiceCount] = useState(1);

  const isOpen = activeModal === "action_detail" && actionDetailTargetId !== null;

  const myChar = gameState?.characters.find((c) => c.player_id === myPlayerId);
  const target = gameState?.characters.find((c) => c.id === actionDetailTargetId);
  const weaponId = myChar?.equipped_weapons[0] ?? "default";

  // Base dice from character's first weapon (simplified: tai as proxy).
  const maxDice = myChar?.tai ?? 4;

  const handleAutoDistribute = useCallback(() => {
    setDiceCount(maxDice);
  }, [maxDice]);

  const handleSubmit = useCallback(() => {
    if (!actionDetailTargetId) return;
    onSubmit({
      targetId: actionDetailTargetId,
      weaponId,
      style,
      moveMode,
      diceDistribution: [diceCount],
    });
    closeModal();
  }, [actionDetailTargetId, weaponId, style, moveMode, diceCount, onSubmit, closeModal]);

  if (!isOpen || !target || !myChar) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-gray-900 border border-gray-600 rounded-lg p-6 w-96 text-white">
        <h2 className="text-lg font-bold text-white mb-4">{t("room.action.title")}</h2>

        {/* Weapon */}
        <div className="mb-3">
          <label className="text-xs text-gray-400 block mb-1">{t("room.action.weapon")}</label>
          <div className="bg-gray-800 rounded px-3 py-2 text-sm">{weaponId}</div>
        </div>

        {/* Move mode */}
        <div className="mb-3">
          <label className="text-xs text-gray-400 block mb-1">{t("room.action.moveMode")}</label>
          <div className="space-y-1">
            {MOVE_MODES.map((m) => (
              <label key={m} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="moveMode"
                  value={m}
                  checked={moveMode === m}
                  onChange={() => setMoveMode(m)}
                  className="accent-yellow-500"
                />
                <span className="text-sm">{t(`room.action.moveMode.${m}`)}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Style */}
        <div className="mb-3">
          <label className="text-xs text-gray-400 block mb-1">{t("room.action.style")}</label>
          <div className="grid grid-cols-2 gap-1">
            {MELEE_STYLES.map((s) => (
              <label key={s} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="style"
                  value={s}
                  checked={style === s}
                  onChange={() => setStyle(s)}
                  className="accent-yellow-500"
                />
                <span className="text-sm">{t(`room.action.style.${s}`)}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Target */}
        <div className="mb-3">
          <label className="text-xs text-gray-400 block mb-1">{t("room.action.target")}</label>
          <div className="bg-gray-800 rounded px-3 py-2 text-sm">
            {target.name} (HP {target.hp}/{target.max_hp})
          </div>
        </div>

        {/* Dice distribution */}
        <div className="mb-4">
          <label className="text-xs text-gray-400 block mb-1">
            {t("room.action.dice")}: {diceCount}
          </label>
          <input
            type="range"
            min={1}
            max={maxDice}
            value={diceCount}
            onChange={(e) => setDiceCount(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            <span>{t("room.action.totalDice", { total: diceCount, max: maxDice })}</span>
            <span>{maxDice}</span>
          </div>
          <button
            onClick={handleAutoDistribute}
            className="mt-2 text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded"
          >
            {t("room.action.autoDistribute")}
          </button>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={closeModal}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white rounded py-2 text-sm"
          >
            {t("room.action.cancel")}
          </button>
          <button
            onClick={handleSubmit}
            className="flex-1 bg-yellow-600 hover:bg-yellow-500 text-white rounded py-2 text-sm font-semibold"
          >
            {t("room.action.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
