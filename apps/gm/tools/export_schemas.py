#!/usr/bin/env python3
"""Export Pydantic WS message models to JSON Schema files."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Pydantic models to JSON Schema")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from tacex_gm.ws.messages import ClientMessage, JoinRoomMessage  # noqa: PLC0415

    schemas: dict[str, type] = {
        "JoinRoomMessage": JoinRoomMessage,
        "ClientMessage": ClientMessage,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    for name, model in schemas.items():
        out_file = args.out / f"{name}.json"
        out_file.write_text(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n")
        print(f"  Exported: {out_file}")


if __name__ == "__main__":
    main()
