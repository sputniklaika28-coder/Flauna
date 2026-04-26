# タクティカル祓魔師TRPG フロントエンド 完全案件定義書 v1.1 (FINAL)

**最終更新**: 2026-04-25  
**ステータス**: 実装着手用最終版（Claude Code向け）  
**ペア仕様書**: `tacex_gm_spec_v2_5_FINAL.md`, `tacex_ws_schema_v1_0.md`

---

## ⚠️ Claude Code への重要指示

この仕様書は **Claude Code が実装を進めるための完全仕様** である。以下の原則を厳守すること:

1. **UXファースト**: TRPGプレイヤーのテンポを殺すUIは作らない
2. **MVP優先**: Phase 2 完了時点で「1vs1の戦闘がプレイ可能」が最重要
3. **過剰設計を避ける**: 楽観的UI更新の複雑な実装、不要な抽象化を勝手に追加しない
4. **段階的実装**: Phase 0 → 1 → 2 を順次完成させる
5. **疑問は止まる**: 仕様で曖昧な点は実装前に確認を求める
6. **テストと並行**: 各機能実装と同時にテストを書く
7. **依存最小化**: 仕様書に明記されていないライブラリは追加しない
8. **Udonariumの軽快さを守る**: 「3クリックで攻撃」を標準にする

---

## 0. 改訂履歴

| 版 | 日付 | 変更概要 |
|---|---|---|
| v1.0 | — | 初版 |
| v1.1 | 本版 | レビュー指摘を統合反映: ①Redux Toolkit から Zustand へ変更、②AtomicActionビルダーから「クイックアクション+詳細モーダル」へUX改善、③Konvaから PixiJS への変更検討（しかし v1.1 では Konva 維持、Phase 5以降で再検討）、④i18n を Phase 0 から導入、⑤楽観的UI更新を限定的に許容、⑥バックエンドv2.5の TurnAction 構造に対応、⑦MVP を Phase 2 に明確化、⑧工数を15〜20ヶ月に修正 |

---

## 1. プロジェクト概要

| 項目 | 内容 |
|---|---|
| プロジェクト名 | タクティカル祓魔師TRPG フロントエンド |
| 略称 | TacEx-Web |
| 開発対象 | Webブラウザフロントエンド |
| 目的 | バックエンド（TacEx-GM）と通信するTRPGクライアント |
| 対象システム | タクティカル祓魔師TRPG（コアルールブック Ver1.00 準拠） |
| 開発体制 | 単独開発 |
| 推定総工数 | **15〜20ヶ月**（フルタイム1名換算、リスクバッファ込み） |
| プラットフォーム | PCブラウザ（Chrome、Firefox） |
| 推奨ブラウザ | デスクトップ Chrome 最新版 |
| 想定スケール | 同時5〜10セッション（バックエンドと整合） |
| MVP定義 | Phase 2 完了時点で 1vs1 戦闘がプレイ可能 |

### 1-1. UI/UX参考対象: Udonarium Lily

ユドナリウムリリィを主要な UI/UX 参考対象とする。**特に「軽快さ」と「3クリックで攻撃」のテンポを重視**する。

---

## 2. システムコンセプト

### 2-1. 設計原則（v1.1 で再整理）

| 原則 | 説明 |
|---|---|
| **PXファースト** | プレイヤー体験 > 技術的純粋さ |
| **3クリックの軽快さ** | 「右クリック→攻撃→対象クリック」で完了する標準フロー |
| **スマートデフォルト** | 最後に使った武器・スタイルを記憶。モーダルは詳細調整のみ |
| **限定的楽観UI** | 自分の入力（送信中表示等）は楽観更新、ゲーム状態はサーバー応答待ち |
| **過剰抽象化を避ける** | Redux ではなく Zustand、最小の状態管理 |
| **MVP優先** | Phase 2 完了時点で動くものが最優先 |

### 2-2. アーキテクチャ

```
┌──────────────────────────────────────────────────────┐
│            ブラウザクライアント                          │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │      UIレイヤー（React Components）              │ │
│  │  ・Map / CharacterToken                         │ │
│  │  ・QuickActionMenu（軽快なコンテキストメニュー）   │ │
│  │  ・ActionDetailModal（必要時のみ詳細編集）        │ │
│  │  ・ChatPanel / NarrativeStream                  │ │
│  │  ・EvasionDialog / DeathAvoidanceDialog         │ │
│  └─────────────────────┬──────────────────────────┘ │
│                        │ Hooks                       │
│  ┌─────────────────────▼──────────────────────────┐ │
│  │       状態管理（Zustand）                       │ │
│  │  ・useGameStore（gameState）                    │ │
│  │  ・usePendingStore                              │ │
│  │  ・useUIStore（ローカルUI）                       │ │
│  │  ・useChatStore                                 │ │
│  │  ・useDraftStore（構築中のTurnAction）            │ │
│  └─────────────────────┬──────────────────────────┘ │
│                        │                              │
│  ┌─────────────────────▼──────────────────────────┐ │
│  │   通信レイヤー（カスタムWebSocketクライアント）     │ │
│  │  ・自動再接続バックオフ                            │ │
│  │  ・client_request_id 生成                       │ │
│  │  ・event_id 順序検証                             │ │
│  └─────────────────────┬──────────────────────────┘ │
└────────────────────────┼─────────────────────────────┘
                         │ WebSocket (JSON、別schema定義)
                         ▼
                ┌──────────────────────┐
                │  バックエンド          │
                │  (TacEx-GM v2.5)     │
                └──────────────────────┘
```

---

