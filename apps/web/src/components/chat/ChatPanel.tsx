import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useChatStore, useGameStore, useUIStore } from "../../stores";
import type { ChatEntry } from "../../types";

function EntryRow({ entry }: { entry: ChatEntry }) {
  const prefix =
    entry.kind === "gm_narrative"
      ? "GM"
      : entry.kind === "system"
        ? "System"
        : "You";
  const color =
    entry.kind === "gm_narrative"
      ? "text-purple-300"
      : entry.kind === "system"
        ? "text-gray-400"
        : "text-blue-300";

  return (
    <div className="mb-2 text-sm">
      <span className={`font-semibold ${color}`}>{prefix}: </span>
      <span className="text-gray-100">{entry.text}</span>
      {entry.isStreaming && (
        <span className="animate-pulse text-gray-500 ml-1">…</span>
      )}
    </div>
  );
}

interface Props {
  onSendStatement: (text: string) => void;
}

export default function ChatPanel({ onSendStatement }: Props) {
  const { t } = useTranslation();
  const entries = useChatStore((s) => s.entries);
  const { gameState } = useGameStore();
  const chatPanelOpen = useUIStore((s) => s.chatPanelOpen);
  const closeMobilePanels = useUIStore((s) => s.closeMobilePanels);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState("");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !gameState) return;
    onSendStatement(text);
    setInput("");
  };

  return (
    <>
      {chatPanelOpen && (
        <button
          type="button"
          aria-label={t("room.mobile.closeChatPanel")}
          onClick={closeMobilePanels}
          className="lg:hidden fixed inset-0 z-30 bg-black/50"
          data-testid="chatpanel-backdrop"
        />
      )}
      <div
        data-testid="chatpanel"
        className={`w-64 bg-gray-900 text-white flex flex-col flex-shrink-0
          lg:relative lg:translate-x-0 lg:flex
          fixed inset-y-0 right-0 z-40 transition-transform
          ${chatPanelOpen ? "translate-x-0" : "translate-x-full"}
          lg:transform-none`}
      >
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {entries.map((e) => (
          <EntryRow key={e.id} entry={e} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-700 p-2 flex gap-2">
        <input
          className="flex-1 bg-gray-800 rounded px-2 py-1 text-sm text-white placeholder-gray-500 outline-none"
          placeholder={t("room.messagePlaceholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button
          onClick={handleSend}
          className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
        >
          {t("room.send")}
        </button>
      </div>
      </div>
    </>
  );
}
