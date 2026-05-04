import { Stage, Layer, Rect, Line, Circle, Text, Group } from "react-konva";
import { useTranslation } from "react-i18next";
import { useGameStore, useUIStore } from "../../stores";
import type {
  BarrierEffect,
  Character,
  MapObject,
  Pillar,
  Wire,
} from "../../types";
import DamagePopups, { DamageAnnouncements } from "./DamagePopup";

const FACTION_COLORS: Record<string, string> = {
  pc: "#3b82f6",
  enemy: "#ef4444",
  neutral: "#6b7280",
};

function CharToken({
  char,
  cellSize,
  isCurrentActor,
  isSelected,
  onClick,
  onContextMenu,
}: {
  char: Character;
  cellSize: number;
  isCurrentActor: boolean;
  isSelected: boolean;
  onClick: () => void;
  onContextMenu: (pos: { x: number; y: number }) => void;
}) {
  const [cx, cy] = char.position;
  const x = cx * cellSize + cellSize / 2;
  const y = cy * cellSize + cellSize / 2;
  const r = cellSize * 0.4;
  const color = FACTION_COLORS[char.faction] ?? "#9ca3af";
  const hpPct = char.max_hp > 0 ? char.hp / char.max_hp : 0;

  return (
    <Group
      x={x}
      y={y}
      onClick={onClick}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        const stage = e.target.getStage();
        const pos = stage?.getPointerPosition() ?? { x: 0, y: 0 };
        onContextMenu(pos);
      }}
    >
      {/* selection / current-actor ring */}
      {(isCurrentActor || isSelected) && (
        <Circle
          radius={r + 3}
          stroke={isCurrentActor ? "#facc15" : "#60a5fa"}
          strokeWidth={2}
          fill="transparent"
        />
      )}
      {/* token body */}
      <Circle radius={r} fill={char.hp <= 0 ? "#374151" : color} />
      {/* HP arc — simple bar below token */}
      <Rect
        x={-r}
        y={r + 3}
        width={r * 2}
        height={3}
        fill="#374151"
        cornerRadius={1}
      />
      <Rect
        x={-r}
        y={r + 3}
        width={r * 2 * hpPct}
        height={3}
        fill="#22c55e"
        cornerRadius={1}
      />
      {/* name */}
      <Text
        text={char.name.slice(0, 4)}
        fontSize={Math.max(8, cellSize * 0.22)}
        fill="white"
        align="center"
        verticalAlign="middle"
        offsetX={(r * 2) / 2}
        offsetY={Math.max(8, cellSize * 0.22) / 2 - 1}
        width={r * 2}
      />
    </Group>
  );
}

const BARRIER_COLORS: Record<BarrierEffect, string> = {
  barrier_wall: "#a78bfa",
  armor_dissolve: "#f97316",
  evasion_block: "#ef4444",
  attack_opportunity: "#22d3ee",
};

function PillarMark({
  pillar,
  cellSize,
}: {
  pillar: Pillar;
  cellSize: number;
}) {
  const [px, py] = pillar.position;
  const x = px * cellSize + cellSize / 2;
  const y = py * cellSize + cellSize / 2;
  const r = cellSize * 0.18;
  const color = pillar.is_active ? "#c4b5fd" : "#6b7280";
  return (
    <Group x={x} y={y}>
      <Rect
        x={-r}
        y={-r}
        width={r * 2}
        height={r * 2}
        rotation={45}
        fill={color}
        stroke="#1e1b4b"
        strokeWidth={1}
      />
    </Group>
  );
}

