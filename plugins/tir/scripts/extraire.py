#!/usr/bin/env python3
"""Extrait le script Python du bloc de code de tir/SKILL.md vers build/cible.py.
   SKILL.md est la source unique : rien n'est duplique dans le depot."""
import pathlib, sys

racine = pathlib.Path(__file__).resolve().parent.parent
md = (racine / "tir" / "SKILL.md").read_text(encoding="utf-8")
blocs = md.split("```python")
if len(blocs) != 2:
    sys.exit(f"attendu 1 bloc python dans SKILL.md, trouve {len(blocs)-1}")
code = blocs[1].split("```")[0]
out = racine / "build" / "cible.py"
out.parent.mkdir(exist_ok=True)
out.write_text(code, encoding="utf-8")
out.chmod(0o755)
print(out, len(code.splitlines()), "lignes")
