# タクティカル祓魔師TRPG Headless AI-GM バックエンド 完全案件定義書 v2.5 (FINAL)

**最終更新**: 2026-04-25  
**ステータス**: 実装着手用最終版（Claude Code向け）  
**ペア仕様書**: `tacex_web_spec_v1_1.md`, `tacex_ws_schema_v1_0.md`

---

## ⚠️ Claude Code への重要指示

この仕様書は **Claude Code が実装を進めるための完全仕様** である。以下の原則を厳守すること:

1. **過剰設計を避ける**: 仕様書に書かれていない複雑な並行制御、抽象化、最適化を勝手に追加しない
2. **MVP を最優先**: Phase 2 完了時点で「1人 PC vs 1体 NPC の単純戦闘が動く」ことが最重要
3. **段階的実装**: Phase 0 → 1 → 2 を順次完成させる。Phase 3 以降は MVP 動作確認後
4. **詰まったら止まる**: 仕様で曖昧な点は実装前に確認を求める。勝手な解釈で進めない
5. **テストと並行**: 各機能実装と同時にテストを書く。後回しにしない
6. **疑似コードは参考**: 仕様書のコード片は方針提示。より良い実装があれば採用してよい
7. **依存最小化**: 仕様書に明記されていないライブラリは追加しない

---

## 0. 改訂履歴

| 版 | 日付 | 変更概要 |
|---|---|---|
| v1.0〜v2.4 | — | 5回のレビューサイクルを経て発展 |
| v2.5 | 本版 | **過剰設計の撤回**。3つの厳しいレビューを統合反映: ①楽観的並行制御を撤回し悲観ロックに、②NPC側は「1ツール=1ターン」に簡略化、③UXを Udonarium 流に軽量化、④MVP を Phase 2 に前倒し、⑤工数を18〜24ヶ月に現実化、⑥WebSocketスキーマを別ファイルに分離、⑦AIの優雅な失敗を主役に、⑧多言語化を Phase 0 から準備、⑨実装可能性を最優先 |

---

## 1. プロジェクト概要

| 項目 | 内容 |
|---|---|
| プロジェクト名 | タクティカル祓魔師TRPG Headless AI-GM バックエンド |
| 略称 | TacEx-GM |
| 開発対象 | バックエンドAPIサーバー |
| 目的 | AIによるTRPGセッション進行・状態管理・判定処理に特化したヘッドレスサーバー |
| 対象システム | タクティカル祓魔師TRPG（コアルールブック Ver1.00 準拠） |
| 開発体制 | 単独開発 |
| 推定総工数 | **18〜24ヶ月**（フルタイム1名換算、リスクバッファ込み） |
| 想定運用スケール | 同時5〜10セッション |
| MVP定義 | **Phase 2 完了時点で 1vs1 単純戦闘が動作** |

### 1-1. MVP の最小機能セット（Phase 2 完了時点）

これだけ動けば一旦リリース可能とする:

- ルーム作成・参加・WebSocket接続・再接続
- 1人 PC + 1体 NPC（鬱黒揚羽のような最弱モブ）の戦闘
- PC のターン: 移動 + 通常近接攻撃
- NPC のターン: AI が「攻撃」を選択（移動なし）
- 攻撃 → 命中判定 → 回避要求 → 回避判定 → ダメージ適用
- HP 0 で死亡（形代システムなし、リスポーンなし）
- AI による最低限のナラティブ生成（テンプレでもOK）
- セッションログ表示

これ以降の機能（連撃、戦術機動、結界、祓魔術、形代、複数プレイヤー、ハードモード等）は MVP 確認後に追加する。

---

## 2. システムコンセプト

### 2-1. 3層アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│              AI（GM・NPC行動決定）                  │
│  ・行動決定（function calling、1ツール=1ターン）     │
│  ・ナラティブ生成（plain text）                     │
│  ・優雅な失敗: 失敗時はデフォルト行動テーブル          │
└──────────────────────┬──────────────────────────┘
                       │ Anthropic API or OpenAI互換
                       ▼
┌─────────────────────────────────────────────────┐
│         FastAPI バックエンド                        │
│  ・ゲーム状態の完全管理                              │
│  ・悲観ロック（asyncio.Lock）でルーム単位排他          │
│  ・ルールエンジン                                   │
│  ・WebSocketによるリアルタイム通信                   │
│  ・Python内蔵ダイスエンジン                          │
└──────────────────────┬──────────────────────────┘
                       │ WebSocket (JSON、別schema定義)
                       │
┌─────────────────────────────────────────────────┐
│         フロントエンド（別仕様書）                    │
└─────────────────────────────────────────────────┘
```

### 2-2. 設計思想（v2.5 で再整理）

| 原則 | 説明 |
|---|---|
| **PXファースト** | プレイヤー体験 > 技術的純粋さ。テンポを殺す設計は採用しない |
| **MVP優先** | Phase 2 完了時点で動くものを作る。それまでは機能を絞る |
| **AIの優雅な失敗** | AIが壊れても確実に動く。デフォルト行動テーブルが主役 |
| **単純な悲観ロック** | 同時10セッション規模なら asyncio.Lock で十分 |
| **過剰抽象化を避ける** | Protocol/抽象クラスは差替が必要なものだけ |
| **状態管理はシンプル** | 監査ログとして event_log を残すが、複雑なイベントソーシングはしない |
| **テスト容易性** | DIによる差替、決定論的テスト |

---

## 3. 技術スタック

| 技術 | 用途 | 備考 |
|---|---|---|
| Python 3.11+ | 開発言語 | |
| FastAPI | Webフレームワーク | 非同期処理、WebSocket対応 |
| Pydantic v2 | データモデル・バリデーション | discriminated union、JSON Schema自動生成 |
| WebSocket | フロント通信 | |
| anthropic (Python SDK) | LLM呼び出し（メイン） | Phase 0 必須 |
| openai (Python SDK) | LLM呼び出し（OpenAI互換、vLLM等） | Phase 5 で対応 |
| Jinja2 | ナラティブテンプレートレンダリング | |
| Python random | ダイスエンジン（標準） | seed指定で決定論的 |
| pytest + hypothesis + pytest-asyncio | テスト | |
| Prometheus形式 | メトリクス | `/metrics` エンドポイント |
| PyYAML | シナリオ・データファイル | |

### 3-1. 排除した技術（v2.4 から）

- ~~BCDice-API~~ : Python内蔵ダイスのみで十分
- ~~vLLM 必須~~ : Phase 5 まで Anthropic API のみ
- ~~楽観的並行制御~~ : 悲観ロックで十分

### 3-2. AIモデル選定（簡素化）

**Phase 0〜4**: Anthropic API のみ（Claude Sonnet 4.5）
**Phase 5以降**: OpenAI互換バックエンドの追加実装（vLLM経由のローカルモデル）

ローカルモデル候補は MVP 後に検討。

---

## 4. AIプロトコル仕様

### 4-1. プロトコル方針: function calling、ただし「1ツール=1ターン」

v2.4 までの「AtomicActionのリストを生成させる」方針は撤回。**NPCの行動決定では1ツール呼び出しで1ターン分を完結させる**。

これにより:
- マルチステップツール呼び出しの精度問題を回避
- function calling の構造破綻率を抑制
- AIの負担を軽減

```python
# NPCのターン処理（簡略化された方針）
# AIは以下のような大きな粒度のツールから1つだけ選ぶ:
tools = [
    {"name": "do_simple_attack", "description": "対象に通常攻撃する"},
    {"name": "do_movement_and_attack", "description": "移動してから対象を攻撃する"},
    {"name": "do_simple_move", "description": "位置を移動するだけ"},
    {"name": "skip_turn", "description": "何もしない"},
    # Phase 4 以降: do_cast_art, do_deploy_barrier 等
]

