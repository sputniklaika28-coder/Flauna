import { useTranslation } from "react-i18next";
import { useGameStore, usePendingStore, useUIStore } from "../../stores";

interface Props {
  onEndTurn: () => void;
}

export default function QuickActionBar({ onEndTurn }: Props) {
  const { t } = useTranslation();
  const { gameState, myPlayerId } = useGameStore();
  const openCastArt = useUIStore((s) => s.openCastArt);
  const submitting = usePendingStore((s) => s.submittingTurnAction);

  if (!gameState) return null;

  const { turn_order, current_turn_index, characters, machine_state } =
    gameState;
  const currentActorId =
    turn_order.length > 0
      ? turn_order[current_turn_index % turn_order.length]
      : null;
  const currentActor = characters.find((c) => c.id === currentActorId);
  const isMyTurn =
    currentActor?.player_id === myPlayerId &&
    machine_state === "IDLE";

  if (!isMyTurn) return null;

  const myChar = characters.find((c) => c.player_id === myPlayerId);
  const hasArts = (myChar?.arts ?? []).length > 0;

  return (
    <div
      className="border-t border-gray-700 bg-gray-900 px-4 py-2 flex items-center gap-3"
      data-testid="quickaction-bar"
      aria-busy={submitting}
    >
      <span className="text-yellow-400 text-sm font-semibold">
        {t("room.yourTurn")}
      </span>
      {hasArts && (
        <button
          onClick={() => openCastArt(null)}
          disabled={submitting}
          className="bg-purple-700 hover:bg-purple-600 text-white text-sm px-3 py-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="quickbar-cast-art"
        >
          {t("room.castArt.button")} ✦
        </button>
      )}
      <button
        onClick={onEndTurn}
        disabled={submitting}
        className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="quickbar-end-turn"
      >
        {t("room.endTurn")}
      </button>
      {submitting && (
        <span
          className="text-gray-400 text-xs italic"
          data-testid="quickbar-submitting"
          role="status"
        >
          {t("room.submitting")}
        </span>
      )}
    </div>
  );
}