## 3. 技術スタック

### 3-1. v1.1 で変更された選択

| 用途 | v1.0 | v1.1 | 理由 |
|---|---|---|---|
| 状態管理 | Redux Toolkit | **Zustand** | WebSocketとの相性、ボイラープレート削減 |
| i18n | Phase 8 | **Phase 0 から react-i18next** | 後付け修正の高コスト回避 |
| マップ描画 | Konva | **Konva 維持、Phase 5でPixiJS再検討** | MVPでは Konva で十分 |

### 3-2. 確定技術スタック

| 技術 | 用途 | 備考 |
|---|---|---|
| TypeScript 5.x | 開発言語 | strict モード |
| React 18 | UIフレームワーク | hooks 中心 |
| Vite | ビルドツール | |
| **Zustand** | 状態管理 | Redux Toolkit から変更 |
| react-router-dom v6 | ルーティング | |
| TailwindCSS | スタイリング | |
| shadcn/ui | UIコンポーネント | （ヘッドレス、必要分のみ） |
| Zod | 入力バリデーション | |
| Konva (react-konva) | 2Dマップ Canvas描画 | Phase 5 で PixiJS 再検討 |
| Framer Motion | アニメーション | |
| **react-i18next** | **多言語化（Phase 0から）** | |
| Howler.js | 音声再生 | Phase 6 以降 |
| nanoid | client_request_id 生成 | |
| vitest + @testing-library/react | テスト | |
| Storybook | コンポーネントカタログ | |
| ws (Node.js) | WebSocketモックサーバ | テスト用 |
| Playwright | E2Eテスト | **Phase 3 から導入** |

### 3-3. 削除した技術

- ~~Redux Toolkit~~ : Zustand に変更
- ~~immer~~ : Zustand組み込みで不要
- ~~MSW (WebSocket mocking)~~ : 軽量な ws サーバ自作の方が確実

---

## 4. 画面構成

### 4-1. 全体レイアウト

```
┌────────────────────────────────────────────────────────┐
│ ヘッダー: ルーム名 / 接続状態 / 自分のキャラ名 / 設定         │
├──────────┬──────────────────────────┬─────────────────┤
│          │                          │                 │
│  サイド  │      マップ（中央）        │  チャット      │
│  メニュー │                          │  パネル        │
│          │                          │                 │
│  - 自分  │                          │  ────────       │
│    PC情報│                          │                 │
│  - イニシ │                          │  ナラティブ    │
│   アチブ  │                          │  履歴          │
│  - 戦闘  │                          │                 │
│    圧力  │                          │                 │
│          │                          │                 │
│          ├──────────────────────────┤                 │
│          │ クイックアクションバー       │                 │
│          │ (ターン中の主要アクション)  │                 │
└──────────┴──────────────────────────┴─────────────────┘
```

### 4-2. レスポンシブ方針

PC専用前提、最低解像度 1280×720。Phase 5 でタブレット対応検討。

---

## 5. 画面別詳細仕様

### 5-1. ロビー画面

```
┌──────────────────────────────────────┐
│  TacEx-GM へようこそ                  │
│                                      │
│  [新しいルームを作成]                  │
│                                      │
│  または既存のルームに参加:              │
│  ルームID: [___________]              │
│  プレイヤー名: [_______]              │
│  [参加]                              │
└──────────────────────────────────────┘
```

機能:
- ルーム作成: `POST /rooms` → master_token 取得
- ルーム参加: `POST /rooms/{id}/join` → player_token 取得
- トークン保存: sessionStorage

### 5-2. ルーム画面 - メイン

#### 5-2-1. マップエリア

| 機能 | 仕様 |
|---|---|
| グリッド表示 | 1マス40px（拡大縮小30〜64px） |
| 障害物・オブジェクト | グレー背景＋アイコン |
| キャラコマ | 立ち絵サムネイルまたは色付き円。HP/MPバー |
| 結界 | 半透明オーバーレイ（Phase 4以降） |
| 射程範囲表示 | 武器選択時にハイライト |
| 移動範囲表示 | 自ターン中、移動可能マスをハイライト |
| 射線表示 | 遠隔攻撃ターゲット選択時、射線を線で表示 |
| 自分のPCのフォーカス | 細い枠 |
| 現在手番のハイライト | 目立つ枠 |
| ダメージエフェクト | ダメージ受けたコマに数値ポップアップ |

#### 5-2-2. クイックアクションメニュー（**v1.1 の主要改善**）

レビュー指摘を反映、Udonarium Lily の軽快さを取り戻す。コマ右クリックで開くメニュー:

```
┌──────────────┐
│ 怨霊武者         │  ← 敵を右クリック
├──────────────┤
│ 攻撃する 🗡️    │  ← デフォルト武器・スタイルで即実行
│ 詳細攻撃 ⚙    │  ← モーダル開いて詳細調整
│ ─────────── │
│ 詳細を表示     │
│ ターゲットに設定│
└──────────────┘
```

**「攻撃する」**を選ぶと、**スマートデフォルト**で即座に攻撃を実行:
- 武器: 装備中の最初の武器
- スタイル: 通常攻撃
- ダイス分配: 単発（連撃なら均等割り）
- → そのまま `submit_turn_action` 送信

これで「3クリックで攻撃」を達成（右クリック → 攻撃する → 確認なしで実行、または1クリック確認）。

**「詳細攻撃」**を選ぶと、従来のモーダル（§5-2-3）が開く。

#### 5-2-3. 詳細アクションモーダル（必要時のみ）

スタイルやダイス分配を細かく調整したい時のみ使用。

