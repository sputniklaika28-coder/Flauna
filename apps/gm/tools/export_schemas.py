"""Export Pydantic message schemas to JSON Schema files for ws-schema package."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running as `uv run python tools/export_schemas.py` from apps/gm/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tacex_gm.errors import ErrorCode  # noqa: E402
from tacex_gm.ws.messages import ClientMessage, ServerMessage  # noqa: E402

out_dir = Path(
    os.environ.get(
        "WS_SCHEMA_OUT_DIR",
        str(Path(__file__).parent.parent.parent.parent / "packages" / "ws-schema" / "schemas"),
    )
)
out_dir.mkdir(parents=True, exist_ok=True)

# Pydantic v2 model_json_schema works on Annotated union via TypeAdapter
from pydantic import TypeAdapter  # noqa: E402

client_schema = TypeAdapter(ClientMessage).json_schema()  # type: ignore[type-arg]
server_schema = TypeAdapter(ServerMessage).json_schema()  # type: ignore[type-arg]

(out_dir / "client_message.json").write_text(
    json.dumps(client_schema, indent=2, ensure_ascii=False) + "\n"
)
(out_dir / "server_message.json").write_text(
    json.dumps(server_schema, indent=2, ensure_ascii=False) + "\n"
)

# Export ErrorCode values for ts/error_codes.ts generation
error_codes = [e.value for e in ErrorCode]
(out_dir / "error_codes.json").write_text(
    json.dumps({"error_codes": error_codes}, indent=2, ensure_ascii=False) + "\n"
)

print(f"Schemas written to {out_dir}")
