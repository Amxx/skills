#!/usr/bin/env python3
"""Controles avant publication : frontmatter, bloc unique, syntaxe du script,
   presence des commandes attendues."""
import ast, pathlib, sys

racine = pathlib.Path(__file__).resolve().parent.parent
md = (racine / "tir" / "SKILL.md").read_text(encoding="utf-8")
erreurs = []

if not md.startswith("---\n"):
    erreurs.append("frontmatter YAML absent en tete de SKILL.md")
else:
    tete = md.split("---", 2)[1]
    for champ in ("name:", "description:"):
        if champ not in tete:
            erreurs.append(f"champ {champ} absent du frontmatter")
    if "name: tir" not in tete:
        erreurs.append("le nom doit rester 'tir' : sinon l'import cree une skill de plus")

if md.count("```python") != 1:
    erreurs.append(f"{md.count('```python')} blocs python, attendu 1")
else:
    code = md.split("```python")[1].split("```")[0]
    try:
        ast.parse(code)
    except SyntaxError as e:
        erreurs.append(f"syntaxe du script : ligne {e.lineno} — {e.msg}")
    for cmd in ("analyse", "overlay", "zoom", "tiles"):
        if f'"{cmd}"' not in code:
            erreurs.append(f"commande {cmd} absente du script")

if erreurs:
    print("\n".join("ECHEC : " + e for e in erreurs))
    sys.exit(1)
print("OK — frontmatter, bloc unique, syntaxe et commandes")
