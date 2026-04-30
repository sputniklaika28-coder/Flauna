import { useTranslation } from "react-i18next";
import { useGameStore } from "../../stores";
import type { Character, PressureLevel } from "../../types";

const PRESSURE_BG: Record<PressureLevel, string> = {
  normal: "bg-gray-800 border-gray-700",
  hard: "bg-orange-900/40 border-orange-500",
  ultra_hard: "bg-red-900/50 border-red-500",
};

const PRESSURE_TEXT: Record<PressureLevel, string> = {
  normal: "text-gray-300",
  hard: "text-orange-300",
  ultra_hard: "text-red-300",
};

function ResourceBar({
  current,
  max,
  color,
}: {
  current: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? Math.round((current / max) * 100) : 0;
  return (
    <div className="w-full h-2 bg-gray-700 rounded overflow-hidden">
      <div
        className={`h-full ${color} transition-all`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function CharCard({ char, isCurrent }: { char: Character; isCurrent: boolean }) {
  const { t } = useTranslation();
  return (
    <div
      className={`p-2 rounded mb-2 text-sm ${
        isCurrent
          ? "border border-yellow-400 bg-gray-750"
          : "border border-gray-700 bg-gray-800"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold truncate">{char.name}</span>
        {isCurrent && (
          <span className="text-xs text-yellow-400 ml-1">▶</span>
        )}
      </div>
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>{t("room.hp")}</span>
          <span>
            {char.hp}/{char.max_hp}
          </span>
        </div>
        <ResourceBar current={char.hp} max={char.max_hp} color="bg-red-500" />
        <div className="flex justify-between text-xs text-gray-400">
          <span>{t("room.mp")}</span>
          <span>
            {char.mp}/{char.max_mp}
          </span>
        </div>
        <ResourceBar current={char.mp} max={char.max_mp} color="bg-blue-500" />
        <div className="flex justify-between text-xs text-gray-400">
          <span>{t("room.evasion")}</span>
          <span>
            {char.evasion_dice}/{char.max_evasion_dice}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function SideMenu() {
  const { t } = useTranslation();
  const { gameState, myPlayerId } = useGameStore();

  if (!gameState) return null;

  const { characters, turn_order, current_turn_index } = gameState;
  const currentActorId =
    turn_order.length > 0
      ? turn_order[current_turn_index % turn_order.length]
      : null;

  const myChars = characters.filter((c) => c.player_id === myPlayerId);
  const others = characters.filter((c) => c.player_id !== myPlayerId);

  return (
    <aside className="w-52 bg-gray-900 text-white p-2 overflow-y-auto flex-shrink-0">
      {myChars.map((c) => (
        <CharCard key={c.id} char={c} isCurrent={c.id === currentActorId} />
      ))}

      {others.length > 0 && (
        <>
          <div className="text-xs text-gray-500 uppercase tracking-wide my-2">
            {t("room.turnOrder")}
          </div>
          {others.map((c) => (
            <CharCard
              key={c.id}
              char={c}
              isCurrent={c.id === currentActorId}
            />
          ))}
        </>
      )}

      {turn_order.length > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            {t("room.turnOrder")}
          </div>
          <ol className="space-y-0.5">
            {turn_order.map((id, i) => {
              const char = characters.find((c) => c.id === id);
              return (
                <li
                  key={id}
                  className={`text-xs px-1 rounded ${
                    i === current_turn_index % turn_order.length
                      ? "bg-yellow-700 text-white"
                      : "text-gray-400"
                  }`}
                >
                  {i + 1}. {char?.name ?? id}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {gameState.combat_pressure && (
        <div
          data-testid="hard-mode-panel"
          className={`mt-3 p-2 rounded border text-xs ${
            PRESSURE_BG[gameState.combat_pressure.level]
          }`}
        >
          <div className="text-gray-500 uppercase tracking-wide mb-1">
            {t("room.hardMode.title")}
          </div>
          <div
            data-testid="hard-mode-level"
            className={`font-semibold mb-1 ${
              PRESSURE_TEXT[gameState.combat_pressure.level]
            }`}
          >
            {t(`room.hardMode.level.${gameState.combat_pressure.level}`)}
          </div>
          <div
            data-testid="hard-mode-zero-rounds"
            className="text-gray-400"
          >
            {t("room.hardMode.zeroRounds", {
              n: gameState.combat_pressure.zero_damage_rounds,
            })}
          </div>
        </div>
      )}
    </aside>
  );
}
