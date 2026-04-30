import { useTranslation } from "react-i18next";
import { useGameStore } from "../../stores";
import { LanguageSwitcher } from "../common";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-500",
  CONNECTING: "bg-yellow-400",
  AUTHENTICATING: "bg-yellow-400",
  DISCONNECTED: "bg-red-500",
  SESSION_LOST: "bg-red-700",
};

export default function Header() {
  const { t } = useTranslation();
  const { gameState, connectionStatus, myPlayerId } = useGameStore();

  const phaseKey = gameState
    ? (`room.phase.${gameState.phase}` as const)
    : null;

  const myPc = gameState?.characters.find(
    (c) => c.player_id === myPlayerId && c.faction === "pc",
  );
  const katashiro = myPc?.inventory["katashiro"] ?? null;
  const showMp = !!myPc && myPc.max_mp > 0;

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-gray-900 text-white text-sm">
      <span className="font-bold">{t("app.name")}</span>

      <div className="flex items-center gap-3">
        {gameState && (
          <>
            <span>{t("room.round", { n: gameState.round_number })}</span>
            <span className="text-gray-400">
              {phaseKey ? t(phaseKey) : ""}
            </span>
            {showMp && myPc && (
              <span
                className="text-purple-300"
                title={t("room.hud.mpLabel", {
                  current: myPc.mp,
                  max: myPc.max_mp,
                })}
                data-testid="hud-mp"
              >
                {t("room.hud.mpLabel", {
                  current: myPc.mp,
                  max: myPc.max_mp,
                })}
              </span>
            )}
            {katashiro !== null && (
              <span
                className="text-amber-300"
                title={t("room.hud.katashiro")}
                data-testid="hud-katashiro"
              >
                {t("room.hud.katashiroLabel", { n: katashiro })}
              </span>
            )}
            <span className="text-gray-500 font-mono text-xs">
              {gameState.room_id}
            </span>
          </>
        )}
        <span
          className={`w-2 h-2 rounded-full ${STATUS_COLORS[connectionStatus] ?? "bg-gray-500"}`}
          title={connectionStatus}
        />
        <span className="text-gray-400">
          {connectionStatus === "ACTIVE"
            ? t("room.connected")
            : t("room.connecting")}
        </span>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
