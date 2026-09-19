#!/usr/bin/env python3
"""Controles avant publication : manifestes du plugin, frontmatter de la fiche,
   syntaxe du script livre et presence des commandes attendues."""
import ast, json, pathlib, sys

racine = pathlib.Path(__file__).resolve().parent.parent
skill = racine / "skills" / "tir"
md = (skill / "SKILL.md").read_text(encoding="utf-8")
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

# le script est livre a cote de la fiche : c'est lui la source, rien n'est transcrit
cible = skill / "scripts" / "cible.py"
if not cible.exists():
    erreurs.append(f"{cible} absent : la fiche renvoie a un script qui n'existe pas")
else:
    code = cible.read_text(encoding="utf-8")
    try:
        ast.parse(code)
    except SyntaxError as e:
        erreurs.append(f"syntaxe de cible.py : ligne {e.lineno} — {e.msg}")
    for cmd in ("analyse", "overlay", "zoom", "tiles"):
        if f'"{cmd}"' not in code:
            erreurs.append(f"commande {cmd} absente de cible.py")
if "```python" in md:
    erreurs.append("bloc python dans SKILL.md : le script doit rester dans scripts/cible.py")

# manifestes : le nom doit etre le meme partout, sinon l'install casse
manif = racine / ".claude-plugin" / "plugin.json"
try:
    plugin = json.loads(manif.read_text(encoding="utf-8"))
except FileNotFoundError:
    plugin = None
    erreurs.append(f"{manif} absent : le plugin ne sera pas installable")
except json.JSONDecodeError as e:
    plugin = None
    erreurs.append(f"plugin.json illisible : {e}")
if plugin is not None:
    if plugin.get("name") != racine.name:
        erreurs.append(f"plugin.json name={plugin.get('name')!r} != dossier {racine.name!r}")
    if not (skill / "SKILL.md").exists():
        erreurs.append("la skill doit vivre dans skills/tir/ pour etre decouverte")

marche = racine.parent.parent / ".claude-plugin" / "marketplace.json"
if marche.exists():
    entrees = json.loads(marche.read_text(encoding="utf-8")).get("plugins", [])
    src = f"./{racine.relative_to(racine.parent.parent).as_posix()}"
    if not any(e.get("source") == src for e in entrees):
        erreurs.append(f"aucune entree de marketplace.json ne pointe sur {src}")
else:
    erreurs.append(f"{marche} absent : le marketplace ne listera rien")

if erreurs:
    print("\n".join("ECHEC : " + e for e in erreurs))
    sys.exit(1)
print("OK — manifestes, frontmatter, script livre et commandes")
