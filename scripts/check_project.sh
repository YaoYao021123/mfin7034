#!/bin/bash
set -euo pipefail

echo "[1/4] Python syntax check"
python3 -m py_compile extract_pdf.py generate_html.py serve.py scripts/sync_lectures_json.py

echo "[2/4] Shell syntax check"
bash -n run.sh

echo "[3/4] Sync static lecture index"
python3 scripts/sync_lectures_json.py

echo "[4/4] Placeholder and key exposure scan"
python3 - <<'PY'
from pathlib import Path
import re

root = Path(".")
html_dir = root / "html"
placeholder_re = re.compile(
    r"This concept is like a familiar everyday process|"
    r"Understanding this helps in practical applications|"
    r"Consider a typical scenario where this applies|"
    r"Students often confuse this with related concepts"
)
key_re = re.compile(r"AIza[0-9A-Za-z_-]{20,}")

issues = []
for p in html_dir.glob("*.html"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    if placeholder_re.search(text):
        issues.append(f"Placeholder text found: {p}")
    if key_re.search(text):
        issues.append(f"Potential key found in HTML: {p}")

if issues:
    print("\n".join(issues))
    raise SystemExit(1)
print("All checks passed.")
PY

echo "Done."

