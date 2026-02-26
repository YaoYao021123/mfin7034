#!/usr/bin/env python3
"""Sync html/lectures.json from current html/pdfs folders."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import serve


def main() -> None:
    output = BASE_DIR / "html" / "lectures.json"
    lectures = serve.build_lecture_list(BASE_DIR)
    output.write_text(
        json.dumps({"lectures": lectures, "count": len(lectures)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Synced {output} ({len(lectures)} lectures)")


if __name__ == "__main__":
    main()
