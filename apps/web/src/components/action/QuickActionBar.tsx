import { useTranslation } from "react-i18next";
import { useGameStore } from "../../stores";

interface Props {
  onEndTurn: () => void;
}

export default function QuickActionBar({ onEndTurn }: Props) {
  const { t } = useTranslation();
  const { gameState, myPlayerId } = useGameStore();

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

  return (
    <div className="border-t border-gray-700 bg-gray-900 px-4 py-2 flex items-center gap-3">
      <span className="text-yellow-400 text-sm font-semibold">
        {t("room.yourTurn")}
      </span>
      <button
        onClick={onEndTurn}
        className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1 rounded"
      >
        {t("room.endTurn")}
      </button>
    </div>
  );
}
