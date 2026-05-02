import { useTranslation } from "react-i18next";
import { useGameStore } from "../../stores";

interface Props {
  onBackToLobby: () => void;
}

export default function SessionLostScreen({ onBackToLobby }: Props) {
  const { t } = useTranslation();
  const { connectionStatus } = useGameStore();

  if (connectionStatus !== "SESSION_LOST") return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="session-lost-title"
      data-testid="session-lost-screen"
    >
      <div className="rounded-xl p-8 w-96 text-center shadow-2xl border-2 bg-gray-900 border-red-700">
        <div className="text-5xl mb-4 text-red-500">⚠</div>
        <h2
          id="session-lost-title"
          className="text-2xl font-bold mb-2 text-red-400"
        >
          {t("room.sessionLost.title")}
        </h2>
        <p className="text-gray-400 text-sm mb-6 whitespace-pre-line">
          {t("room.sessionLost.message")}
        </p>
        <button
          onClick={onBackToLobby}
          className="w-full bg-gray-700 hover:bg-gray-600 text-white rounded py-2 font-semibold"
        >
          {t("room.sessionLost.backToLobby")}
        </button>
      </div>
    </div>
  );
}