# 各ツールのパラメータは単純化:
# do_simple_attack: target_id のみ。スタイル等はバックエンドが推奨を選ぶ
# do_movement_and_attack: target_id, approach_distance（最大移動マス数）
```

バックエンドは AI のツール呼び出しを受け取って、**内部で詳細パラメータを決定**する（武器選択、スタイル選択、ダイス配分等）。AIには戦略的判断のみ任せる。

### 4-2. 採用方式: 2フェーズ生成（維持）

```
[Phase 1: 行動決定]
  AI入力: 状態 + 履歴
  AI出力: tool_call (1個のみ)
       ↓
  バックエンド: 詳細パラメータ決定 → 判定実行 → 割り込み処理
       ↓
[Phase 2: 結果描写]
  AI入力: 状態 + 行動 + 判定結果
  AI出力: plain text
```

### 4-3. AI失敗時のデフォルト行動テーブル（決定事項 D-FINAL-1: 主役化）

AI Phase 1 が失敗した場合のフォールバック:

```python
DEFAULT_NPC_ACTIONS = {
    # 攻撃可能な敵があれば攻撃
    "has_enemy_in_range": "do_simple_attack(target=nearest_enemy)",
    # 攻撃可能な敵がなく、近づけば届くなら接近攻撃
    "can_approach_to_attack": "do_movement_and_attack(target=nearest_pc, approach=mobility)",
    # それ以外
    "default": "skip_turn",
}
```

このテーブルは確実に動く。AI再試行は最大2回（v2.4の3回から削減、レイテンシ削減）。失敗してもゲームは止まらない。

### 4-4. PCのターン処理

PCのターンは AI 介在なし。プレイヤー入力を直接コマンド化（v2.4 D4 維持）。フロントエンドが詳細なコマンドを構築して送信する。

### 4-5. レンダリング関数（インターフェースのみ）

```python
def render_game_state_for_ai(state: GameState) -> str: ...
def render_resolution(resolution: dict) -> str: ...
def build_phase1_messages(state: GameState, actor: Character) -> list[Message]: ...
def build_phase1_tools(actor: Character, state: GameState) -> list[ToolDefinition]: ...
def build_phase2_messages(state: GameState, action_summary: dict, resolution: dict) -> list[Message]: ...
```

---

## 5. 権限境界

| 主体 | 範囲 |
|---|---|
| プレイヤー | 自分のPCの行動決定、自由発言、回避ダイス数、形代消費判断 |
| AI | 敵NPCの**戦略的**行動決定、状況描写 |
| ヒューリスティック | NPCの**戦術的**詳細（武器選択、ダイス分配、回避） |
| バックエンド | ルール処理、判定実行、状態管理、フェーズ遷移 |

### 5-1. プレイヤー入力の2分類（変更なし）

```json
// 1. 構造化された行動宣言
{
  "action": "submit_turn_action",
  "player_id": "...",
  "room_id": "...",
  "client_request_id": "req-uuid-...",
  "turn_action": { /* TurnAction */ }
}

// 2. 自由発言
{
  "action": "player_statement",
  "player_id": "...",
  "room_id": "...",
  "client_request_id": "req-uuid-...",
  "text": "..."
}
```

### 5-2. PCの行動コマンド（簡素化版）

PC側もAtomicActionリストではなく、**単一の構造化コマンド**にする。フロントエンドUIで一連の操作を組み立てて、まとめて1つのコマンドとして送信:

```python
class TurnAction(BaseModel):
    """1手番分の行動を表す。"""
    actor_id: str
    
    # 第一移動（任意、省略時は移動しない）
    first_move: Optional[Movement] = None
    
    # 主行動（必須、ただし Skip も可）
    main_action: MainAction  # discriminated union
    
    # 第二移動（任意）
    second_move: Optional[Movement] = None
    
    # サブアクション（任意、Phase 4以降）
    sub_actions: list[SubAction] = []

class Movement(BaseModel):
    path: list[tuple[int, int]]
    mode: Literal["normal", "tactical_maneuver", "attack_focus"] = "normal"

