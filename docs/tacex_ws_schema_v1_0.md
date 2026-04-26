# タクティカル祓魔師TRPG WebSocketメッセージスキーマ仕様 v1.0 (FINAL)

**最終更新**: 2026-04-25  
**ステータス**: 実装着手用最終版（Claude Code向け、両仕様書が共通参照する単一の真実）  
**ペア仕様書**: `tacex_gm_spec_v2_5_FINAL.md`, `tacex_web_spec_v1_1_FINAL.md`

---

## ⚠️ 本仕様書の位置づけ

レビュー指摘により、**バックエンドとフロントエンドの間の WebSocket メッセージスキーマは、両仕様書の暗黙の共有ではなく、明示的な単一の真実として本ファイルで定義する**。

両仕様書（バックエンド・フロントエンド）は本ファイルを参照する形で整合する。本ファイルが両者の唯一の通信契約である。

実装時には、本ファイルから TypeScript の型定義と Python の Pydantic モデルの両方を同期させること。

---

## 1. 共通基盤

### 1-1. 通信プロトコル

- WebSocket over TLS（`wss://`）必須
- JSON テキストメッセージのみ（バイナリは使わない）
- UTF-8 エンコード
- メッセージサイズ上限: 1MB（超過時はサーバー側で強制切断）

### 1-2. 接続URL

```
wss://server/room/{room_id}
```

### 1-3. メッセージ共通フォーマット

すべてのメッセージは `type` または `action` フィールドで種別を区別する。

**クライアント → サーバー**: `action` フィールドで種別を識別
**サーバー → クライアント**: `type` フィールドで種別を識別

### 1-4. 共通フィールド

| フィールド | 必須 | 説明 |
|---|---|---|
| client_request_id | クライアント送信時 | UUID（nanoid 推奨）。サーバー側で冪等処理に使用 |
| event_id | サーバー送信時 | ルーム内で単調増加する整数 |
| timestamp | サーバー送信時 | ISO 8601 UTC形式 |

---

## 2. 認証API（HTTP）

WebSocket 接続前の認証は HTTP API で行う。

### 2-1. ルーム作成

```
POST /api/v1/rooms

Request:
{
  "scenario_id": "first_mission",
  "player_name": "GM"
}

Response (200):
{
  "room_id": "room-abc123",
  "master_token": "eyJ...",
  "scenario_title": "最初の任務"
}
```

### 2-2. ルーム参加

```
POST /api/v1/rooms/{room_id}/join

Request:
{
  "player_name": "アリス"
}

Response (200):
{
  "player_id": "player-xyz",
  "player_token": "eyJ...",
  "room_info": {
    "room_id": "room-abc123",
    "title": "最初の任務"
  }
}

Response (404):
{
  "error": {
    "code": "ROOM_NOT_FOUND",
    "message": "指定されたルームが見つかりません"
  }
}
```

---

## 3. WebSocket メッセージ: クライアント → サーバー

### 3-1. join_room（接続時の最初のメッセージ）