function WireLine({
  wire,
  pillars,
  cellSize,
  barrierEffect,
}: {
  wire: Wire;
  pillars: Pillar[];
  cellSize: number;
  barrierEffect: BarrierEffect | null;
}) {
  const a = pillars.find((p) => p.id === wire.pillar_a_id);
  const b = pillars.find((p) => p.id === wire.pillar_b_id);
  if (!a || !b) return null;
  const [ax, ay] = a.position;
  const [bx, by] = b.position;
  const x1 = ax * cellSize + cellSize / 2;
  const y1 = ay * cellSize + cellSize / 2;
  const x2 = bx * cellSize + cellSize / 2;
  const y2 = by * cellSize + cellSize / 2;
  if (barrierEffect) {
    const color = BARRIER_COLORS[barrierEffect];
    return (
      <>
        <Line
          points={[x1, y1, x2, y2]}
          stroke={color}
          strokeWidth={Math.max(6, cellSize * 0.2)}
          opacity={0.35}
          lineCap="round"
        />
        <Line
          points={[x1, y1, x2, y2]}
          stroke={color}
          strokeWidth={1.5}
          opacity={0.9}
        />
      </>
    );
  }
  return (
    <Line
      points={[x1, y1, x2, y2]}
      stroke="#9ca3af"
      strokeWidth={1}
      dash={[4, 4]}
      opacity={0.6}
    />
  );
}

function ObjectMark({
  obj,
  cellSize,
}: {
  obj: MapObject;
  cellSize: number;
}) {
  const [ox, oy] = obj.position;
  const inset = 3;
  return (
    <Group>
      <Rect
        x={ox * cellSize + inset}
        y={oy * cellSize + inset}
        width={cellSize - inset * 2}
        height={cellSize - inset * 2}
        fill="#854d0e"
        stroke="#fbbf24"
        strokeWidth={1}
        cornerRadius={2}
      />
      {obj.strength > 0 && (
        <Text
          x={ox * cellSize}
          y={oy * cellSize + cellSize - inset - 10}
          width={cellSize}
          align="center"
          text={`◆${obj.strength}`}
          fontSize={Math.max(8, cellSize * 0.22)}
          fill="#fde68a"
        />
      )}
    </Group>
  );
}

interface Props {
  onCharRightClick: (charId: string, pos: { x: number; y: number }) => void;
}

