import { Stage, Layer, Rect, Line, Circle, Text, Group } from "react-konva";
import { useGameStore, useUIStore } from "../../stores";
import type { Character } from "../../types";

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

interface Props {
  onCharRightClick: (charId: string, pos: { x: number; y: number }) => void;
}

export default function GameMap({ onCharRightClick }: Props) {
  const { gameState } = useGameStore();
  const { mapZoom, selectedCharId, setSelectedChar } = useUIStore();

  if (!gameState) {
    return (
      <div className="flex-1 bg-gray-800 flex items-center justify-center text-gray-500">
        マップデータなし
      </div>
    );
  }

  const { map_size, characters, obstacles, turn_order, current_turn_index } =
    gameState;
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

  return (
    <div className="flex-1 overflow-auto bg-gray-800 flex items-center justify-center">
      <Stage width={width} height={height}>
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
        </Layer>
      </Stage>
    </div>
  );
}