# MainAction の discriminated union
MainAction = Union[
    MeleeAttack,
    RangedAttack,
    PegAttack,
    CastArt,         # Phase 4以降
    DeployWire,      # Phase 4以降
    DispelBarrier,   # Phase 4以降
    UseItem,         # Phase 4以降
    OtherAction,
    Skip,
]
```

これは v2.4 の AtomicAction リスト方式と v2.3 までの first_move/main_action/second_move 方式の **折衷**。実装複雑度を抑えつつ、順序の表現も明確。

### 5-3. 攻撃コマンドの簡素化（v2.4 と同じ）

```python
class MeleeAttack(BaseModel):
    type: Literal["melee_attack"] = "melee_attack"
    weapon_id: str
    style: MeleeStyle = MeleeStyle.NONE
    additional_style: Optional[AdditionalStyle] = None
    dice_distribution: list[int]
    targets: list[str]
    
    @model_validator(mode="after")
    def validate_targets_length(self):
        if len(self.targets) != len(self.dice_distribution):
            raise ValueError("targets length must match dice_distribution length")
        return self
```

---

## 6. データモデル

### 6-1. 設計方針: 仕様は振る舞いと制約

仕様書には主要な構造とインターフェースのみを記述。実装の詳細はコード側で持つ。

### 6-2. キャラクター

| フィールド | 型 | 説明 |
|---|---|---|
| id | str | 一意識別子 |
| name | str | 表示名 |
| player_id | Optional[str] | PCの場合のみ |
| faction | Literal["pc", "enemy", "neutral"] | 陣営 |
| is_boss | bool | ハードモード判定用、デフォルト False |
| tai, rei, kou, jutsu | int | 基礎能力値（jutsu は 0〜3、他は 1〜12） |
| max_hp, max_mp | int | 上限値 |
| hp, mp | int | 現在値 |
| mobility | int (computed) | max(tai, kou)/2 切り上げ、最低2 |
| evasion_dice | int | 現在の回避ダイス |
| max_evasion_dice | int | 最大値 |
| position | tuple[int, int] | マップ座標 |
| equipped_weapons | list[str] | 装備中の祭具ID |
| equipped_jacket | Optional[str] | 狩衣 |
| armor_value | int | 装甲値（狩衣由来） |
| inventory | dict[str, int] | 祭具残数 |
| skills | list[str] | スキル名リスト |
| arts | list[str] | 祓魔術名リスト |
| status_effects | list[StatusEffect] | 状態異常 |
| has_acted_this_turn | bool | 当ターン行動済みフラグ |
| movement_used_this_turn | int | 当ターン使用済み移動 |
| first_move_mode | Optional[str] | normal/tactical_maneuver/attack_focus |
| evasion_policy | Optional[NPCEvasionPolicy] | NPC専用 |

### 6-3. ゲーム状態

| フィールド | 型 | 説明 |
|---|---|---|
| room_id | str | |
| version | int | 状態バージョン（クライアント同期用） |
| seed | int | ダイスシード |
| phase | Literal["briefing", "exploration", "combat", "assessment"] | |
| machine_state | MachineState | 状態マシン |
| turn_order | list[str] | キャラID順 |
| current_turn_index | int | 現在のターン |
| round_number | int | 現在のラウンド |
| characters | list[Character] | |
| map_size | tuple[int, int] | |
| obstacles | list[tuple[int, int]] | |
| objects | list[MapObject] | Phase 5以降 |
| barriers | list[Barrier] | Phase 4以降 |
| pillars | list[Pillar] | Phase 4以降 |
| wires | list[Wire] | Phase 4以降 |
| combat_pressure | CombatPressure | Phase 6以降 |
| current_turn_summary | TurnSummary | |
| pending_actions | list[PendingAction] | 割り込み待機 |
| event_log | list[GameEvent] | 監査ログ |
| next_event_id | int | |
| archived_event_count | int | |
| scenario | Scenario | |

### 6-4. メモリ管理（実測重視）

```
EVENT_LOG_MAX_SIZE = 10000  # 暫定値
EVENT_LOG_TARGET_SIZE_AFTER_TRIM = 8000
```

**Phase 0 必須タスク**: 実際の `GameEvent` のシリアライズサイズを 100件サンプリングして実測。試算と乖離があれば値を調整。レビュー指摘により、Pythonオブジェクトのオーバーヘッドを過小評価しないよう、**実測前にバジェットを語らない**。

### 6-5. その他のデータモデル（インターフェース概要）

- `Pillar`: 祓串（位置、設置者）
- `Wire`: 注連鋼縄（pillar_id、覆う範囲）
- `Barrier`: 結界（pillar_id、効果、範囲）
- `MapObject`: マップオブジェクト（位置、強度、装甲）
- `CombatPressure`: 戦闘圧力レベル
- `TurnSummary`: 当ターンのダメージ集計
- `GameEvent`: イベントログエントリ（event_id, type, payload）

詳細は実装時に Pydantic モデルとして定義。

### 6-6. 難易度定数

```python
DIFFICULTY_TABLE = {
    "KIDS": 2, "EASY": 3, "NORMAL": 4, "HARD": 5, "ULTRA_HARD": 6,
}
# 修正は KIDS〜ULTRA_HARD にクランプ
```

### 6-7. 攻撃スタイル定数

| 種類 | 値 |
|---|---|
| MeleeStyle | none, 連撃, 精密攻撃, 強攻撃, 全力攻撃 |
| RangedStyle | none, 2回射撃, 連射, 連射II, 狙撃, 抜き撃ち |
| AdditionalStyle | 両手利き |

### 6-8. ダメージ仕様

ルールブック内のダメージ式は `NdM`, `NdM+K`, 定数, 能力値ボーナスのみ。

```python
class DamageFormula(BaseModel):
    """NdM+K 形式のみサポート"""
    raw: str
    def expected_value(self) -> float: ...

class AbilityBonus(BaseModel):
    """能力値依存ボーナス"""
    ability: Literal["体", "霊", "巧"]
    multiplier: float = 1.0
    condition: Literal["always", "on_six", "on_double_six"] = "always"

class DamageSpec(BaseModel):
    base_formula: DamageFormula
    ability_bonus: Optional[AbilityBonus] = None
