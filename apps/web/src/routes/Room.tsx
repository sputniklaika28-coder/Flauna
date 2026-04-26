import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>();
  const { t } = useTranslation();

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-bold">{t("app.name")}</h1>
      <p>
        {t("room.connecting")} room: <code>{roomId}</code>
      </p>
    </main>
  );
}