```
┌────────────────────────────────────────┐
│  近接攻撃の設定                          │
│  ─────────────────────                 │
│  使用祭具: [中型近接祭具 ▼]              │
│  スタイル:                              │
│    ◉ 通常                              │
│    ○ 連撃                              │
│    ○ 精密攻撃                          │
│    ○ 強攻撃                            │
│                                        │
│  [自動分配 ✨]   ← Phase 3で連撃時に表示  │
│                                        │
│  ターゲット:                            │
│    [マップでクリック] 怨霊武者 [×]        │
│                                        │
│  予測:                                  │
│    難易度: NORMAL                       │
│    成功確率: 約88%                      │
│                                        │
│  [キャンセル] [送信]                    │
└────────────────────────────────────────┘
```

**「自動分配」ボタン**: ダイスを均等割りする（プレイヤーの操作負担軽減）。

#### 5-2-4. 自分のPCのターン時メニュー

ターン中のクイックアクションバー（マップ下に常駐）:

```
[ 移動 ] [ 攻撃 ] [ 戦術機動 ] [ 攻撃集中 ] [ 結界 ] [ 術 ] [ 手番終了 ]
   ↑この順番でフロー的にアクションを組み立てる
```

各ボタンを押すと該当のミニウィザードが起動。

#### 5-2-5. チャットパネル

```
┌────────────────────────────────┐
│ 全体 / パーティ / 秘話            │
├────────────────────────────────┤
│ 🤖 GM:                          │
│  アリスの祓串が空を切る...        │
│                                 │
│ 👤 アリス:                       │
│  くっ、堅いな…                  │
│                                 │
│ ⚔ システム:                     │
│  攻撃判定: 成功 / 回避: 成功      │
├────────────────────────────────┤
│ [____________________]          │
│   :HP-3 などの操作も可（Phase 4）│
│                          [送信] │
└────────────────────────────────┘
```

#### 5-2-6. サイドメニュー

```
┌──────────────────────┐
│ ▼ アリス（あなた）       │
│  HP: 7/8  ━━━━━━━─    │
│  MP: 4/5  ━━━━━━━━━    │
│  回避: 3/5 ●●●○○        │
│  形代: 7枚                │
│  状態: なし             │
├──────────────────────┤
│ ▼ ターン順              │
│  1. 怨霊武者 (現在)     │
│  2. アリス (次)         │
├──────────────────────┤
│ ▼ ハードモード         │  ← Phase 6
│  Normal                 │
│  ノーダメ: 0/2          │
└──────────────────────┘
```

### 5-3. 割り込みダイアログ

#### 5-3-1. 回避要求ダイアログ

```
┌────────────────────────────────────────┐
│  ⚠️ 回避が必要です                       │
│  ─────────────────────                 │
│  攻撃元: 怨霊武者                        │
│  攻撃数: 1                              │
│  期待ダメージ: 約4                       │
│                                        │
│  あなたの残り回避ダイス: 5個             │
│                                        │
│  使用ダイス: [3] /─\━━━━━━━━           │
│  または                                 │
│  [自動 ✨] [全力で躱す] [回避放棄]       │
│                                        │
│  ⏱ 残り時間: 45秒                       │
│                                        │
│  [送信]                                 │
└────────────────────────────────────────┘
```

**重要なUX改善（v1.1）**:
- 「自動」ボタン: バックエンドのNPC回避ヒューリスティックと同じロジックで推奨ダイス数を計算
- 「全力で躱す」ボタン: 残り回避ダイス全部を投入
- 「回避放棄」ボタン: ダイス0個で送信

これで「3クリックで回避」を達成。

#### 5-3-2. 死亡回避ダイアログ（Phase 4以降）

```
┌────────────────────────────────────────┐
│  💀 致命傷！                             │
│  ─────────────────────                 │
│  受けるダメージ: 12点                    │
│  あなたの現在HP: 5（HP×2超 → 形代2枚）   │
│  残り形代: 7枚                          │
│                                        │
│  ◉ 形代2枚消費して死亡回避               │
│  ○ 形代2枚消費してリスポーン地点に転移   │
│  ○ 受け入れる（キャラクター完全死亡）    │
│                                        │
│  ⏱ 残り時間: 45秒                       │
│                                        │
│  [送信]                                 │
└────────────────────────────────────────┘
```

### 5-4. 設定モーダル

| 設定 | 内容 | Phase |
|---|---|---|
| プレイヤー名変更 | セッション中変更可 | 0 |
| 立ち絵アップロード | | 4 |
| サウンド設定 | BGM/SE音量 | 6 |
| 言語設定 | 日本語/英語 | 0 |
| マップズーム | 30〜64px | 1 |
| ヘルプ | ルール参照 | 1 |
| 退出 | 接続切断 | 0 |

---

## 6. 状態管理（Zustand）

### 6-1. ストア設計

レビュー指摘を反映、Redux Toolkit から Zustand に変更。複数のスライスを単純なストアに統合。

```typescript
// src/stores/gameStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface GameStore {
  // バックエンドから受信したGameStateのミラー
  gameState: GameState | null;
  
  // 接続状態
  connectionStatus: 'CONNECTING' | 'AUTHENTICATING' | 'ACTIVE' | 'DISCONNECTED' | 'SESSION_LOST';
  lastSeenEventId: number;
  
  // アクション
  setGameState: (state: GameState) => void;
  applyEvent: (event: GameEvent) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}

export const useGameStore = create<GameStore>()(
  devtools(
    (set, get) => ({
      gameState: null,
      connectionStatus: 'DISCONNECTED',
      lastSeenEventId: 0,
      
      setGameState: (state) => set({ gameState: state }),
      applyEvent: (event) => {
        // イベント種別に応じて状態を更新
        // ...
      },
      setConnectionStatus: (status) => set({ connectionStatus: status }),
    }),
    { name: 'gameStore' }
  )
);
```