```

### 6-9. スキル前提依存

`SKILL_REQUIREMENTS` 辞書で各スキルの前提条件を定義。Phase 1 で網羅。

---

## 7. ステートマシンと並行制御（**v2.5 で大幅簡素化**）

### 7-1. マシンステート

| 状態 | 意味 |
|---|---|
| IDLE | 次コマンド待機 |
| RESOLVING_ACTION | コマンド処理中 |
| AWAITING_PLAYER_INPUT | 割り込み待機 |
| NARRATING | AI Phase 2 実行中 |
| PAUSED | 切断等で一時停止 |

### 7-2. RoomLock（**悲観ロック、AI呼び出し中も維持**）

レビュー指摘により、楽観的並行制御を撤回。**シンプルな悲観ロックに戻す**。

```python
class RoomLock:
    """ルーム単位の排他ロック。AI呼び出し中もロックを維持する単純な実装。"""
    def __init__(self, room_id: str, default_timeout: float = 30.0):
        self.room_id = room_id
        self._lock = asyncio.Lock()
        self.default_timeout = default_timeout
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        timeout = timeout or self.default_timeout
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            raise StateLockTimeout(...)
        try:
            yield
        finally:
            self._lock.release()
```

**重要**: AI Phase 1/2 呼び出し中もロックを保持する。タイムアウトは30秒（AI応答時間 + 余裕）。

トレードオフ:
- **メリット**: 実装が劇的に単純、衝突解決ロジック不要、デバッグ容易
- **デメリット**: NPC ターン中、他プレイヤーは「ターン進行中」を待つ
- **判断**: 同時5〜10セッション規模なら問題なし。プレイヤーは「GMが処理中」を待つことに慣れている

### 7-3. 楽観的並行制御は **採用しない**

v2.4 の D57（楽観的並行制御）は撤回。version衝突解決の複雑さは排除。

ただし、**`expected_version` チェックはクライアント側UI整合のため残す**:
- クライアントが古い state を見て送信してきた場合に検出
- VERSION_MISMATCH エラーで返す（UIで再表示を促す）

### 7-4. PendingAction

```python
class EvasionRequest(BaseModel):
    pending_id: str
    target_character_id: str
    target_player_id: Optional[str]
    incoming_attacks: list[IncomingAttack]
    can_batch: bool
    max_evasion_dice: int
    created_at: datetime
    deadline_at: datetime  # 60秒後

class DeathAvoidanceRequest(BaseModel):
    pending_id: str
    target_character_id: str
    target_player_id: str
    incoming_damage: int
    damage_type: Literal["physical", "spiritual"]
    katashiro_required: int
    katashiro_remaining: int
    created_at: datetime
    deadline_at: datetime
```

### 7-5. タイムアウト処理（変更なし）

- 通常タイムアウト: 60秒
- 警告: 30秒前、10秒前
- 回避タイムアウト: 0ダイス回避自動応答
- 死亡回避タイムアウト: accept_death 自動選択
- 切断中もタイマー進行

### 7-6. 戦闘1ターンのフロー（簡素化版）

```
[IDLE]
  ↓ プレイヤー submit_turn_action (with expected_version)
[RESOLVING_ACTION] ← RoomLock取得
  - expected_version 検証（不一致なら VERSION_MISMATCH 返却、ロック解放）
  - first_move 適用
  - main_action の処理
  - 命中判定
[AWAITING_PLAYER_INPUT] ← RoomLock解放
  - EvasionRequest 作成
  - evade_required 送信
  ↓ submit_evasion
[RESOLVING_ACTION] ← RoomLock再取得
  - 回避判定 → ダメージ確定
  - 死亡判定 → 必要なら DeathAvoidanceRequest（Phase 4以降）
  - second_move 適用
[NARRATING] ← RoomLock維持
  - AI Phase 2 呼び出し（同期、ロック保持）
  - 描写発行
[IDLE] ← RoomLock解放
```

NPC ターンも同様にロック内で完結。

---

## 8. WebSocketプロトコル

詳細は **`tacex_ws_schema_v1_0.md`（別ファイル）** を参照。本仕様書では概要のみ。

### 8-1. 接続ライフサイクル

```
[CLOSED]
  ↓ wss://server/room/{room_id}
[CONNECTING]
  ↓ accept
  ↓ join_room (auth_token, last_seen_event_id)
[AUTHENTICATING]
  ↓ session_restore
[ACTIVE]
  ⇄ メッセージ送受信
  ⇄ TCP keep-alive 依存（独自ハートビート不要）
[DISCONNECTED]
  ↓ 再接続試行（60秒以内）
```

### 8-2. ハートビート（最小化）

TCP keep-alive と WebSocket 標準 ping/pong に依存。独自プロトコルは作らない。

### 8-3. バックプレッシャー

送信バッファ100メッセージ超過 → 強制切断（close code 4003）。間引きはしない（状態の一貫性のため）。

### 8-4. 再接続

- タイムアウト: 60秒
- バックオフ: 1s, 2s, 4s, 8s, 16s
- 50イベント超過時は full_sync モード（状態のみ送る）

### 8-5. close codeハンドリング

| code | 意味 |
|---|---|
| 1000 | 正常終了 |
| 4000 | 認証失敗 |
| 4001 | session_lost (60秒超切断) |
| 4002 | session_lost (サーバー再起動) |
| 4003 | バッファ超過 |
| 4004 | レート制限 |
| 4005 | 重複接続 |

---

## 9. コア判定エンジン

### 9-1. 回避判定（独立判定）

攻撃判定と回避判定は完全独立。成功数の比較なし。1個以上難易度満たせば成功。

### 9-2. ダイスエンジン

```python
class DiceEngine(Protocol):
    async def roll_pool(self, count: int, threshold: int) -> DiceResult: ...
    async def roll_sum(self, count: int, sides: int = 6, modifier: int = 0) -> DiceResult: ...

class PythonDiceEngine:
    """標準ダイスエンジン。seed指定で決定論的。"""
    def __init__(self, seed: Optional[int] = None): ...
