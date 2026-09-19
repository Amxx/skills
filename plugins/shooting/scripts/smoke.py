#!/usr/bin/env python3
"""Smoke test: cible.py really imports (dependencies present, nothing blowing up
   at load time) and exposes the functions behind the four commands.
   verify.py only parses the syntax; here the module actually runs."""
import importlib.util, pathlib, sys

sys.dont_write_bytecode = True   # no __pycache__ next to the skill

root = pathlib.Path(__file__).resolve().parent.parent
engine = root / "skills" / "target-analysis" / "scripts" / "cible.py"

spec = importlib.util.spec_from_file_location("cible", engine)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)          # __name__ != "__main__": the CLI stays put

missing = [n for n in ("analyser", "overlay", "zoom", "tiles")
           if not callable(getattr(module, n, None))]
if missing:
    sys.exit("FAIL: functions missing from cible.py — " + ", ".join(missing))
print(f"OK — {engine.name} imports and exposes analyser, overlay, zoom, tiles")