### 6-2. ストア構成

| ストア | 内容 |
|---|---|
| useGameStore | gameState、connectionStatus、lastSeenEventId |
| usePendingStore | EvasionRequest, DeathAvoidanceRequest |
| useUIStore | 選択中のキャラ、表示中のモーダル、マップズーム |
| useDraftStore | 構築中の TurnAction |
| useChatStore | メッセージ履歴 |

各ストアは独立しており、フック経由でアクセス。

### 6-3. WebSocketクライアント

Redux ミドルウェアではなく、独立したクラスとして実装:

```typescript
// src/services/websocket.ts
class TacExWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempt = 0;
  
  connect(roomId: string, token: string, lastEventId: number) {
    this.ws = new WebSocket(`wss://server/room/${roomId}`);
    
    this.ws.onopen = () => {
      this.send({
        action: 'join_room',
        room_id: roomId,
        auth_token: token,
        last_seen_event_id: lastEventId,
      });
    };
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };
    
    this.ws.onclose = (event) => {
      this.handleClose(event);
    };
  }
  
  send(message: ClientMessage) {
    // client_request_id 自動付与
    const payload = {
      ...message,
      client_request_id: nanoid(),
    };
    this.ws?.send(JSON.stringify(payload));
  }
  
  private handleMessage(msg: ServerMessage) {
    // メッセージ種別ごとに該当ストアを更新
    switch (msg.type) {
      case 'session_restore':
        useGameStore.getState().setGameState(msg.current_state);
        break;
      case 'state_update':
        useGameStore.getState().applyStateUpdate(msg.patch);
        break;
      case 'gm_narrative':
        useChatStore.getState().addMessage(msg);
        break;
      // ...
    }
  }
  
  private handleClose(event: CloseEvent) {
    // close codeに応じた処理
    if (event.code === 4001 || event.code === 4002) {
      useGameStore.getState().setConnectionStatus('SESSION_LOST');
    } else {
      this.reconnect();
    }
  }
  
  private async reconnect() {
    const delays = [1000, 2000, 4000, 8000, 16000];
    if (this.reconnectAttempt >= delays.length) {
      useGameStore.getState().setConnectionStatus('SESSION_LOST');
      return;
    }
    await sleep(delays[this.reconnectAttempt]);
    this.reconnectAttempt++;
    this.connect(/* ... */);
  }
}
```

### 6-4. 楽観的UI更新の方針（v1.1 で限定的緩和）

レビュー指摘を反映、UX 向上のため**送信中インジケータ**と**自分の操作の即時反映**を限定的に許可:

**楽観的更新する操作:**
- 送信中インジケータ（ボタン無効化、「送信中...」表示）
- 自分のキャラの選択状態
- マップズーム
- モーダル開閉
- ドラフト編集（構築中のTurnAction）
- 回避ダイアログでの「使用ダイス」表示

**楽観的更新しない操作:**
- HP/MP/位置/装備等のゲーム状態の変更（必ずサーバー応答待ち）
- 攻撃判定や回避判定の結果
- ダメージ計算

### 6-5. event_id 順序検証

サーバー受信メッセージで `event_id` が前回より小さい場合:
- console.warn で記録
- 通常運用は継続（再接続のリプレイ等で起きうる）

---

## 7. 通信レイヤー

### 7-1. WebSocketプロトコル

詳細は **`tacex_ws_schema_v1_0.md`** を参照。本仕様書では概要のみ。

#### 7-1-1. 接続フロー

```
1. ロビーで POST /rooms または POST /rooms/{id}/join → token取得
2. WebSocket 接続: wss://server/room/{room_id}
3. join_room メッセージ送信
4. session_restore 受信 → ストア初期化 → ルーム画面遷移
```

#### 7-1-2. 再接続

```typescript
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]; // ms
const TOTAL_TIMEOUT = 60000; // 60秒
```

60秒で諦めて session_lost 画面表示。

#### 7-1-3. close codeハンドリング

| code | UI挙動 |
|---|---|
| 1000 | 通常終了、ロビーへ |
| 4000 | 認証失敗、ロビーへ |
| 4001 | 60秒超切断、session_lost画面 |
| 4002 | サーバー再起動、session_lost画面 |
| 4003 | バッファ超過、再接続 |
| 4004 | レート制限、10秒待機 |
| 4005 | 重複接続、警告表示 |

### 7-2. メッセージ送受信

詳細は別仕様書 (`tacex_ws_schema_v1_0.md`) 参照。

### 7-3. 冪等性

全送信に `client_request_id` (nanoid) を付与。サーバー側で重複検出。

### 7-4. VERSION_MISMATCH 処理

レビュー指摘を反映、UX を改善:

```typescript
// VERSION_MISMATCH 受信時
function handleVersionMismatch(detail: { current_version: number }) {
  // 1. ドラフトを保持
  const draft = useDraftStore.getState().draft;
  
  // 2. 最新stateで draft が valid か再チェック
  const validation = validateDraftAgainstState(draft, useGameStore.getState().gameState);
  
  // 3. valid なら自動再送信（プレイヤー負担なし）
  if (validation.valid) {
    showToast({ severity: 'info', message: '最新状態で再送信します' });
    submitTurnAction(draft);
    return;
  }
  
  // 4. invalid ならドラフトをクリーンアップして再編集を促す
  showToast({ 
    severity: 'warning', 
    message: '他プレイヤーの行動で状態が変わりました。再構築してください。',
  });
  // ドラフト保持、UIフォーカスを行動エリアに
}
```

これにより「同じ操作を2回」の最悪UXを回避。

---

## 8. UI コンポーネント設計

### 8-1. コンポーネント階層

```
<App>
  <Router>
    <Lobby />
    <Room>
      <Header />
      <Layout>
        <SideMenu />
        <CenterArea>
          <Map>
            <Grid />
            <CharacterTokens />
            <RangeOverlay />
            <DamagePopups />
          </Map>
          <QuickActionBar />
        </CenterArea>
        <ChatPanel />
      </Layout>
      <Modals>
        <QuickActionContextMenu />
        <ActionDetailModal />
        <EvasionDialog />
        <DeathAvoidanceDialog />
        <CharacterDetailModal />
        <SettingsModal />
      </Modals>
      <Toasts />
    </Room>
  </Router>