```

DiceResult: command, rolls, successes, sum, success の各フィールド。

### 9-3. 距離計算

```python
def calc_distance(p1: tuple[int, int], p2: tuple[int, int]) -> int:
    """チェビシェフ距離（8方向移動）"""
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))
```

### 9-4. 射線判定

Bresenham 8方向、両側ブロック判定（プレイヤー有利の解釈）。

### 9-5. 移動経路バリデーション

Path の隣接性、距離、障害物、終点の空きをチェック。

### 9-6. 射程別難易度テーブル

| 祭具種類 | 0〜3マス | 4〜8マス | 9〜11マス |
|---|---|---|---|
| 小型遠隔 | NORMAL | HARD | ULTRA_HARD |
| 中型遠隔 | HARD | NORMAL | HARD |
| 大型遠隔 | HARD (〜8) | NORMAL (9〜) | — |
| 祓串遠隔 | NORMAL (〜5) | HARD (6〜8) | ULTRA_HARD (9〜11) |

---

## 10. ルールエンジン処理フロー

### 10-1. TurnAction 処理

```
1. expected_version チェック → VERSION_MISMATCH ならエラー返却
2. first_move を実行（あれば）
3. main_action を実行
   3.1 攻撃系なら命中判定 → EvasionRequest 発行 → 待機
   3.2 その他は即時処理
4. 回避応答受信後、ダメージ計算・適用（逐次）
5. 死亡判定 → 必要なら DeathAvoidanceRequest（Phase 4以降）
6. second_move を実行（あれば）
7. sub_actions を実行（Phase 4以降）
8. TurnSummary 更新
9. AI Phase 2 で描写
10. ターン終了、次のキャラへ
```

### 10-2. 死亡回避（Phase 4以降）

「現在HP×2を超える物理ダメージ」なら形代2枚必要。各撃逐次判定。

### 10-3. ハードモード（Phase 6以降）

PC側ボスへのダメージ0 かつ ボス側PCへのダメージ0 の連続2ターンで hard、さらに2ターンで ultra_hard。

### 10-4. NPC回避（ヒューリスティック）

```python
def npc_decide_evasion(character, incoming, state) -> SubmitEvasion:
    """脅威度ベースのダイス配分。enemies.yamlのevasion_policyで調整可能。"""
    # 期待ダメージ計算 → 脅威度ソート → ダイス配分
    # 詳細は実装時に
```

### 10-5. NPC行動決定（AI、簡素化）

```python
async def npc_decide_action(character, state) -> ActionDecision:
    """
    Phase 1: AI に「1ツール=1ターン」で大粒度の決定をさせる
    AIが失敗したら DEFAULT_NPC_ACTIONS テーブルから選ぶ
    """
    try:
        tool_call = await ai_phase1(character, state, max_retries=2)
        return interpret_tool_call(tool_call, character, state)
    except (AIFailure, ValidationError):
        return select_default_action(character, state)
```

### 10-6. AI ツール呼び出しの内部展開

AI が `do_movement_and_attack(target_id="alice", approach_distance=3)` のように呼び出した場合、バックエンドが内部で:

1. NPCから対象への経路を計算（最短経路）
2. approach_distance 以内に収める
3. 装備武器・スタイルを推奨選択（基本は単発攻撃）
4. ダイス配分（連撃時は均等割り）
5. 完全な TurnAction を構築

これにより AI の出力構造を単純に保ちつつ、ルールに準拠した行動を生成できる。

---

## 11. AI出力信頼性

### 11-1. 簡素化された再試行

```python
async def get_npc_action_with_retry(state, character, max_retries=2):
    last_error = None
    for attempt in range(max_retries):
        try:
            tool_call = await llm.chat_completion(...)
            return parse_and_validate(tool_call)
        except Exception as e:
            last_error = e
    
    # フォールバック: デフォルト行動テーブル
    notify_player_fallback(state.room_id, level="minor")
    return select_default_action(character, state)
```

`max_retries` は v2.4 の3回から **2回に削減**（レイテンシ低減）。

### 11-2. ナラティブフォールバック（v2.4 維持）

3階層: 縮約再試行 → テンプレライブラリ → 最低限テンプレ。

### 11-3. テンプレライブラリ（YAML外部化）

`data/narration_templates.yaml` で外部化、Jinja2レンダリング、起動時バリデーション。

### 11-4. メトリクス

```
ai_calls_total{phase="action|narration"}
ai_failures_total{layer="schema|semantic|tool_choice"}
ai_retries_total{attempt="1|2"}
ai_default_action_used_total
ai_latency_seconds (histogram)
narration_fallback_level{level="none|minor|major"}
room_lock_acquire_seconds (histogram)
room_lock_timeouts_total
ws_connections_active (gauge)
ws_close_total{code="..."}
event_log_size (gauge, per room)
event_log_trim_total
```

---

## 12. システムモジュールインターフェース

```python
class SystemModule(Protocol):
    system_name: str
    
    def get_system_prompt(self) -> str: ...
    def build_phase1_tools(self, actor: Character, state: GameState) -> list[ToolDefinition]: ...
    
    async def execute_turn_action(
        self, action: TurnAction, state: GameState, dice_engine: DiceEngine
    ) -> TurnResult: ...
    
    def validate_turn_action(
        self, action: TurnAction, state: GameState, source: CommandSource
    ) -> ValidationResult: ...
    
    def calculate_turn_order(self, state: GameState) -> list[str]: ...
    def expand_ai_tool_call(
        self, tool_call: dict, character: Character, state: GameState
    ) -> TurnAction: ...
    
    def select_default_action(
        self, character: Character, state: GameState
    ) -> TurnAction: ...

class TacticalExorcistModule(SystemModule):
    """コアルール準拠の実装"""
```

---

## 13. 認証・認可・エラーコード

### 13-1. 認証

| 項目 | 仕様 |
|---|---|
| ルーム作成 | POST /rooms でルームID + マスタートークン発行 |
| プレイヤー参加 | POST /rooms/{id}/join でプレイヤートークン発行 |
| WebSocket | プレイヤートークンを Authorization ヘッダ |
| 検証 | サーバー側でトークン → player_id 解決 |
| 期限 | Phase 1〜7: プロセス終了まで、Phase 8 以降: 24時間 |

### 13-2. エラーコード（v2.4 D54 維持）

`ErrorCode` Enum で全網羅。詳細は `tacex_ws_schema_v1_0.md` 参照。

`ErrorResponse`: code, message (日本語、デバッグ用), detail (構造化)。

---

## 14. シナリオ定義

### 14-1. シナリオYAML構造

```yaml
scenario_id: "first_mission"
title: "最初の任務"
map_size: [20, 20]
respawn_point: [10, 10]
obstacles:
  - [3, 5]
