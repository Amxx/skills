#!/usr/bin/env bash
# Verifie puis fabrique l'archive tir.skill importable dans claude.ai.
# Le zip doit contenir tir/SKILL.md : on empaquette donc depuis skills/.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verifier.py
rm -f tir.skill
python3 - <<'PY'
import zipfile, pathlib
racine = pathlib.Path("skills")
z = zipfile.ZipFile("tir.skill", "w", zipfile.ZIP_DEFLATED)
for f in sorted(racine.rglob("*")):
    if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
        z.write(f, str(f.relative_to(racine)))
z.close()
print("tir.skill :", ", ".join(zipfile.ZipFile("tir.skill").namelist()))
PY
