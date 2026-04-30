import { useCallback, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { nanoid } from "nanoid";
import { TacexWebSocket } from "../services/websocket";
import { joinRoom } from "../services/api";
import { playSe } from "../services/audio";
import {
  useGameStore,
  useChatStore,
  useUIStore,
  usePendingStore,
} from "../stores";
import { Header, SideMenu } from "../components/layout";
import { ChatPanel } from "../components/chat";
import { GameMap, ContextMenu } from "../components/map";
import { QuickActionBar, ActionDetailModal } from "../components/action";
import {
  EvasionDialog,
  CombatResultModal,
  DeathAvoidanceDialog,
  CastArtModal,
  CastArtCutscene,
  AssessmentScreen,
} from "../components/dialogs";
import type {
  GameState,
  EvasionPending,
  DeathAvoidancePending,
  DeathAvoidanceChoice,
  CastArtPayload,
} from "../types";
import type { ServerMessage } from "@flauna/ws-schema";

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

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
  const {
    openContextMenu,
    openActionDetail,
    openCastArt,
    triggerCastArtCutscene,
    addDamageEvent,
    setCombatResult,
  } = useUIStore();
  const { setEvasionRequest, setDeathAvoidanceRequest } = usePendingStore();

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
          let anyDamage = false;
          state.characters.forEach((char) => {
            const prevHp = prevHpRef.current[char.id];
            if (prevHp !== undefined && char.hp < prevHp) {
              anyDamage = true;
              addDamageEvent({
                id: nanoid(),
                charId: char.id,
                amount: prevHp - char.hp,
                gridX: char.position[0],
                gridY: char.position[1],
              });
            }
          });
          if (anyDamage) playSe("damage");
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
              playSe(outcome);
              addEntry("system", outcome === "victory" ? "戦闘終了: 勝利！" : "戦闘終了: 敗北…");
            }
          } else if (msg.event_name === "combat_pressure_escalated") {
            playSe("escalation");
            const lvl = (msg.payload as { level?: string }).level ?? "hard";
            const localized = t(`room.hardMode.level.${lvl}`, {
              defaultValue: lvl,
            });
            addEntry(
              "system",
              t("room.hardMode.escalated", { level: localized }),
            );
          } else if (msg.event_name === "art_cast") {
            const p = msg.payload as {
              art_name?: string;
              caster_id?: string;
            };
            if (p.art_name && p.caster_id) {
              const caster = useGameStore
                .getState()
                .gameState?.characters.find((c) => c.id === p.caster_id);
              triggerCastArtCutscene({
                id: nanoid(),
                artName: p.art_name,
                casterName: caster?.name ?? p.caster_id,
              });
              playSe("cast_art");
              addEntry("system", `『${p.art_name}』が放たれた！`);
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
        case "death_avoidance_required": {
          const daReq: DeathAvoidancePending = {
            pending_id: msg.pending_id,
            target_character_id: msg.target_character_id,
            target_player_id: msg.target_player_id,
            incoming_damage: msg.incoming_damage,
            damage_type: msg.damage_type,
            katashiro_required: msg.katashiro_required,
            katashiro_remaining: msg.katashiro_remaining,
            deadline_seconds: msg.deadline_seconds,
          };
          setDeathAvoidanceRequest(daReq);
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
      setDeathAvoidanceRequest,
      setLastSeenEventId,
      addDamageEvent,
      setCombatResult,
      triggerCastArtCutscene,
      t,
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

  const handleSubmitDeathAvoidance = useCallback(
    (pendingId: string, choice: DeathAvoidanceChoice) => {
      if (!gameState || !myPlayerId) return;
      sendWs({
        action: "submit_death_avoidance",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        pending_id: pendingId,
        choice,
      });
      setDeathAvoidanceRequest(null);
    },
    [gameState, myPlayerId, sendWs, setDeathAvoidanceRequest],
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

  const handleDetailAttack = useCallback(
    (targetId: string) => {
      openActionDetail(targetId);
    },
    [openActionDetail],
  );

  const handleDetailAttackSubmit = useCallback(
    (payload: {
      targetId: string;
      weaponId: string;
      style: string;
      moveMode: string;
      diceDistribution: number[];
    }) => {
      if (!gameState || !myPlayerId) return;
      const firstMove =
        payload.moveMode !== "normal"
          ? { path: [], mode: payload.moveMode }
          : undefined;
      sendWs({
        action: "submit_turn_action",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        expected_version: gameState.version,
        turn_action: {
          actor_id: gameState.characters.find((c) => c.player_id === myPlayerId)?.id ?? "",
          ...(firstMove ? { first_move: firstMove } : {}),
          main_action: {
            type: "melee_attack",
            weapon_id: payload.weaponId,
            targets: [payload.targetId],
            style: payload.style,
            dice_distribution: payload.diceDistribution,
          },
        },
      });
    },
    [gameState, myPlayerId, sendWs],
  );

  const handleOpenCastArt = useCallback(
    (targetId: string | null) => {
      openCastArt(targetId);
    },
    [openCastArt],
  );

  const handleSubmitCastArt = useCallback(
    (payload: CastArtPayload) => {
      if (!gameState || !myPlayerId) return;
      const myChar = gameState.characters.find(
        (c) => c.player_id === myPlayerId,
      );
      if (!myChar) return;
      sendWs({
        action: "submit_turn_action",
        player_id: myPlayerId,
        room_id: gameState.room_id,
        client_request_id: nanoid(),
        expected_version: gameState.version,
        turn_action: {
          actor_id: myChar.id,
          main_action: {
            type: "cast_art",
            art_name: payload.art_name,
            ...(payload.target ? { target: payload.target } : {}),
            ...(payload.center_position
              ? { center_position: payload.center_position }
              : {}),
          },
        },
      });
      triggerCastArtCutscene({
        id: nanoid(),
        artName: payload.art_name,
        casterName: myChar.name,
      });
      addEntry("system", `『${payload.art_name}』を発動！`);
    },
    [gameState, myPlayerId, sendWs, triggerCastArtCutscene, addEntry],
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

      <ContextMenu
        onAttack={handleAttack}
        onDetailAttack={handleDetailAttack}
        onCastArt={handleOpenCastArt}
      />
      <ActionDetailModal onSubmit={handleDetailAttackSubmit} />
      <CastArtModal onSubmit={handleSubmitCastArt} />
      <CastArtCutscene />
      <EvasionDialog onSubmit={handleSubmitEvasion} />
      <DeathAvoidanceDialog onSubmit={handleSubmitDeathAvoidance} />
      <CombatResultModal onBackToLobby={() => navigate("/")} />
      <AssessmentScreen onBackToLobby={() => navigate("/")} />
    </div>
  );
}