export default function GameMap({ onCharRightClick }: Props) {
  const { t } = useTranslation();
  const { gameState } = useGameStore();
  const { mapZoom, selectedCharId, setSelectedChar } = useUIStore();

  if (!gameState) {
    return (
      <div
        role="region"
        aria-label={t("room.map.region")}
        className="flex-1 bg-gray-800 flex items-center justify-center text-gray-500"
        data-testid="game-map-empty"
      >
        {t("room.map.empty")}
      </div>
    );
  }

  const {
    map_size,
    characters,
    obstacles,
    turn_order,
    current_turn_index,
    pillars = [],
    wires = [],
    barriers = [],
    objects = [],
  } = gameState;
  const [cols, rows] = map_size;
  const cellSize = mapZoom;
  const width = cols * cellSize;
  const height = rows * cellSize;
  const currentActorId =
    turn_order.length > 0
      ? turn_order[current_turn_index % turn_order.length]
      : null;

  // grid lines
  const gridLines: React.ReactElement[] = [];
  for (let c = 0; c <= cols; c++) {
    gridLines.push(
      <Line
        key={`v${c}`}
        points={[c * cellSize, 0, c * cellSize, height]}
        stroke="#374151"
        strokeWidth={0.5}
      />,
    );
  }
  for (let r = 0; r <= rows; r++) {
    gridLines.push(
      <Line
        key={`h${r}`}
        points={[0, r * cellSize, width, r * cellSize]}
        stroke="#374151"
        strokeWidth={0.5}
      />,
    );
  }

  const currentActor = currentActorId
    ? characters.find((c) => c.id === currentActorId) ?? null
    : null;

  const factionLabel = (faction: string): string => {
    const key = `room.map.faction.${faction}`;
    const label = t(key);
    return label === key ? faction : label;
  };

  return (
    <div
      role="region"
      aria-label={t("room.map.region")}
      data-testid="game-map"
      className="flex-1 overflow-auto bg-gray-800 flex items-center justify-center"
    >
      {/* §17 a11y: parallel DOM surface so keyboard / screen-reader users can
          inspect and act on the otherwise canvas-only map. */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="game-map-current-actor"
      >
        {currentActor
          ? t("room.map.currentActor", { name: currentActor.name })
          : t("room.map.noCurrentActor")}
      </div>
      <ul
        role="list"
        aria-label={t("room.map.charList")}
        className="sr-only"
        data-testid="game-map-char-list"
      >
        {characters.map((char) => {
          const isCurrent = char.id === currentActorId;
          const isSelected = char.id === selectedCharId;
          const summary = t("room.map.charSummary", {
            name: char.name,
            faction: factionLabel(char.faction),
            hp: char.hp,
            maxHp: char.max_hp,
            x: char.position[0],
            y: char.position[1],
          });
          const stateBits: string[] = [];
          if (isCurrent) stateBits.push(t("room.map.charCurrent"));
          if (char.hp <= 0) stateBits.push(t("room.map.charDown"));
          const fullSummary = stateBits.length
            ? `${summary} · ${stateBits.join(" · ")}`
            : summary;
          return (
            <li
              key={char.id}
              data-testid={`game-map-char-${char.id}`}
              {...(isCurrent ? { "aria-current": "true" } : {})}
            >
              <button
                type="button"
                aria-pressed={isSelected}
                aria-label={
                  isSelected
                    ? t("room.map.deselectChar", { name: char.name })
                    : t("room.map.selectChar", { name: char.name })
                }
                data-testid={`game-map-select-${char.id}`}
                onClick={() =>
                  setSelectedChar(isSelected ? null : char.id)
                }
              >
                {fullSummary}
              </button>
              <button
                type="button"
                aria-haspopup="menu"
                aria-label={t("room.map.openCharActions", {
                  name: char.name,
                })}
                data-testid={`game-map-actions-${char.id}`}
                onClick={(e) => {
                  const rect = (
                    e.currentTarget as HTMLButtonElement
                  ).getBoundingClientRect();
                  onCharRightClick(char.id, {
                    x: rect.left,
                    y: rect.bottom,
                  });
                }}
              >
                {t("room.map.openCharActions", { name: char.name })}
              </button>
            </li>
          );
        })}
      </ul>
      <DamageAnnouncements />
      <Stage width={width} height={height} aria-hidden="true">
        <Layer>
          {/* background */}
          <Rect x={0} y={0} width={width} height={height} fill="#1f2937" />

          {/* grid */}
          {gridLines}

          {/* obstacles */}
          {obstacles.map(([ox, oy], i) => (
            <Rect
              key={i}
              x={ox * cellSize + 1}
              y={oy * cellSize + 1}
              width={cellSize - 2}
              height={cellSize - 2}
              fill="#4b5563"
              cornerRadius={2}
            />
          ))}

          {/* destructible objects */}
          {objects.map((obj) => (
            <ObjectMark key={obj.id} obj={obj} cellSize={cellSize} />
          ))}

          {/* wires + barriers (drawn under pillars/characters) */}
          {wires.map((wire) => {
            const barrier = barriers.find(
              (b) => b.wire_id === wire.id && b.is_active,
            );
            return (
              <WireLine
                key={wire.id}
                wire={wire}
                pillars={pillars}
                cellSize={cellSize}
                barrierEffect={barrier?.effect ?? null}
              />
            );
          })}

          {/* pillars */}
          {pillars.map((pillar) => (
            <PillarMark
              key={pillar.id}
              pillar={pillar}
              cellSize={cellSize}
            />
          ))}

          {/* characters */}
          {characters.map((char) => (
            <CharToken
              key={char.id}
              char={char}
              cellSize={cellSize}
              isCurrentActor={char.id === currentActorId}
              isSelected={char.id === selectedCharId}
              onClick={() =>
                setSelectedChar(
                  char.id === selectedCharId ? null : char.id,
                )
              }
              onContextMenu={(pos) => onCharRightClick(char.id, pos)}
            />
          ))}

          {/* damage popups */}
          <DamagePopups cellSize={cellSize} />
        </Layer>
      </Stage>
    </div>
  );
}
