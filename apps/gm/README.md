# TacEx-GM

タクティカル祓魔師TRPG Headless AI-GM バックエンド

## 起動

```bash
uv sync
uv run uvicorn tacex_gm.main:app --reload --port 8000
```

## テスト

```bash
uv run pytest
```

## スキーマエクスポート

```bash
uv run python tools/export_schemas.py
```
