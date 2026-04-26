# Flauna

タクティカル祓魔師TRPG Headless AI-GM + Web クライアント モノレポ

## 構成

```
apps/gm/          Python/FastAPI バックエンド (TacEx-GM)
apps/web/         React/Vite/TypeScript フロントエンド (TacEx-Web)
packages/ws-schema/  Pydantic → JSON Schema → Zod/TS 共有スキーマ
docs/             仕様書 (WS スキーマが唯一の通信契約)
```

## 仕様書

- [WebSocket スキーマ v1.0 (FINAL)](docs/tacex_ws_schema_v1_0.md) — **唯一の通信契約**
- [GM バックエンド仕様 v2.5 (FINAL)](docs/tacex_gm_spec_v2_5_FINAL.md)
- [Web フロントエンド仕様 v1.1 (FINAL)](docs/tacex_web_spec_v1_1_FINAL.md)

## 必要環境

| ツール | バージョン |
|--------|-----------|
| Python | 3.11 |
| uv     | 最新 |
| Node.js | 20 |
| pnpm   | 9+ |

## GM サーバー起動

```bash
cd apps/gm
uv sync
uv run uvicorn tacex_gm.main:app --reload --port 8000
# http://localhost:8000/health
```

## Web クライアント起動

```bash
pnpm install
pnpm -F web dev
# http://localhost:5173
```

## スキーマ同期

```bash
bash packages/ws-schema/scripts/generate.sh
bash packages/ws-schema/scripts/check.sh   # exit 0 = OK
```

## テスト

```bash
# GM
cd apps/gm && uv run pytest

# Web
pnpm -F web test
pnpm -F web typecheck
pnpm -F web build
```

## Phase 0 動作確認

```bash
# 1. GM ヘルスチェック
curl http://localhost:8000/health

# 2. ルーム作成 (WS スキーマ §2-1 形式で応答)
curl -X POST http://localhost:8000/api/v1/rooms \
  -H 'content-type: application/json' \
  -d '{"scenario_id":"first_mission","player_name":"GM"}'

# 3. Web ロビー表示
open http://localhost:5173
```
