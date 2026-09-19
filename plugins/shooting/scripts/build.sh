#!/usr/bin/env bash
# Verify, then build the shooting.skill archive importable on claude.ai.
# The zip must contain <skill>/SKILL.md, so it is packed from skills/.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify.py
rm -f shooting.skill
python3 - <<'PY'
import zipfile, pathlib
root = pathlib.Path("skills")
z = zipfile.ZipFile("shooting.skill", "w", zipfile.ZIP_DEFLATED)
for f in sorted(root.rglob("*")):
    if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
        z.write(f, str(f.relative_to(root)))
z.close()
print("shooting.skill:", ", ".join(zipfile.ZipFile("shooting.skill").namelist()))
PY