</App>
```

### 8-2. 主要コンポーネント

#### Map (Konvaベース)
- グリッド描画、キャラコマ、範囲ハイライト
- クリック・右クリック・ドラッグ対応

#### QuickActionContextMenu
- 軽量、3クリックで完了するメニュー
- スマートデフォルトで「攻撃する」を即実行

#### QuickActionBar
- ターン中の常駐バー
- フロー的にアクションを組み立てる

#### EvasionDialog
- 60秒タイマー
- 「自動」「全力」「放棄」のクイック選択
- 詳細はスライダーで調整

### 8-3. アニメーション

| 場面 | アニメーション | Phase |
|---|---|---|
| ダメージ表示 | 数値ポップアップ + フェードアウト | 2 |
| キャラ揺れ | ダメージ受領時の揺れ | 2 |
| 移動 | 経路に沿ったtween | 2 |
| 結界出現 | フェードイン + パルス | 4 |
| カットイン（術発動等） | フルスクリーンエフェクト | 5 |

### 8-4. 演出スコープ（Phase別）

| Phase | 演出 |
|---|---|
| Phase 0〜2 | 機能のみ、最低限のフィードバック |
| Phase 3〜4 | 立ち絵差分、ダメージエフェクト、移動アニメ |
| Phase 5〜6 | カットイン、ハードモード演出 |
| Phase 7〜 | BGM、SE、追加カットイン |

---

## 9. UX フロー図

### 9-1. PCの戦闘ターン（v1.1 簡素化版）

```
[自分のターン開始]
    ↓ サイドメニューに「あなたの番」表示
[マップ上の敵を右クリック]
    ↓ クイックアクションメニュー表示
[「攻撃する」をクリック]
    ↓ スマートデフォルトで即送信
    ↓ または「詳細攻撃」で調整モーダル
[サーバー処理]
    ↓ 命中判定
    ↓ NPCの回避判定（自動）
[gm_narrative 受信]
    ↓ チャットに描写表示
    ↓ ダメージエフェクト
[ターン終了]
```

3クリック完結（右クリック → 攻撃する → ターゲット確認）。

### 9-2. 敵NPCのターン（自分が攻撃対象）

```
[NPC ターン開始]
    ↓ 「GM考え中」表示（最大10秒）
    ↓ NPCが攻撃を実行
[evade_required 受信]
    ↓ EvasionDialog 表示
[「自動」ボタン]
    ↓ 推奨ダイス数で送信
    ↓ または手動調整
[回避判定]
    ↓ ダメージ確定
[gm_narrative 受信]
    ↓ チャットに描写
[ターン終了]
```

### 9-3. 切断と再接続

```
[突然の切断]
    ↓ 接続状態インジケータが赤
    ↓ トースト「再接続中...」
[再接続試行]
    ↓ 60秒以内に成功
[session_restore 受信]
    ↓ 状態復元
    ↓ pending_for_you があれば該当ダイアログ再表示
[通常運用復帰]

または

[60秒超切断]
[session_lost画面表示]
```

---

## 10. エラーハンドリング

### 10-1. エラーコード対応

詳細は `tacex_ws_schema_v1_0.md` 参照。主なものだけ抜粋:

| ErrorCode | UI挙動 |
|---|---|
| AUTH_INVALID_TOKEN | エラー表示、ロビーへ |
| ROOM_NOT_FOUND | エラー表示、ロビーへ |
| OUT_OF_TURN | トースト「あなたの番ではありません」 |
| VERSION_MISMATCH | §7-4 の自動再送信ロジック |
| INVALID_PATH | 「その経路は移動できません」 |
| INSUFFICIENT_MP | 「MPが足りません」 |
| AI_FALLBACK | majorのみトースト「AI処理にエラー」 |

### 10-2. 多言語対応（**v1.1 で Phase 0 から導入**）

レビュー指摘を反映、後付けの高コスト回避のため Phase 0 から `react-i18next` を導入:

```typescript
// src/i18n/ja.ts
export const ja = {
  errors: {
    OUT_OF_TURN: 'あなたの番ではありません',
    INVALID_PATH: 'その経路は移動できません',
    // ...
  },
  combat: {
    evasion_title: '回避が必要です',
    // ...
  },
};

