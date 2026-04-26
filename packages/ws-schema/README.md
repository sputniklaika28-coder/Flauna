# @flauna/ws-schema

Pydantic → JSON Schema → TypeScript/Zod 共有スキーマパッケージ

## 生成チェーン

```
apps/gm/src/tacex_gm/ws/messages.py  (Pydantic モデル — 一次定義)
  ↓ apps/gm/tools/export_schemas.py
packages/ws-schema/schemas/*.json    (JSON Schema — git 管理)
  ↓ json-schema-to-typescript / json-schema-to-zod
packages/ws-schema/ts/generated.ts   (TypeScript 型 + Zod — git 管理)
```

## 再生成

```bash
bash packages/ws-schema/scripts/generate.sh
```

## 整合チェック

```bash
bash packages/ws-schema/scripts/check.sh
# exit 0 = スキーマに差分なし
```