```json
{
  "action": "join_room",
  "player_id": "player-xyz",
  "room_id": "room-abc123",
  "auth_token": "eyJ...",
  "last_seen_event_id": 0
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| action | "join_room" | ✓ | |
| player_id | string | ✓ | プレイヤー参加時に取得したID |
| room_id | string | ✓ | |
| auth_token | string | ✓ | プレイヤートークン |
| last_seen_event_id | integer | ✓ | 最後に受信したイベントID。初回接続時は 0 |

**サーバー応答**: `session_restore` または close code

### 3-2. submit_turn_action（行動宣言）

```json
{
  "action": "submit_turn_action",
  "player_id": "player-xyz",
  "room_id": "room-abc123",
  "client_request_id": "req-uuid-001",
  "expected_version": 42,
  "turn_action": {
    "actor_id": "alice",
    "first_move": {
      "path": [[5, 5], [6, 5], [7, 5]],
      "mode": "normal"
    },
    "main_action": {
      "type": "melee_attack",
      "weapon_id": "alice_chuukei_1",
      "style": "連撃",
      "additional_style": null,
      "dice_distribution": [3, 3],
      "targets": ["enemy1", "enemy1"]
    },
    "second_move": null,
    "sub_actions": []
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| action | "submit_turn_action" | ✓ | |
| player_id | string | ✓ | |
| room_id | string | ✓ | |
| client_request_id | string | ✓ | 冪等処理用 |
| expected_version | integer | ✓ | 送信時に把握している state.version |
| turn_action | TurnAction | ✓ | 後述 |

**TurnAction の構造:**

```typescript
interface TurnAction {
  actor_id: string;
  first_move: Movement | null;
  main_action: MainAction;        // discriminated union
  second_move: Movement | null;
  sub_actions: SubAction[];        // Phase 4 以降
}

interface Movement {
  path: [number, number][];        // [x, y] のリスト、始点は actor の現在位置
  mode: "normal" | "tactical_maneuver" | "attack_focus";
}

type MainAction =
  | MeleeAttack
  | RangedAttack
  | PegAttack
  | CastArt
  | DeployWire
  | DispelBarrier
  | UseItem
  | OtherAction
  | Skip;

interface MeleeAttack {
  type: "melee_attack";
  weapon_id: string;
  style: "none" | "連撃" | "精密攻撃" | "強攻撃" | "全力攻撃";
  additional_style: "両手利き" | null;
  dice_distribution: number[];     // 各攻撃へのダイス割り当て
  targets: string[];                // ターゲットID、dice_distribution と同じ長さ
}

interface RangedAttack {
  type: "ranged_attack";
  weapon_id: string;
  style: "none" | "2回射撃" | "連射" | "連射II" | "狙撃" | "抜き撃ち";
  additional_style: "両手利き" | null;
  dice_distribution: number[];
  targets: string[];
}

interface PegAttack {
  type: "peg_attack";
  attack_kind: "melee" | "ranged";
  target: string;
}

interface CastArt {
  type: "cast_art";
  art_name: "加護防壁" | "反閃歩法" | "霊力放出" | "霊弾発射" | "呪祝詛詞" | "式神使役";
  target: string | null;
  center_position: [number, number] | null;
  options: Record<string, unknown>;
}

interface DeployWire {
  type: "deploy_wire";
  pillar_id: string;
}

interface DispelBarrier {
  type: "dispel_barrier";
  barrier_id: string;
}

interface UseItem {
  type: "use_item";
  item_name: string;
  target: string | null;
  center_position: [number, number] | null;
}

interface OtherAction {
  type: "other_action";
  description: string;
  target_object_id: string | null;
}

interface Skip {
  type: "skip";
}

type SubAction = PlacePillar | ActivateBarrier | ConsumeKatashiroForMP;

interface PlacePillar {
  type: "place_pillar";
  position: [number, number];
}

interface ActivateBarrier {
  type: "activate_barrier";
  pillar_id: string;
  effect: "barrier_wall" | "armor_dissolve" | "evasion_block" | "attack_opportunity";
}

interface ConsumeKatashiroForMP {
  type: "consume_katashiro_mp";
}
```

**バリデーション**:
- `expected_version` がサーバーの現在 `version` と一致しない場合は `VERSION_MISMATCH` エラー
- `turn_action` のスキーマ違反（target数とdice数の不一致等）は `INVALID_DICE_DISTRIBUTION` 等のエラー
- 移動経路の不正は `INVALID_PATH`
- 距離・射線等のセマンティック違反は適切なエラーコード

**サーバー応答**: 
- 成功時: state_update イベントが流れ、最終的に gm_narrative
- 失敗時: error メッセージ

### 3-3. submit_evasion（回避応答）

```json
{
  "action": "submit_evasion",
  "player_id": "player-xyz",
  "room_id": "room-abc123",
  "client_request_id": "req-uuid-002",
  "pending_id": "pending-uuid",
  "mode": "individual",
  "dice_assignments": [3, 0]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| action | "submit_evasion" | ✓ | |
| pending_id | string | ✓ | EvasionRequest の pending_id |
| mode | "individual" \| "batch" | ✓ | individual: 各攻撃に個別配分、batch: まとめて回避 |
| dice_assignments | number[] | ✓ | individual時: 各攻撃の配分。batch時: 単一値 [N] |

### 3-4. submit_death_avoidance（死亡回避応答、Phase 4以降）

```json
{
  "action": "submit_death_avoidance",
  "player_id": "player-xyz",
  "room_id": "room-abc123",
  "client_request_id": "req-uuid-003",
  "pending_id": "pending-uuid",
  "choice": "avoid_death"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| choice | "avoid_death" \| "respawn" \| "accept_death" | ✓ | |

### 3-5. player_statement（自由発言）

```json
{
  "action": "player_statement",
  "player_id": "player-xyz",
  "room_id": "room-abc123",
  "client_request_id": "req-uuid-004",
  "text": "祠の周りに何か手がかりはないか調べる",
  "channel": "all"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| text | string | ✓ | 発言内容、最大1000文字 |
| channel | "all" \| "party" \| string | – | string は 秘話相手の player_id（Phase 7以降）。デフォルト "all" |

---

## 4. WebSocket メッセージ: サーバー → クライアント

### 4-1. session_restore（join_room への応答 / 再接続時）

```json
{
  "type": "session_restore",
  "event_id": 145,
  "timestamp": "2026-04-25T12:00:00Z",
  "mode": "incremental",
  "current_state": { /* GameState 全量 */ },
  "missed_events": [
    { "event_id": 143, "type": "...", "payload": {} }
  ],
  "missed_event_count": 2,
  "pending_for_you": [
    { /* PendingAction */ }
  ],
  "expired_pending": [
    {
      "pending_id": "pending-uuid",
      "type": "evasion_request",
      "auto_choice": "0_dice_evasion",
      "reason": "timeout_during_disconnection"
    }
  ]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| mode | "incremental" \| "full_sync" | ✓ | full_sync は missed_events を送らず最新状態のみ |
| current_state | GameState | ✓ | 後述 |
| missed_events | GameEvent[] | ✓ | mode="full_sync" 時は空配列 |
| missed_event_count | integer | ✓ | 実際に発生した件数（送信件数とは異なる場合あり） |
| pending_for_you | PendingAction[] | ✓ | 自分宛の有効な保留中アクション |
| expired_pending | ExpiredPending[] | ✓ | 切断中に自動処理された保留中アクション |

### 4-2. state_update（差分更新）

```json
{
  "type": "state_update",
  "event_id": 146,
  "timestamp": "2026-04-25T12:00:01Z",
  "version": 43,
  "patch": [
    { "op": "replace", "path": "/characters/0/hp", "value": 5 }
  ]
}
```

JSON Patch (RFC 6902) 形式の差分。

### 4-3. state_full（全量更新）

```json
{
  "type": "state_full",
  "event_id": 147,
  "timestamp": "2026-04-25T12:00:02Z",
  "version": 44,
  "state": { /* GameState 全量 */ }
}
```

差分が複雑になる場合や、再接続時に使用。

### 4-4. gm_narrative（GM描写）

```json
{
  "type": "gm_narrative",
  "event_id": 148,
  "timestamp": "2026-04-25T12:00:03Z",
  "text": "アリスの祓串が空を切り、二度の閃光を放つ。",
  "turn_id": "turn-uuid",
  "speaker_character_id": null,
  "fallback_level": "none"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| text | string | ✓ | 描写本文 |
| turn_id | string | – | 関連するターンの識別子 |
| speaker_character_id | string \| null | – | NPCの台詞を表現する場合のキャラID |
| fallback_level | "none" \| "minor" \| "major" | ✓ | AIフォールバックの段階 |

### 4-5. event（ゲームイベント）

```json
{
  "type": "event",
  "event_id": 149,
  "timestamp": "2026-04-25T12:00:04Z",
  "event_name": "attack_resolved",
  "payload": {
    "attacker_id": "alice",
    "target_id": "enemy1",
    "hit_successes": 4,
    "hit_threshold": 4,
    "evasion_successes": 1,
    "evasion_threshold": 4,
    "result": "evaded"
  },
  "affected_characters": ["alice", "enemy1"]
}
```

| event_name | 説明 |
|---|---|
| attack_resolved | 攻撃の解決完了 |
| damage_applied | ダメージ適用 |
| character_died | キャラクター死亡 |
| character_respawned | リスポーン（Phase 4） |
| barrier_deployed | 結界設置（Phase 4） |
| art_cast | 祓魔術発動（Phase 5） |
| combat_pressure_increased | 戦闘圧力上昇（Phase 6） |
| turn_started | ターン開始 |
| turn_ended | ターン終了 |
| round_started | ラウンド開始 |
| phase_changed | フェーズ遷移 |
| scenario_event_triggered | シナリオトリガー発火 |

### 4-6. ai_thinking（AI処理中通知）

```json
{
  "type": "ai_thinking",
  "event_id": 150,
  "timestamp": "2026-04-25T12:00:05Z",
  "stage": "deciding_action",
  "actor_id": "enemy1"
}
```

| stage | 説明 |
|---|---|
| deciding_action | AI Phase 1（行動決定中） |
| narrating | AI Phase 2（描写生成中） |

### 4-7. evade_required（回避要求）

```json
{
  "type": "evade_required",
  "event_id": 151,
  "timestamp": "2026-04-25T12:00:06Z",
  "payload": {
    "pending_id": "pending-uuid",
    "target_character_id": "alice",
    "incoming_attacks": [
      {
        "attacker_id": "enemy1",
        "attack_command_id": "attack-uuid-1",
        "successes": 3,
        "threshold": 4,
        "damage_formula": "1d6+1",
        "damage_type": "physical"
      }
    ],
    "can_batch": false,
    "max_evasion_dice": 5,
    "deadline_at": "2026-04-25T12:01:06Z"
  }
}
```

### 4-8. death_avoidance_required（死亡回避要求、Phase 4以降）

```json
{
  "type": "death_avoidance_required",
  "event_id": 152,
  "timestamp": "2026-04-25T12:00:07Z",
  "payload": {
    "pending_id": "pending-uuid",
    "target_character_id": "alice",
    "target_player_id": "player-xyz",
    "incoming_damage": 12,
    "damage_type": "physical",
    "katashiro_required": 2,
    "katashiro_remaining": 7,
    "deadline_at": "2026-04-25T12:01:07Z"
  }
}
```

### 4-9. input_timeout_warning（タイムアウト警告）

```json
{
  "type": "input_timeout_warning",
  "event_id": 153,
  "timestamp": "2026-04-25T12:00:30Z",
  "pending_id": "pending-uuid",
  "seconds_remaining": 30
}
```

30秒前と10秒前に送信。

### 4-10. pending_auto_resolved（自動処理通知、再接続時）

```json
{
  "type": "pending_auto_resolved",
  "event_id": 154,
  "timestamp": "2026-04-25T12:01:06Z",
  "pending_id": "pending-uuid",
  "reason": "timeout",
  "auto_choice": "0_dice_evasion"
}
```

| reason | 説明 |
|---|---|
| timeout | タイムアウト |
| timeout_during_disconnection | 切断中タイムアウト |
| cancelled | 攻撃元の状態変化等でキャンセル |

### 4-11. ai_fallback_notice（AIフォールバック通知）

```json
{
  "type": "ai_fallback_notice",
  "event_id": 155,
  "timestamp": "2026-04-25T12:00:08Z",
  "level": "major",
  "reason": "ai_max_retries",
  "message": "AI処理にエラーが発生したため、自動処理されました"
}
```

| level | 通知 |
|---|---|
| minor | UI内部ログのみ |
| major | プレイヤーにトースト表示 |

### 4-12. session_lost（セッション喪失）

```json
{
  "type": "session_lost",
  "event_id": 156,
  "timestamp": "2026-04-25T12:00:09Z",
  "reason": "server_restart",
  "message": "サーバーが再起動されました。新しいセッションを開始してください。"
}
```

| reason | close code |
|---|---|
| server_restart | 4002 |
| reconnect_timeout | 4001 |
| event_log_truncated | 4001 |

### 4-13. error（エラー応答）

```json
{
  "type": "error",
  "event_id": 157,
  "timestamp": "2026-04-25T12:00:10Z",
  "code": "VERSION_MISMATCH",
  "message": "状態が他のプレイヤーの行動で変化しました",
  "detail": {
    "current_version": 43,
    "expected_version": 42
  },
  "client_request_id": "req-uuid-001"
}
```

`client_request_id` を含めてどのリクエストへの応答かを明示。

---

## 5. データ型定義

### 5-1. GameState（受信時の構造）

クライアントは GameState を **読み取り専用** として扱う。書き込みはサーバー応答経由のみ。

```typescript
interface GameState {
  room_id: string;
  version: number;
  seed: number;
  phase: "briefing" | "exploration" | "combat" | "assessment";
  machine_state: "idle" | "resolving_action" | "awaiting_player_input" | "narrating" | "paused";
  turn_order: string[];
  current_turn_index: number;
  round_number: number;
  characters: Character[];
  map_size: [number, number];
  obstacles: [number, number][];
  objects: MapObject[];
  barriers: Barrier[];
  pillars: Pillar[];
  wires: Wire[];
  combat_pressure: CombatPressure;
  current_turn_summary: TurnSummary;
  pending_actions: PendingAction[];
  // event_log は session_restore でのみ送信、通常の state_update には含まない
  next_event_id: number;
  archived_event_count: number;
  scenario: Scenario;
}

interface Character {
  id: string;
  name: string;
  player_id: string | null;
  faction: "pc" | "ally_npc" | "enemy" | "neutral";
  is_boss: boolean;
  tai: number;
  rei: number;
  kou: number;
  jutsu: number;
  max_hp: number;
  max_mp: number;
  hp: number;
  mp: number;
  mobility: number;
  evasion_dice: number;
  max_evasion_dice: number;
  position: [number, number];
  equipped_weapons: string[];
  equipped_jacket: string | null;
  weapon_carry_cost: number;
  armor_value: number;
  inventory: Record<string, number>;
  skills: string[];
  arts: string[];
  status_effects: StatusEffect[];
  has_acted_this_turn: boolean;
  movement_used_this_turn: number;
  first_move_mode: "normal" | "tactical_maneuver" | "attack_focus" | null;
  tactical_maneuver_active: boolean;
  attack_focus_active: boolean;
}

interface StatusEffect {
  name: string;
  source: string;
  duration_rounds: number | null;
  magnitude: Record<string, unknown>;
}

interface CombatPressure {
  level: "normal" | "hard" | "ultra_hard";
  consecutive_no_damage_turns: number;
  boss_combat_active: boolean;
}

interface TurnSummary {
  damage_dealt_to_bosses: number;
  damage_dealt_to_pcs: number;
  damage_dealt_to_mobs: number;
}

interface MapObject {
  id: string;
  name: string;
  position: [number, number];
  strength: number;
  armor: number;
  properties: Record<string, unknown>;
}

interface Pillar {
  id: string;
  position: [number, number];
  deployer_id: string;
}

interface Wire {
  id: string;
  pillar_id: string;
  positions: [number, number][];
}

interface Barrier {
  id: string;
  pillar_id: string;
  deployer_id: string;
  effect: "barrier_wall" | "armor_dissolve" | "evasion_block" | "attack_opportunity";
  range_cells: [number, number][];
  dispel_difficulty: "NORMAL" | "HARD" | "ULTRA_HARD";
}

interface Scenario {
  scenario_id: string;
  title: string;
  map_size: [number, number];
  respawn_point: [number, number];
  // ... その他のシナリオ情報
}
```

### 5-2. PendingAction

```typescript
type PendingAction = EvasionRequest | DeathAvoidanceRequest;

interface EvasionRequest {
  type: "evasion_request";
  pending_id: string;
  target_character_id: string;
  target_player_id: string | null;
  incoming_attacks: IncomingAttack[];
  can_batch: boolean;
  max_evasion_dice: number;
  created_at: string;  // ISO 8601
  deadline_at: string;
}

interface IncomingAttack {
  attacker_id: string;
  attack_command_id: string;
  successes: number;
  threshold: number;
  damage_formula: string;
  damage_type: "physical" | "spiritual";
}

interface DeathAvoidanceRequest {
  type: "death_avoidance_request";
  pending_id: string;
  target_character_id: string;
  target_player_id: string;
  incoming_damage: number;
  damage_type: "physical" | "spiritual";
  katashiro_required: number;
  katashiro_remaining: number;
  created_at: string;
  deadline_at: string;
}
```

### 5-3. GameEvent

```typescript
interface GameEvent {
  event_id: number;
  timestamp: string;  // ISO 8601
  type: string;
  payload: Record<string, unknown>;
  affected_characters: string[];
}
```

### 5-4. ExpiredPending

```typescript
interface ExpiredPending {
  pending_id: string;
  type: "evasion_request" | "death_avoidance_request";
  auto_choice: string;
  reason: string;
}
```

---

## 6. ErrorCode 完全一覧

両仕様書で参照される `ErrorCode` Enum の唯一の正本。

```typescript
type ErrorCode =
  // 認証・認可
  | "AUTH_INVALID_TOKEN"
  | "AUTH_TOKEN_EXPIRED"
  | "AUTH_PERMISSION_DENIED"
  
  // ルーム・接続
  | "ROOM_NOT_FOUND"
  | "ROOM_FULL"
  | "DUPLICATE_CONNECTION"
  
  // ステートマシン
  | "STATE_LOCK_TIMEOUT"
  | "OUT_OF_TURN"
  | "INVALID_STATE_TRANSITION"
  | "VERSION_MISMATCH"
  
  // コマンドバリデーション
  | "INVALID_PATH"
  | "OUT_OF_RANGE"
  | "UNKNOWN_TARGET"
  | "UNKNOWN_CHARACTER"
  | "UNKNOWN_WEAPON"
  | "INVALID_DICE_DISTRIBUTION"
  | "INVALID_ACTION_SEQUENCE"
  
  // リソース
  | "INSUFFICIENT_MP"
  | "INSUFFICIENT_KATASHIRO"
  | "NO_LINE_OF_SIGHT"
  
  // 割り込み
  | "PENDING_NOT_FOUND"
  | "PENDING_EXPIRED"
  | "DUPLICATE_REQUEST"
  
  // AI
  | "AI_FALLBACK"
  | "AI_PARSE_ERROR"
  | "AI_BACKEND_UNAVAILABLE"
  
  // シナリオ
  | "SCENARIO_VALIDATION_FAILED"
  | "SCENARIO_NOT_FOUND"
  
  // 内部
  | "INTERNAL_ERROR";
```

各 ErrorCode の `detail` フィールドの構造例:

```typescript
// VERSION_MISMATCH
{ current_version: number, expected_version: number }

// INVALID_PATH
{ invalid_at_index: number, reason: string }

// OUT_OF_RANGE
{ distance: number, max_range: number }

// INSUFFICIENT_MP
{ required: number, current: number }

// PENDING_NOT_FOUND
{ pending_id: string }

// その他は detail なし or { hint: string }
```

---

## 7. WebSocket close code 完全一覧

| code | 意味 | 再接続 |
|---|---|---|
| 1000 | 正常終了 | しない |
| 1001 | クライアント離脱 | しない |
| 4000 | 認証失敗 | しない |
| 4001 | session_lost (60秒超切断 or event_log_truncated) | しない |
| 4002 | session_lost (サーバー再起動) | しない |
| 4003 | バックプレッシャー超過 | する |
| 4004 | レート制限 | する（10秒待機） |
| 4005 | 重複接続 | しない |

---

## 8. 通信シナリオ例

### 8-1. 正常な戦闘1ターン（PC側）

```
C → S: join_room { auth_token, last_seen_event_id: 0 }
S → C: session_restore { mode: "incremental", current_state, ... }

(プレイヤーが行動構築)

C → S: submit_turn_action { 
  client_request_id: "req-1",
  expected_version: 42,
  turn_action: { /* MeleeAttack 等 */ }
}

S → C: state_update { version: 43, patch: [...] }
S → C: event { event_name: "turn_started", ... }

(攻撃が命中、敵に回避要求)
(敵はNPCなのでサーバー側でヒューリスティック処理)

S → C: state_update { version: 44, patch: [...] }
S → C: event { event_name: "attack_resolved", ... }
S → C: ai_thinking { stage: "narrating" }
S → C: gm_narrative { text: "..." }
S → C: state_update { version: 45, patch: [...] }
S → C: event { event_name: "turn_ended", ... }
```

### 8-2. NPCに攻撃された時

```
S → C: ai_thinking { stage: "deciding_action", actor_id: "enemy1" }
S → C: state_update { ... } (NPCの位置変更等)
S → C: event { event_name: "turn_started", ... }
S → C: evade_required { 
  payload: { 
    pending_id: "pending-1",
    incoming_attacks: [...],
    deadline_at: "...",
  }
}

(プレイヤーが回避ダイス選択)

C → S: submit_evasion {
  client_request_id: "req-2",
  pending_id: "pending-1",
  mode: "individual",
  dice_assignments: [3]
}

S → C: state_update { ... } (回避結果)
S → C: event { event_name: "attack_resolved", ... }
S → C: ai_thinking { stage: "narrating" }
S → C: gm_narrative { text: "..." }
S → C: event { event_name: "turn_ended", ... }
```

### 8-3. 切断と再接続

```
(WebSocket 切断)

(60秒以内に再接続試行)
C → S: WebSocket connect
S → C: WebSocket accept
C → S: join_room { last_seen_event_id: 145 }

(missed_events が30件)
S → C: session_restore {
  mode: "incremental",
  current_state: {...},
  missed_events: [/* 30件 */],
  pending_for_you: [/* 自分宛の有効なpending */]
}

(または missed_events が60件)
S → C: session_restore {
  mode: "full_sync",
  current_state: {...},
  missed_events: [],
  missed_event_count: 60,
  expired_pending: [/* タイムアウト処理されたもの */]
}

(または60秒超過)
S → C: WebSocket close with code 4001
```

### 8-4. VERSION_MISMATCH 発生時

```
C → S: submit_turn_action {
  client_request_id: "req-3",
  expected_version: 42,  ← 古い
  turn_action: {...}
}

S → C: error {
  code: "VERSION_MISMATCH",
  detail: { current_version: 43, expected_version: 42 },
  client_request_id: "req-3"
}

(クライアント: 自動再送信ロジック)
(ドラフトを最新stateで再検証 → valid なので自動再送信)

C → S: submit_turn_action {
  client_request_id: "req-4",
  expected_version: 43,  ← 更新
  turn_action: {...}
}

S → C: state_update { version: 44, ... }
```

### 8-5. AIフォールバック発動

```
S → C: ai_thinking { stage: "deciding_action", actor_id: "enemy1" }

(AI Phase 1 が2回失敗 → デフォルト行動テーブルから選択)

S → C: ai_fallback_notice {
  level: "major",
  reason: "ai_max_retries",
  message: "AI処理にエラー、自動処理"
}
S → C: state_update { ... } (デフォルト行動の結果)
```

---

## 9. クライアント側実装ガイド

### 9-1. 受信メッセージのバリデーション

クライアント側で受信メッセージを Zod で検証することを推奨:

```typescript
// src/types/server_messages.ts
import { z } from 'zod';

const SessionRestoreSchema = z.object({
  type: z.literal('session_restore'),
  event_id: z.number(),
  timestamp: z.string(),
  mode: z.enum(['incremental', 'full_sync']),
  current_state: GameStateSchema,
  missed_events: z.array(GameEventSchema),
  missed_event_count: z.number(),
  pending_for_you: z.array(PendingActionSchema),
  expired_pending: z.array(ExpiredPendingSchema),
});

// 受信時にパースしてエラーなら無視 + ログ
function handleMessage(raw: unknown) {
  const result = ServerMessageSchema.safeParse(raw);
  if (!result.success) {
    console.error('Invalid message:', result.error);
    return;
  }
  // 処理
}
```

### 9-2. 送信メッセージの構築

```typescript
// 送信前に Zod で検証
function submitTurnAction(turnAction: TurnAction) {
  const message = {
    action: 'submit_turn_action',
    player_id: getPlayerId(),
    room_id: getRoomId(),
    client_request_id: nanoid(),
    expected_version: useGameStore.getState().gameState?.version ?? 0,
    turn_action: turnAction,
  };
  
  // Zodで自前検証（バックエンド到達前に弾く）
  const validation = SubmitTurnActionSchema.safeParse(message);
  if (!validation.success) {
    showError('内部エラー: コマンドが不正です');
    return;
  }
  
  ws.send(JSON.stringify(message));
}
```

---

## 10. サーバー側実装ガイド

### 10-1. メッセージスキーマと Pydantic モデルの同期

```python
# src/tacex_gm/ws/messages.py
from pydantic import BaseModel
from typing import Literal, Union

class SubmitTurnAction(BaseModel):
    action: Literal["submit_turn_action"]
    player_id: str
    room_id: str
    client_request_id: str
    expected_version: int
    turn_action: TurnAction

class SubmitEvasion(BaseModel):
    action: Literal["submit_evasion"]
    # ...

# discriminated union
ClientMessage = Annotated[
    Union[SubmitTurnAction, SubmitEvasion, SubmitDeathAvoidance, PlayerStatement, JoinRoom],
    Field(discriminator="action")
]

# WebSocket 受信時
async def receive_message(raw_text: str):
    try:
        msg = ClientMessage.model_validate_json(raw_text)
    except ValidationError as e:
        await send_error(ErrorCode.INVALID_MESSAGE, str(e))
        return
    
    await handle_client_message(msg)
```

### 10-2. JSON Schema のエクスポート（型同期）

実装時に、Pydantic から JSON Schema を生成してフロントエンドの Zod スキーマと比較:

```python
# tools/export_schemas.py
import json
from src.tacex_gm.ws.messages import ClientMessage, ServerMessage

with open("schemas/client_message.json", "w") as f:
    json.dump(ClientMessage.model_json_schema(), f, indent=2, ensure_ascii=False)

with open("schemas/server_message.json", "w") as f:
    json.dump(ServerMessage.model_json_schema(), f, indent=2, ensure_ascii=False)
```

これによりバックエンドとフロントエンドの型定義の同期を機械的に確認可能。

---

## 11. 互換性管理

### 11-1. バージョニング

本仕様書 v1.0 をベースラインとする。互換性のない変更は v2.0 として、移行期間中は旧クライアントもサポートする。

### 11-2. 前方互換性

- サーバーが将来追加するメッセージ種別やフィールドは、クライアント側で「未知のフィールドは無視」する設計
- TypeScript の Zod 検証で `.passthrough()` を使用

---

## 12. 確定事項一覧

| # | 項目 | 決定内容 |
|---|---|---|
| WS-D1 | 通信プロトコル | WebSocket over TLS、JSON テキスト |
| WS-D2 | メッセージ識別 | クライアント送信は action、サーバー送信は type |
| WS-D3 | 冪等性キー | client_request_id（クライアント生成、UUID/nanoid） |
| WS-D4 | イベント順序 | event_id（サーバー生成、単調増加） |
| WS-D5 | 状態バージョン | version（楽観排除した後でも整合性確認用） |
| WS-D6 | TurnAction構造 | 単一構造化オブジェクト（first_move/main_action/second_move/sub_actions） |
| WS-D7 | エラーコード | 本ファイルの ErrorCode 一覧が唯一の正本 |
| WS-D8 | close code | 1000-4005 で意味付け |
| WS-D9 | 再接続 | 60秒タイムアウト、50イベント超過で full_sync |
| WS-D10 | バックプレッシャー | 100件で強制切断、間引きなし |
| WS-D11 | スキーマ同期 | Pydantic → JSON Schema → Zod の機械的同期 |
| WS-D12 | メッセージサイズ | 上限1MB |

---

## 13. Claude Code への最終指示

実装時には:

1. **本仕様書を両仕様書（バックエンド・フロントエンド）の唯一の通信契約として扱う**
2. Pydantic モデル（バックエンド）と Zod スキーマ（フロントエンド）を本仕様書から派生させる
3. 仕様書の変更は両側のコードに必ず反映する
4. JSON Schema エクスポート機能を Phase 0 で実装し、互換性チェックを CI に組み込む
5. メッセージ追加時は本仕様書を先に更新してからコードを書く

---

**以上、WebSocketメッセージスキーマ仕様 v1.0 (FINAL) を実装着手用最終版として固定する。**

両仕様書（`tacex_gm_spec_v2_5_FINAL.md`, `tacex_web_spec_v1_1_FINAL.md`）は本ファイルを参照することで完全な整合性を保つ。

設計フェーズ完了。次は Phase 0 実装開始。