// src/i18n/en.ts (Phase 8 で本格対応)
export const en = {
  errors: {
    OUT_OF_TURN: "It's not your turn",
    // ...
  },
};
```

Phase 0 では日本語のみだが、**全テキストを `t("key")` で書く習慣**をつける。これにより Phase 8 の多言語対応コストを 1/10 に削減。

### 10-3. オフライン検知

`navigator.onLine` と WebSocket切断を組み合わせて検知。

---

## 11. 開発マイルストーン（**v1.1 で工数現実化**）

### 11-1. Phase別工数

| Phase | 内容 | 工数 |
|---|---|---|
| Phase 0 | プロジェクト雛形、ロビー、WebSocket、認証、i18n基盤、ハッピーパス結合 | 4〜6週 |
| Phase 1 | 状態管理基盤（Zustand）、基本UI骨格、Storybook | 6〜8週 |
| Phase 2 | **MVP: マップ表示、クイックアクション、1vs1戦闘UI** | 8〜10週 |
| Phase 3 | TurnAction 完全版UI、連撃、戦術機動、ダイス分配、E2E導入 | 10〜12週 |
| Phase 4 | 結界UI、立ち絵差分、形代システム | 8〜10週 |
| Phase 5 | 祓魔術UI、カットイン演出、PixiJS再検討 | 10〜12週 |
| Phase 6 | ハードモード、複数プレイヤー協調 | 8〜10週 |
| Phase 7 | 査定UI、成長UI | 6〜8週 |
| Phase 8 | 多言語本格対応、永続化UI、モバイル対応 | 8〜10週 |
| Phase 9 | 統合テスト、UX改善、BGM/SE | 4〜6週 |

**合計: 72〜92週（16〜21ヶ月）**

これは v1.0 の「9〜12ヶ月」から **倍増近い**。レビュー指摘により現実化。

### 11-2. Phase 0 完了条件

1. プロジェクト雛形（Vite, TypeScript, ESLint, Prettier 設定）
2. ルーティング基本（ロビー / ルーム）
3. ロビー画面（ルーム作成・参加フォーム）
4. 認証API呼び出し
5. WebSocket接続層（接続、再接続、close codeハンドリング）
6. join_room メッセージ送信、session_restore 受信
7. **i18n基盤**: react-i18next 導入、全テキストを `t()` で書く習慣
8. **ハッピーパス結合テスト**: モックバックエンド相手に、ロビー→接続→簡易マップ表示→1メッセージ送受信

バックエンドの Phase 0 ハッピーパスと協調。

### 11-3. Phase 2 MVP 完了条件（**最重要マイルストーン**）

これだけ動けばリリース可能:

- ロビー → 接続 → ルーム参加 → セッション開始
- マップ表示（PC 1人 + NPC 1体）
- 自ターン: マップで右クリック→「攻撃する」で即送信
- 回避要求 → 「自動」ボタンで即送信
- ダメージ反映、HP表示更新
- ナラティブ表示（テンプレでもOK）
- HP 0 で死亡フラグ立つ
- 戦闘終了表示

**MVPで動かないこと:**
- 連撃、戦術機動、攻撃集中の選択UI（Phase 3）
- 結界UI（Phase 4）
- 祓魔術UI（Phase 5）
- 形代消費UI（Phase 4）
- 立ち絵差分（Phase 4）
- BGM/SE（Phase 6）
- 多言語UI（テキストは `t()` で書くが英語版は Phase 8）

### 11-4. クリティカルパス

- Phase 0 → 1 → 2 が前提条件チェーン
- Phase 3 以降は MVP 動作確認後に着手
- バックエンドの Phase 2 完成を待ってフロントエンド Phase 2 を本格化（並行不可な部分あり）

### 11-5. バックエンドとの並行戦略

レビュー指摘を反映、現実的な並行戦略を設定:

| バックエンド | フロントエンド | 戦略 |
|---|---|---|
| Phase 0（4〜6週） | Phase 0（4〜6週） | 並行可。両者ハッピーパス結合テストで合流 |
| Phase 1（8〜10週） | Phase 1（6〜8週） | フロント先行、バックエンドモック相手に進める |
| Phase 2（6〜8週） | Phase 2（8〜10週） | バックエンド先行、フロントは本格化 |
| Phase 3以降 | Phase 3以降 | バックエンド完成を待ってフロント着手 |

総開発期間（並行込み）: **20〜26ヶ月**

---

## 12. テスト戦略

### 12-1. ユニットテスト

| 対象 | 戦略 |
|---|---|
| Zustand ストア | 純粋関数テスト |
| Selector | createSelector のテスト |
| Utility 関数 | 距離計算、座標変換 |
| Custom Hooks | renderHook |

### 12-2. コンポーネントテスト

| 対象 | 戦略 |
|---|---|
| プレゼンテーショナル | Storybook |
| インタラクティブ | @testing-library/react + user-event |
| EvasionDialog | タイマー動作、配分計算 |
| QuickActionMenu | スマートデフォルトの動作 |

### 12-3. 統合テスト（軽量WSモック使用）

レビュー指摘を反映、MSWではなく軽量な ws サーバを自作:

```typescript
// tests/fixtures/mock_ws_server.ts
import { WebSocketServer } from 'ws';

export class MockWSServer {
  private wss: WebSocketServer;
  private responseQueue: ServerMessage[] = [];
  