characters:
  - id: "enemy1"
    name: "鬱黒揚羽"
    faction: "enemy"
    template: "ukkoku_ageha"
    position: [15, 10]
events:
  - id: "event_zone_entry"
    trigger:
      type: "enter_zone"
      zone: [[10, 10], [15, 15]]
      who: ["any_pc"]
    actions:
      - type: "spawn_enemy"
        template: "ukkoku_ageha"
        count: 2
        positions: [[12, 12], [13, 12]]
    once: true
victory_conditions:
  - type: "all_enemies_defeated"
failure_conditions:
  - type: "all_pcs_defeated"
```

### 14-2. データファイル

| ファイル | 内容 |
|---|---|
| data/enemies.yaml | エネミーテンプレ |
| data/weapons.yaml | 祭具データ |
| data/arts.yaml | 祓魔術（Phase 6） |
| data/narration_templates.yaml | ナラティブテンプレ |

**Phase 1 必須**: 少なくともMVPに必要な3〜5種類の敵テンプレと、初期作成可能な全祭具を定義。

### 14-3. ScenarioValidator

ロード時の包括的バリデーション:
- テンプレ参照の存在
- 座標範囲
- トリガー一貫性
- 重複ID
- Compoundトリガー深度（最大3）
- エラーは行番号付きで報告

### 14-4. Phase別サポートトリガー

| Phase | トリガー |
|---|---|
| Phase 2 | enter_zone, character_dies のみ |
| Phase 6 | + round_reached, object_destroyed |
| Phase 7 | + hp_threshold, compound |

---

## 15. 開発マイルストーン（**v2.5 で工数現実化**）

### 15-1. Phase別工数（フルタイム1名換算）

| Phase | 内容 | 工数 |
|---|---|---|
| Phase 0 | 雛形・認証・WebSocket・LLM接続・ハッピーパス結合テスト | 4〜6週 |
| Phase 1 | データモデル全種、ルールエンジン基礎、Validator、データファイル | 8〜10週 |
| Phase 2 | **MVP: 1vs1 単純戦闘ループ動作** | 6〜8週 |
| Phase 3 | TurnAction 完全版（連撃、戦術機動、攻撃集中） | 8〜10週 |
| Phase 4 | 全祭具・全スタイル、形代システム、リスポーン | 8〜10週 |
| Phase 5 | 祓魔術、結界システム、OpenAI互換LLM追加 | 12〜14週 |
| Phase 6 | ハードモード、複数プレイヤー、トリガー拡張 | 10〜12週 |
| Phase 7 | 査定フェイズ、成長 | 8〜10週 |
| Phase 8 | 永続化（SQLite）、複数術修得 | 10〜12週 |
| Phase 9 | 統合テスト、負荷テスト、長時間稼働 | 6〜8週 |

**合計: 80〜100週（18〜23ヶ月）**

これは v2.4 の「10〜14ヶ月」から**ほぼ倍増**。レビュー指摘により現実化。

### 15-2. Phase 0 完了条件

1. プロジェクト雛形（pyproject.toml, ディレクトリ, docker-compose）
2. 認証エンドポイント（POST /rooms, POST /rooms/{id}/join）
3. WebSocket疎通（join_room ハンドラ）
4. `LLMBackend` Protocol + `AnthropicBackend` 実装
5. ハッピーパス結合テスト: モックNPCターン → モック攻撃 → モック回避応答 → モック描写 まで通る
6. ナラティブテンプレート起動時バリデーション
7. **GameEvent サイズ実測**（100件サンプリング、設計値との乖離を確認）
8. WebSocketメッセージスキーマファイル（`tacex_ws_schema_v1_0.md`）が両仕様書と整合

### 15-3. Phase 2 MVP 完了条件（**最重要マイルストーン**）

これだけ動けば一旦リリース可能:

- ルーム作成→参加→セッション開始
- マップ上に PC 1人 + NPC 1体（鬱黒揚羽）配置
- PC のターン: 移動 + 通常近接攻撃 を選択して送信可能
- NPC のターン: AI が `do_simple_attack` を選択（または default action）
- 命中判定 → 回避要求 → 回避ダイス入力 → 回避判定 → ダメージ
- HP 0 で死亡（フラグ立てるだけ、リスポーン不要）
- ナラティブ表示（テンプレベースで OK、AI Phase 2 はオプション）
- 戦闘終了判定

**MVPで動かないこと:**
- 連撃、戦術機動、攻撃集中
- 結界、祓魔術
- 形代消費、リスポーン
- 複数プレイヤー
- ハードモード
- 査定フェイズ、成長

### 15-4. クリティカルパス

- Phase 0 → 1 → 2 が前提条件チェーン（短縮不可）
- Phase 3 以降は MVP 動作確認後に着手
- フロントエンドは Phase 2 完成後に本格化（モック相手の Phase 0-1 はバックエンド並行）

### 15-5. 実装の進め方ガイド（Claude Code 向け）

各 Phase の完了条件を満たしたら、必ず以下を実施:
1. ユニットテスト全件 PASS
2. 統合テスト全件 PASS
3. ハッピーパス E2E 動作確認
4. 該当 Phase の機能を実際に手で試して動作確認
5. メトリクスエンドポイントが応答するか確認

問題があれば次の Phase に進まず、修正に専念する。

---

## 16. テスト戦略（**v2.5 で具体化**）

### 16-1. テスト環境

すべてのテストで `PythonDiceEngine(seed=...)` を使用。AI 呼び出しはモック化。

### 16-2. ユニットテスト（具体例）

| 対象 | 戦略 | 例 |
|---|---|---|
| ダイス | seed固定 | `test_roll_pool_seed_42_4d6_threshold_4` |
| 距離計算 | property test | `test_distance_chebyshev_property` |
| 射線判定 | パターン網羅 | `test_los_diagonal_corner_blocked_one_side_passes` |
| 移動経路 | 正常・異常 | `test_path_validation_obstacle_in_middle_fails` |
| TurnAction バリデーション | 各 main_action 種別 | `test_validate_melee_attack_targets_mismatch_fails` |
| スキル前提 | 全スキル | `test_skill_踏み込み_requires_白兵戦適性` |
| DamageSpec | 全ダメージ式 | `test_damage_2d6_plus_1_expected_value_8` |
| RoomLock | タイムアウト | `test_lock_acquire_timeout_raises` |
| IdempotencyCache | LRU | `test_cache_eviction_lru` |
| ScenarioValidator | 全エラー種別 | `test_validate_unknown_template_reports_error` |
| NarrationTemplateEngine | 起動時検証 | `test_template_engine_invalid_jinja_raises_on_init` |

### 16-3. 統合テスト（具体例）

| 対象 | 戦略 |
|---|---|
| Phase 0 ハッピーパス | モック AI で end-to-end |
| Phase 2 MVP シナリオ | seed固定、ゴールデンマスター |
| 1vs1戦闘 | PC勝利、PC敗北、相討ちの3パターン |
| 割り込みフロー | モックWSクライアント |
| AIフォールバック | LLMモック化、各種エラー注入 |
| WebSocket Edge Case | 切断、再接続、タイムアウト全パターン |

### 16-4. E2Eテスト（**Phase 3で前倒し**）

レビュー指摘により、E2EテストをPhase 9からPhase 3に前倒し。Phase 3完了時点でPlaywright（フロントエンド側）相当の自動テストを最低限導入。

| Phase | E2E スコープ |
|---|---|
| Phase 3 | スモークテスト（接続→1ターン戦闘→描写） |
| Phase 6 | 主要機能（祓魔術、結界、複数プレイヤー） |
| Phase 9 | 長時間、負荷、Edge Case |

### 16-5. プロパティベーステスト

ダイス、距離、射線判定、ダメージ計算で hypothesis を活用。

### 16-6. ゴールデンマスターの粒度

```
tests/golden/
├── unit/      # AtomicAction単位
├── turn/      # 1ターン処理（メイン）
└── scenario/  # シナリオ通し（数本）
```

中粒度（turn/）をメインに。AIモック使用前提。

### 16-7. AI モック戦略

```python
class MockLLMBackend(LLMBackend):
    """テスト用。事前定義された応答を返す。"""
    def __init__(self, responses: list[ChatCompletionResponse]):
        self.responses = responses
        self.call_index = 0
    
    async def chat_completion(self, **kwargs):
        response = self.responses[self.call_index]
        self.call_index += 1
        return response
