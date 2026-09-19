#!/usr/bin/env python3
"""Test de fumee : cible.py s'importe vraiment (dependances presentes, rien qui
   pete au chargement) et expose les fonctions derriere les quatre commandes.
   Le verifier se contente d'analyser la syntaxe ; ici le module est execute."""
import importlib.util, pathlib, sys

sys.dont_write_bytecode = True   # pas de __pycache__ a cote de la skill

racine = pathlib.Path(__file__).resolve().parent.parent
cible = racine / "skills" / "tir" / "scripts" / "cible.py"

spec = importlib.util.spec_from_file_location("cible", cible)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)          # __name__ != "__main__" : le CLI ne part pas

manquantes = [n for n in ("analyser", "overlay", "zoom", "tiles")
              if not callable(getattr(module, n, None))]
if manquantes:
    sys.exit("ECHEC : fonctions absentes de cible.py — " + ", ".join(manquantes))
print(f"OK — {cible.name} s'importe et expose analyser, overlay, zoom, tiles")