  start(port: number = 0) {
    this.wss = new WebSocketServer({ port });
    this.wss.on('connection', (ws) => {
      ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        this.handleClientMessage(ws, msg);
      });
    });
  }
  
  enqueueResponse(message: ServerMessage) {
    this.responseQueue.push(message);
  }
  
  // ... テスト用ヘルパー
}
```

### 12-4. E2Eテスト（**v1.1 で Phase 3 に前倒し**）

レビュー指摘を反映、E2EをPhase 9からPhase 3に前倒し:

| Phase | E2E スコープ |
|---|---|
| Phase 3 | スモークテスト（接続→1ターン戦闘→描写） |
| Phase 5 | 主要機能（祓魔術、結界、複数プレイヤー） |
| Phase 9 | 長時間、エッジケース |

### 12-5. ビジュアル回帰テスト

Storybook + Chromatic で Phase 5 から導入。

---

## 13. ディレクトリ構成

```
tacex-web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── README.md
├── public/
│   └── assets/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── i18n/                     # Phase 0から
│   │   ├── index.ts
│   │   ├── ja.ts
│   │   └── en.ts                 # Phase 8で本格化
│   ├── routes/
│   │   ├── Lobby.tsx
│   │   └── Room.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── SideMenu.tsx
│   │   │   ├── CenterArea.tsx
│   │   │   └── ChatPanel.tsx
│   │   ├── map/
│   │   │   ├── Map.tsx
│   │   │   ├── Grid.tsx
│   │   │   ├── CharacterToken.tsx
│   │   │   ├── RangeOverlay.tsx
│   │   │   ├── LineOfSightOverlay.tsx
│   │   │   └── DamagePopup.tsx
│   │   ├── action/
│   │   │   ├── QuickActionContextMenu.tsx  # 右クリックメニュー
│   │   │   ├── QuickActionBar.tsx          # 常駐バー
│   │   │   ├── ActionDetailModal.tsx       # 詳細編集モーダル
│   │   │   ├── DiceDistributionSlider.tsx
│   │   │   └── builders/                    # Phase 3以降
│   │   │       ├── MeleeAttackBuilder.tsx
│   │   │       ├── RangedAttackBuilder.tsx
│   │   │       ├── CastArtBuilder.tsx
│   │   │       └── ...
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── ChatInput.tsx
│   │   ├── dialogs/
│   │   │   ├── EvasionDialog.tsx
│   │   │   ├── DeathAvoidanceDialog.tsx
│   │   │   ├── CharacterDetailModal.tsx
│   │   │   └── SettingsModal.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Slider.tsx
│   │       └── Modal.tsx
│   ├── stores/
│   │   ├── gameStore.ts
│   │   ├── pendingStore.ts
│   │   ├── uiStore.ts
│   │   ├── draftStore.ts
│   │   └── chatStore.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── websocket.ts          # WebSocketクライアント
│   │   └── token.ts
│   ├── types/
│   │   ├── server.ts             # サーバー側との共有型
│   │   ├── ui.ts
│   │   └── actions.ts
│   ├── utils/
│   │   ├── geometry.ts
│   │   ├── validation.ts
│   │   ├── dice.ts
│   │   └── format.ts
│   ├── hooks/
│   │   ├── useTimer.ts
│   │   └── useWebSocket.ts
│   └── styles/
│       └── globals.css
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/                       # Phase 3から
│   └── fixtures/
│       └── mock_ws_server.ts
└── .storybook/
    └── main.ts