```

シナリオごとに応答シーケンスを定義してテスト。

---

## 17. ディレクトリ構成

```
tacex-gm/
├── pyproject.toml
├── docker-compose.yml
├── docker-compose.test.yml
├── README.md
├── src/tacex_gm/
│   ├── __init__.py
│   ├── main.py                   # FastAPIエントリポイント
│   ├── config.py
│   ├── auth.py
│   ├── errors.py                 # ErrorCode Enum
│   ├── ws/
│   │   ├── handler.py
│   │   ├── messages.py
│   │   ├── backpressure.py
│   │   └── idempotency.py
│   ├── room/
│   │   ├── lock.py               # RoomLock（悲観ロック）
│   │   └── manager.py
│   ├── models/
│   │   ├── character.py
│   │   ├── game_state.py
│   │   ├── turn_action.py        # TurnAction, MainAction
│   │   ├── pending.py
│   │   ├── events.py
│   │   ├── damage.py             # DamageFormula, DamageSpec
│   │   ├── scenario.py
│   │   └── triggers.py
│   ├── engine/
│   │   ├── dice.py
│   │   ├── geometry.py
│   │   ├── combat.py
│   │   ├── pressure.py           # Phase 6
│   │   ├── npc_policy.py         # 回避ヒューリスティック
│   │   ├── default_actions.py    # AI失敗時のデフォルト行動テーブル
│   │   ├── trigger_engine.py
│   │   └── state_machine.py
│   ├── ai/
│   │   ├── backend.py            # LLMBackend Protocol
│   │   ├── anthropic_backend.py
│   │   ├── openai_compat.py      # Phase 5
│   │   ├── mock_backend.py       # テスト用
│   │   ├── prompt.py
│   │   ├── tools.py              # Pydantic→Tool定義
│   │   ├── tool_expansion.py     # AIツール呼び出しを内部展開
│   │   ├── parser.py
│   │   ├── fallback.py
│   │   └── narration_engine.py
│   ├── system_module/
│   │   ├── base.py
│   │   └── tactical_exorcist/
│   │       ├── module.py
│   │       ├── arts.py            # Phase 5
│   │       ├── weapons.py
│   │       ├── enemies.py
│   │       ├── skills.py
│   │       └── prompts.py
│   ├── scenario/
│   │   ├── loader.py
│   │   └── validator.py
│   └── observability/
│       ├── metrics.py
│       └── logging.py
├── scenarios/
│   └── first_mission.yaml
├── data/
│   ├── enemies.yaml
│   ├── weapons.yaml
│   ├── arts.yaml                 # Phase 5
│   └── narration_templates.yaml
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    │   ├── test_websocket_edge_cases.py
    │   ├── test_room_lock.py
    │   └── test_happy_path.py    # Phase 0必須
    ├── golden/
    │   ├── unit/
    │   ├── turn/
    │   └── scenario/
    └── load/                      # Phase 9
        └── test_concurrent_sessions.py
