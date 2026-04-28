import { useCallback, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { nanoid } from "nanoid";
import { TacexWebSocket } from "../services/websocket";
import { joinRoom } from "../services/api";
import {
  useGameStore,
  useChatStore,
  useUIStore,
  usePendingStore,
} from "../stores";
import { Header, SideMenu } from "../components/layout";
import { ChatPanel } from "../components/chat";
import { GameMap, ContextMenu } from "../components/map";
import { QuickActionBar } from "../components/action";
import { EvasionDialog, CombatResultModal } from "../components/dialogs";
import type { GameState, EvasionPending } from "../types";
import type { ServerMessage } from "@flauna/ws-schema";

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();

  const {
    gameState,
    applyStateFull,
    setConnectionStatus,
    setLastSeenEventId,
    setAuth,
    myPlayerId,
    lastSeenEventId,
  } = useGameStore();
  const { addEntry, updateLastNarrative } = useChatStore();
  const { openContextMenu, addDamageEvent, setCombatResult } = useUIStore();
  const { setEvasionRequest } = usePendingStore();

  // Track previous HP values to detect damage for popups
  const prevHpRef = useRef<Record<string, number>>({});

  const wsRef = useRef<TacexWebSocket | null>(null);

  const handleMessage = useCallback(
    (data: unknown) => {
      const msg = data as ServerMessage;
      if (!msg || typeof msg !== "object" || !("type" in msg)) return;

      if ("event_id" in msg && typeof msg.event_id === "number") {
        setLastSeenEventId(msg.event_id);
      }

      switch (msg.type) {
        case "session_restore": {
          const state = msg.current_state as unknown as GameState;
          applyStateFull(state);
          setConnectionStatus("ACTIVE");
          addEntry("system", "セッション復元");
          // Seed initial HP tracking
          const hpMap: Record<string, number> = {};
          state.characters.forEach((c) => { hpMap[c.id] = c.hp; });
          prevHpRef.current = hpMap;
          break;
        }
        case "state_full": {
          const state = msg.state as unknown as GameState;

          // Detect HP decreases → emit damage popups
          state.characters.forEach((char) => {
            const prevHp = prevHpRef.current[char.id];
            if (prevHp !== undefined && char.hp < prevHp) {
              addDamageEvent({
                id: nanoid(),
                charId: char.id,
                amount: prevHp - char.hp,
                gridX: char.position[0],
                gridY: char.position[1],
              });
            }
          });
          // Update HP map
          const hpMap: Record<string, number> = {};
          state.characters.forEach((c) => { hpMap[c.id] = c.hp; });
          prevHpRef.current = hpMap;

          applyStateFull(state);
          setConnectionStatus("ACTIVE");
          break;
        }
        case "state_update": {
          // Phase 3+: incremental JSON patch — ignored until then
          break;
        }
        case "gm_narrative": {
          updateLastNarrative(msg.text, msg.is_streaming ?? false);
          break;
        }
        case "event": {
          if (msg.event_name === "combat_ended") {
            const outcome = (msg.payload as { outcome?: string }).outcome;
            if (outcome === "victory" || outcome === "defeat") {
              setCombatResult(outcome);
              addEntry("system", outcome === "victory" ? "戦闘終了: 勝利！" : "戦闘終了: 敗北…");
            }
          } else {
            addEntry("system", `[${msg.event_name}]`);
          }
          break;
        }
        case "ai_thinking": {
          addEntry("system", `GM: ${msg.stage}…`);
          break;
        }
        case "evade_required": {
          const req: EvasionPending = {
            pending_id: msg.pending_id,
            attacker_id: msg.attacker_id,
            target_id: msg.target_id,
            deadline_seconds: msg.deadline_seconds,
          };
          setEvasionRequest(req);
          break;
        }
        case "ai_fallback_notice": {
          addEntry("system", `[AI fallback] ${msg.reason}`);
          break;
        }
        case "session_lost": {
          setConnectionStatus("SESSION_LOST");
          addEntry("system", `セッション切断: ${msg.reason}`);
          break;
        }
        case "error": {
          addEntry("system", `エラー: ${msg.code} — ${msg.message}`);
          break;
        }
      }
    },
    [
      applyStateFull,
      setConnectionStatus,
      addEntry,
      updateLastNarrative,
      setEvasionRequest,
      setLastSeenEventId,
      addDamageEvent,
      setCombatResult,
    ],
  );

  useEffect(() => {
    if (!roomId) return;

    (async () => {
      try {
        const joinResp = await joinRoom(roomId, { player_name: "プレイヤー" });
        setAuth(joinResp.player_id, joinResp.player_token);

        const wsUrl = `ws://${window.location.host}/room/${roomId}`;
        const ws = new TacexWebSocket(wsUrl, handleMessage, (status) => {
          if (status === "connected") {
            ws.send({
              action: "join_room",
              player_id: joinResp.player_id,
              room_id: roomId,
              auth_token: joinResp.player_token,
              last_seen_event_id: lastSeenEventId,
            });
            setConnectionStatus("AUTHENTICATING");
          } else if (status === "disconnected") {
            setConnectionStatus("DISCONNECTED");
          } else {
            setConnectionStatus("CONNECTING");
          }
        });
        wsRef.current = ws;
        ws.connect();
      } catch {
        navigate("/");
      }
    })();

    return () => {
      wsRef.current?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId]);

  const sendWs = useCallback((payload: unknown) => {
    wsRef.current?.send(payload);
  }, []);

  const handleEndTurn = useCallback(() => {
    if (!gameState || !myPlayerId) return;
    sendWs({
      action: "submit_turn_action",
      player_id: myPlayerId,
      room_id: gameState.room_id,
      client_request_id: nanoid(),
      expected_version: gameState.version,
      turn_action: { end_turn: true },
    });
  }, [gameState, myPlayerId, sendWs]);

  const handleSendStatement = useCallback(
    (text: string) => {
      if (!gameState || !myPlayerId) return;
      sendWs({
        action: "player_statement",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        text,
      });
      addEntry("player_statement", text);
    },
    [gameState, myPlayerId, sendWs, addEntry],
  );

  const handleSubmitEvasion = useCallback(
    (pendingId: string, diceResult: number) => {
      if (!gameState || !myPlayerId) return;
      sendWs({
        action: "submit_evasion",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        pending_id: pendingId,
        dice_result: diceResult,
      });
      setEvasionRequest(null);
    },
    [gameState, myPlayerId, sendWs, setEvasionRequest],
  );

  const handleAttack = useCallback(
    (targetId: string) => {
      if (!gameState || !myPlayerId) return;
      const myChar = gameState.characters.find(
        (c) => c.player_id === myPlayerId,
      );
      if (!myChar) return;
      const weaponId = myChar.equipped_weapons[0] ?? "default";
      sendWs({
        action: "submit_turn_action",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        expected_version: gameState.version,
        turn_action: {
          main_action: {
            type: "melee_attack",
            weapon_id: weaponId,
            targets: [targetId],
            style: "none",
            dice_distribution: [],
          },
        },
      });
    },
    [gameState, myPlayerId, sendWs],
  );

  const handleCharRightClick = useCallback(
    (charId: string, pos: { x: number; y: number }) => {
      openContextMenu(charId, pos);
    },
    [openContextMenu],
  );

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white overflow-hidden">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <SideMenu />

        <div className="flex flex-col flex-1 overflow-hidden">
          <GameMap onCharRightClick={handleCharRightClick} />
          <QuickActionBar onEndTurn={handleEndTurn} />
        </div>

        <ChatPanel onSendStatement={handleSendStatement} />
      </div>

      <ContextMenu onAttack={handleAttack} />
      <EvasionDialog onSubmit={handleSubmitEvasion} />
      <CombatResultModal onBackToLobby={() => navigate("/")} />
    </div>
  );
}