```

---

## 14. 確定事項一覧（v1.1 最終版）

| # | 項目 | 決定内容 |
|---|---|---|
| FE-D1 | フロントエンド技術 | React 18 + TypeScript + Vite |
| FE-D2 | 状態管理 | **Zustand（v1.1で Redux Toolkit から変更）** |
| FE-D3 | スタイリング | TailwindCSS + shadcn/ui |
| FE-D4 | マップ描画 | Konva、Phase 5 で PixiJS 再検討 |
| FE-D5 | アニメーション | Framer Motion |
| FE-D6 | 入力バリデーション | Zod |
| FE-D7 | UI参考対象 | Udonarium Lily（軽快さ重視） |
| FE-D8 | プラットフォーム | PCブラウザ専用、Phase 8でモバイル検討 |
| FE-D9 | 行動入力方式 | **クイックアクション + 詳細モーダル（v1.1で改善）** |
| FE-D10 | UIレイアウト | モダン固定レイアウト + 詳細モーダル |
| FE-D11 | GM描写表示 | チャット欄に流す |
| FE-D12 | 演出スコープ | 中間（立ち絵 + ダメージエフェクト） |
| FE-D13 | 楽観的UI更新 | **限定的に許容（v1.1で緩和）** |
| FE-D14 | 再接続タイムアウト | 60秒 |
| FE-D15 | 多言語対応 | **Phase 0 から react-i18next 導入（v1.1で前倒し）** |
| FE-D16 | session_lost対応 | 専用画面、ロビーへ |
| FE-D17 | VERSION_MISMATCH対応 | **自動再送信ロジック（v1.1で改善）** |
| FE-D18 | 立ち絵差分 | Phase 4 |
| FE-D19 | エラーコード | バックエンドErrorCodeと整合 |
| FE-D20 | テスト戦略 | Vitest + Storybook + 自作WSモック + Playwright(Phase 3〜) |
| FE-D21 | コンポーネントカタログ | Storybook |
| FE-D22 | デバッグ | Zustand DevTools |
| FE-D23 | 想定スケール | 同時5〜10セッション |
| **FE-D24** | **MVP定義** | **Phase 2 完了時点で 1vs1 戦闘がプレイ可能** |
| **FE-D25** | **工数見積もり** | **72〜92週（16〜21ヶ月）に現実化** |
| **FE-D26** | **クイックアクション** | **「3クリックで攻撃」を標準に。詳細はモーダル** |
| **FE-D27** | **WSモック** | **MSW ではなく自作 ws サーバ（軽量）** |
| **FE-D28** | **WebSocketスキーマ** | **別ファイル `tacex_ws_schema_v1_0.md` で凍結** |
| **FE-D29** | **E2Eテスト** | **Phase 3 から導入（v1.0 のPhase 9から前倒し）** |
| **FE-D30** | **TurnAction構造** | **バックエンドv2.5の単一構造化コマンドに対応（AtomicActionリストではない）** |

---

## 15. バックエンドとの整合性チェックリスト

### 15-1. WebSocketプロトコル整合

| 項目 | バックエンド v2.5 | フロントエンド v1.1 | 整合 |
|---|---|---|---|
| 接続URL | wss://server/room/{id} | 同じ | OK |
| メッセージスキーマ | `tacex_ws_schema_v1_0.md` | 同じ | OK |
| 再接続タイムアウト | 60秒 | 60秒 | OK |
| close code | 1000-4005 | 全対応 | OK |
| ハートビート | TCP+標準ping依存 | 同様 | OK |
| バックプレッシャー | 100件で強制切断 | 切断対応 | OK |
| client_request_id | 全送信に必須 | nanoid生成 | OK |
| expected_version | submit_turn_action | 全送信に付与 | OK |
| TurnAction構造 | first_move/main_action/second_move | 同じ | OK |

### 15-2. TurnAction整合（v1.0 から変更）

v2.5 で AtomicActionリスト方式が撤回され、`first_move/main_action/second_move/sub_actions` の構造に戻ったので、フロントエンドビルダーも単一の TurnAction を構築する形式に対応。

| MainAction型 | バックエンド | フロントエンド ビルダー | Phase |
|---|---|---|---|
| MeleeAttack | OK | MeleeAttackBuilder | 2 |
| RangedAttack | OK | RangedAttackBuilder | 3 |
| PegAttack | OK | (組み込み) | 2 |
| CastArt | OK | CastArtBuilder | 5 |
| DeployWire | OK | DeployWireBuilder | 4 |
| DispelBarrier | OK | (右クリック) | 4 |
| UseItem | OK | UseItemBuilder | 4 |
| OtherAction | OK | OtherActionBuilder | 3 |
| Skip | OK | (手番終了ボタン) | 2 |

### 15-3. エラーコード整合

`tacex_ws_schema_v1_0.md` で全 ErrorCode を共通定義。両仕様書から参照。

---

## 16. UDONARIUM LILY からの取り入れ詳細（変更なし）

| 機能 | 対応 |
|---|---|
| 3要素レイアウト | §4-1 で踏襲 |
| コマ右クリック | クイックアクションメニュー |
| HP/MPバー | CharacterToken |
| バフ・デバフ | 状態異常表示（Phase 4） |
| 立ち絵差分 | Phase 4 |
| 射程ハイライト | RangeOverlay |
| ターゲット機能 | 行動構築UI |
| アラームタイマー | EvasionDialog の60秒タイマー |
| カットイン演出 | Phase 5 |

---

## 17. アクセシビリティと UX 配慮

### 17-1. v1.1 で前倒し

| 項目 | v1.0 | v1.1 |
|---|---|---|
| キーボード操作 | Phase 4以降 | Phase 1 から段階的 |
| スクリーンリーダー | Phase 8 | aria-* は Phase 0 から |
| 色覚多様性 | Phase 8 | Phase 5 |
| フォントサイズ | Phase 8 | Phase 5 |

---

## 18. パフォーマンス目標

レビュー指摘を反映し、現実的な値に調整:

| 指標 | 目標 |
|---|---|
| 初回ロード時間 | 5秒以内（v1.0の3秒から緩和） |
| マップ描画 FPS | 30fps以上（v1.0の60fpsから緩和、Konvaの限界考慮） |
| メッセージ表示遅延 | 受信から200ms以内 |
| 60秒間のメモリ増加 | 80MB以内 |
| WebSocket接続確立 | 2秒以内 |
| バンドルサイズ（gzip後） | 800KB以内（v1.0の500KBから緩和、Konva込みのため） |

---

## 19. 残課題

| 項目 | 対応時期 |
|---|---|
| モバイル対応 | Phase 8 |
| 多言語対応の本格化 | Phase 8（仕組みは Phase 0 から） |
| 3Dマップ | Phase 9 以降 |
| BGM/SE | Phase 6 |
| カットイン演出 | Phase 5 |
| チャットパレット | Phase 4 |
| ボイスチャット | スコープ外 |

---

## 20. Claude Code への最終指示

実装に着手する際:

1. **`tacex_ws_schema_v1_0.md` を最初に読む**: WebSocketメッセージの詳細はそちら
2. **`tacex_gm_spec_v2_5_FINAL.md` を読む**: バックエンドとの整合確認
3. **Phase 0 から順次実装**: スキップしない
4. **i18n基盤を Phase 0 で導入**: 全テキストを `t()` で書く習慣をつける
5. **MVP（Phase 2）優先**: それ以降の機能は MVP 動作後
6. **クイックアクションの軽快さを守る**: 「3クリックで攻撃」を標準に
7. **テストを並行**: 各機能と同時にテスト
8. **疑問は止まる**: 仕様で曖昧な点を勝手に解釈しない
9. **Storybookでコンポーネント管理**: Phase 1 から構築
10. **モックバックエンドで先行開発**: バックエンド完成を待たずに進める

---

**以上、フロントエンド案件定義書 v1.1 (FINAL) を実装着手用最終版として固定する。**

総開発期間（バックエンド v2.5 + フロントエンド v1.1 並行）: **20〜26ヶ月**。

設計フェーズ完了。次は Phase 0 実装開始。
