"""Generate the published CivicClerk OpenAPI artifact."""

from __future__ import annotations

import json
from pathlib import Path

from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "api" / "openapi.json"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
