#!/usr/bin/env bash
# Verifie puis fabrique l'archive tir.skill importable dans claude.ai.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verifier.py
rm -f tir.skill
python3 - <<'PY'
import zipfile, pathlib
z = zipfile.ZipFile("tir.skill", "w", zipfile.ZIP_DEFLATED)
for f in sorted(pathlib.Path("tir").rglob("*")):
    if f.is_file():
        z.write(f, str(f))
z.close()
print("tir.skill :", ", ".join(zipfile.ZipFile("tir.skill").namelist()))
PY
