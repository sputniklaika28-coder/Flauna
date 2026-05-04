import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Text } from "react-konva";
import type Konva from "konva";
import { useGameStore, useUIStore } from "../../stores";
import type { DamageEvent } from "../../stores/uiStore";

const DURATION_MS = 900;

interface SinglePopupProps {
  event: DamageEvent;
  cellSize: number;
}

function SinglePopup({ event, cellSize }: SinglePopupProps) {
  const removeDamageEvent = useUIStore((s) => s.removeDamageEvent);
  const textRef = useRef<Konva.Text>(null);
  const startTime = useRef(Date.now());

  const centerX = event.gridX * cellSize + cellSize / 2;
  const centerY = event.gridY * cellSize;

  useEffect(() => {
    const node = textRef.current;
    if (!node) return;

    const frame = () => {
      const elapsed = Date.now() - startTime.current;
      const t = Math.min(elapsed / DURATION_MS, 1);
      node.y(centerY - t * cellSize * 1.2);
      node.opacity(1 - t);
      node.getLayer()?.batchDraw();

      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        removeDamageEvent(event.id);
      }
    };
    const raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [event.id, centerY, cellSize, removeDamageEvent]);

  return (
    <Text
      ref={textRef}
      x={centerX - 20}
      y={centerY}
      width={40}
      text={`-${event.amount}`}
      fontSize={Math.max(12, cellSize * 0.35)}
      fontStyle="bold"
      fill="#f87171"
      align="center"
      listening={false}
    />
  );
}

interface Props {
  cellSize: number;
}

export default function DamagePopups({ cellSize }: Props) {
  const damageEvents = useUIStore((s) => s.damageEvents);
  return (
    <>
      {damageEvents.map((ev) => (
        <SinglePopup key={ev.id} event={ev} cellSize={cellSize} />
      ))}
    </>
  );
}

/**
 * §17 a11y: parallel DOM live region so screen-reader users hear damage that
 * is otherwise rendered only inside the Konva stage. Mounted by GameMap
 * outside the aria-hidden Stage.
 */
export function DamageAnnouncements() {
  const { t } = useTranslation();
  const damageEvents = useUIStore((s) => s.damageEvents);
  const characters = useGameStore((s) => s.gameState?.characters ?? null);
  return (
    <ul
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      aria-label={t("room.map.damageRegion")}
      className="sr-only"
      data-testid="game-map-damage-log"
    >
      {damageEvents.map((ev) => {
        const name =
          characters?.find((c) => c.id === ev.charId)?.name ?? ev.charId;
        return (
          <li
            key={ev.id}
            data-testid={`game-map-damage-${ev.id}`}
          >
            {t("room.map.damageItem", { name, amount: ev.amount })}
          </li>
        );
      })}
    </ul>
  );
}