```

---

## 18. 確定事項一覧（v2.5 最終版）

| # | 項目 | 決定内容 |
|---|---|---|
| D1 | AI出力 | 2フェーズ生成（Phase 1=ツール呼び出し、Phase 2=描写） |
| D2 | 思考表現 | Anthropic API の reasoning content / message content |
| D3 | Phase 2 不正出力 | 無視＋警告ログ |
| D4 | PC行動の権限 | プレイヤー入力からコマンド直接生成 |
| D5 | 入力UI方針 | 構造化UI主体、自由テキストはRP用 |
| D6 | request_check 発行 | AI自動発行 |
| D7 | 味方NPC | Phase 7まで実装しない |
| D8 | 回避タイムアウト | 60秒、警告は30/10秒前 |
| D9 | タイムアウト時応答 | 0ダイス回避 |
| D10 | 複数同時回避 | 全員揃うまで同期、ダメージは逐次 |
| D11 | 非IDLE時の新規コマンド | 拒否してエラー |
| D12 | 永続化 | Phase 8 |
| D13 | 切断中のタイマー | 進行 |
| D14 | LLM接続層 | LLMBackend Protocol |
| D15 | AI再試行回数 | **2回（v2.5で削減）** |
| D16 | Few-shot例数 | 5例 |
| D17 | フォールバック通知 | majorのみ |
| D18 | メトリクス | Prometheus形式 |
| D19 | AI生ログ保存 | 直近1000件 |
| D20 | コマンド粒度 | TurnAction（first_move/main_action/second_move）。**v2.5でAtomicActionリストを撤回** |
| D21 | ダイスエンジン | Python内蔵のみ |
| D22 | NPC回避判断 | ヒューリスティック |
| D23 | スキル前提 | SKILL_REQUIREMENTS |
| D24 | 再接続プロトコル | event_id + client_request_id |
| D25 | 回避判定 | 攻撃判定と独立 |
| D26 | ナラティブフォールバック | 3階層 |
| D27 | シナリオトリガー | discriminated union |
| D28 | テスト環境のダイス | PythonDiceEngine(seed) |
| D29 | AIプロトコル | function calling |
| D30 | ダメージ式 | DamageSpec |
| D31 | 排他制御 | **悲観ロック（v2.5で楽観的並行制御を撤回）** |
| D32 | 独立判定と同期 | 判定独立、ダメージは逐次 |
| D33 | 再接続スケーリング | 50件閾値、60秒タイムアウト |
| D34 | 死亡回避 | 現在HP×2、各撃逐次 |
| D35 | 戦闘圧力判定 | 双方ノーダメ |
| D36 | respawn状態 | 半量回復、当ターン行動不可 |
| D37 | シナリオ characters | CharacterPlacement で厳密型化 |
| D38 | Compound深度 | 最大3 |
| D39 | ゴールデンマスター粒度 | 細/中/粗の3段階 |
| D40 | AIモデル | Anthropic API（Phase 0-4）、OpenAI互換（Phase 5+） |
| D41 | メモリ管理 | Phase 0で実測必須 |
| D42 | RoomLock Protocol化 | 不要（v2.5で撤回、単純実装のみ） |
| D43 | WebSocketプロトコル | TCP keep-alive依存、独自ハートビート不要 |
| D44 | バックプレッシャー | 100件超過で強制切断 |
| D45 | NPC評価ポリシー外部化 | enemies.yaml |
| D46 | ナラティブテンプレ | YAML 外部化、Jinja2、起動時バリデーション |
| D47 | 認証トークン期限 | Phase 1〜7 はプロセス終了まで |
| D48 | エラーコード体系 | ErrorCode Enum |
| D49 | ScenarioValidator | ロード時に包括的検証 |
| **D-FINAL-1** | **AI失敗時のデフォルト行動** | **DEFAULT_NPC_ACTIONS テーブルで主役化** |
| **D-FINAL-2** | **NPC行動決定の粒度** | **AIには「1ツール=1ターン」、詳細はバックエンドで補完** |
| **D-FINAL-3** | **MVP定義** | **Phase 2 完了時点で 1vs1 単純戦闘** |
| **D-FINAL-4** | **工数見積もり** | **80〜100週（18〜23ヶ月）に現実化** |
| **D-FINAL-5** | **WebSocketスキーマ** | **別ファイル `tacex_ws_schema_v1_0.md` に分離** |
| **D-FINAL-6** | **E2Eテスト** | **Phase 3 に前倒し（v2.4 のPhase 9から）** |

---

## 19. ルール準拠注意事項（変更なし）

| 項目 | 注意点 |
|---|---|
| 機動力計算 | max(体, 巧)/2 切り上げ、最低2 |
| 回避ダイス | 戦闘開始時のみ獲得、手番開始時補充 |
| 攻撃判定と回避判定 | 独立判定、成功数比較なし |
| 装備状態 | 戦闘開始時宣言、攻撃時入れ替え可 |
| 祓串の扱い | 装備状態にならない、近接1d6/遠隔3点 |
| 連続攻撃 | キーワード値+1=攻撃回数 |
| 攻撃集中 | 第一移動放棄、攻撃判定難易度-1段階 |
| 戦術機動 | 巧NORMAL判定、機動力2倍、能動行動難易度+1段階 |
| 形代の死亡回避 | 現在HP×2超で2枚消費、各撃逐次 |
| まとめて回避 | モブ敵の同イニシ・同対象 |
| ハードモード | PC側ダメ0かつボス側ダメ0 |
| 結界設置 | 祓串→注連鋼縄→効果付与 |
| 難易度修正 | KIDS〜ULTRA_HARDクランプ |
| リスポーン | 半量回復、状態異常クリア、当ターン行動不可 |

---

## 20. 残課題（実装中に再検討する項目）

| 項目 | 対応時期 |
|---|---|
| 複合ダメージ式 | 必要時 |
| マルチセッション分散 | Phase 9 以降 |
| BCDice 連携 | コミュニティ要望時 |
| AIモデルベンチ | Phase 5 |
| リプレイ機能 | Phase 8 |
| モバイル対応 | フロントエンド側で検討 |

---

## 21. Claude Code への最終指示

実装に着手する際:

1. **まず `tacex_ws_schema_v1_0.md` を読む**: WebSocketメッセージの詳細はそちら
2. **次に `tacex_web_spec_v1_1.md` を読む**: フロントエンドとの整合確認のため
3. **Phase 0 から順次実装**: スキップしない
4. **疑問があれば止まる**: 仕様で曖昧な点を勝手に解釈しない
5. **テストを並行**: 各機能と同時にテストを書く
6. **MVP（Phase 2）を最優先**: それ以降の機能は MVP 動作後
7. **過剰最適化を避ける**: シンプルな実装を優先
8. **コミット粒度を細かく**: 各機能完成ごとにコミット

設計フェーズはここで完了する。**実装の途中で仕様の不備に気付いた場合のみ**、本仕様書を改訂する。

---

**以上、タクティカル祓魔師TRPG Headless AI-GM バックエンド 完全案件定義書 v2.5 (FINAL) を実装着手用最終版として固定する。**

総開発期間（バックエンド + フロントエンド並行）: 24〜30ヶ月。

設計フェーズ完了。次は Phase 0 実装開始。
