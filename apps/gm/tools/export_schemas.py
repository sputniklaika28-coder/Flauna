"""Export Pydantic models to JSON Schema files for ws-schema package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # Import Pydantic models
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from tacex_gm.ws.messages import (
        ClientMessage,
        ErrorMessage,
        JoinRoomMessage,
        SessionRestoreMessage,
    )

    schemas = {
        "ClientMessage": ClientMessage,
        "JoinRoomMessage": JoinRoomMessage,
        "SessionRestoreMessage": SessionRestoreMessage,
        "ErrorMessage": ErrorMessage,
    }

    for name, model in schemas.items():
        schema = model.model_json_schema()
        (out_dir / f"{name}.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2))
        print(f"  Exported: {out_dir / name}.json")


if __name__ == "__main__":
    main()
