import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useGameStore, useUIStore } from "../../stores";

interface Props {
  onAttack: (targetId: string) => void;
  onDetailAttack: (targetId: string) => void;
  onCastArt: (targetId: string) => void;
}

export default function ContextMenu({
  onAttack,
  onDetailAttack,
  onCastArt,
}: Props) {
  const { t } = useTranslation();
  const { contextMenuCharId, contextMenuPos, closeContextMenu } = useUIStore();
  const { gameState } = useGameStore();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        closeContextMenu();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [closeContextMenu]);

  if (!contextMenuCharId || !contextMenuPos) return null;

  const char = gameState?.characters.find((c) => c.id === contextMenuCharId);
  if (!char) return null;

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-gray-800 border border-gray-600 rounded shadow-lg text-white text-sm py-1 min-w-36"
      style={{ left: contextMenuPos.x, top: contextMenuPos.y }}
    >
      <div className="px-3 py-1 text-gray-400 font-semibold text-xs border-b border-gray-700">
        {char.name}
      </div>
      <button
        className="w-full text-left px-3 py-1.5 hover:bg-gray-700"
        onClick={() => {
          onAttack(contextMenuCharId);
          closeContextMenu();
        }}
      >
        {t("room.contextMenu.attack")}
      </button>
      <button
        className="w-full text-left px-3 py-1.5 hover:bg-gray-700 text-yellow-300"
        onClick={() => {
          onDetailAttack(contextMenuCharId);
          closeContextMenu();
        }}
      >
        {t("room.contextMenu.detailAttack")} ⚙
      </button>
      <button
        className="w-full text-left px-3 py-1.5 hover:bg-gray-700 text-purple-300"
        onClick={() => {
          onCastArt(contextMenuCharId);
          closeContextMenu();
        }}
        data-testid="ctx-cast-art"
      >
        {t("room.contextMenu.castArt")} ✦
      </button>
      <div className="border-t border-gray-700 my-0.5" />
      <button
        className="w-full text-left px-3 py-1.5 hover:bg-gray-700"
        onClick={closeContextMenu}
      >
        {t("room.contextMenu.detail")}
      </button>
    </div>
  );
}
