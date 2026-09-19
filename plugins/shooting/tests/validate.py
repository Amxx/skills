#!/usr/bin/env python3
"""Replay a session and measure hits / false positives / time against tests/verite.json.
   The JSON keys stay French: they are the hand-written truth files' format."""
import json, math, pathlib, subprocess, sys, time

root = pathlib.Path(__file__).resolve().parent.parent
engine = root / "skills" / "target-analysis" / "scripts" / "cible.py"
truth = json.loads((root / "tests" / "verite.json").read_text(encoding="utf-8"))
out = root / "tests" / "sortie"; out.mkdir(exist_ok=True)
state_path = out / "etat.json"
per_series = truth.get("coups_par_serie", 10)
C10 = {"r10_mm": 5.75, "pas_mm": 8, "noir_mm": 29.75, "anneaux": 10, "calibre_mm": 4.5}

def fresh(n):
    return {"cible": "ISSF 10m pistolet a air", **C10, "series": [], "cartons": n,
            "coups_par_serie": per_series}

state, card, n, hits, false_pos, elapsed = None, None, 0, 0, 0, 0.
for s in truth["series"]:
    if s.get("carton") != card:
        card = s.get("carton"); state = fresh(card or 1)
    src = "-"
    if state["series"]:
        state_path.write_text(json.dumps(state), encoding="utf-8"); src = str(state_path)
    photo = root / "tests" / "cartons" / s["photo"]
    if not photo.exists():
        sys.exit(f"missing photo: {photo}")
    t = time.time()
    r = subprocess.run([sys.executable, str(engine), "analyse", str(photo), src, str(out)],
                       capture_output=True, text=True)
    dt = time.time() - t; elapsed += dt
    if r.returncode:
        sys.exit(f"{s['photo']}: {r.stderr[-500:]}")
    found = json.loads(r.stdout)["nouveaux"]
    taken, good = set(), 0
    for d in found:
        best = None
        for k, v in enumerate(s["impacts"]):
            if k in taken: continue
            dd = math.hypot(d["x"] - v["x"], d["y"] - v["y"])
            if dd < 2.5 and (best is None or dd < best[1]): best = (k, dd)
        if best: taken.add(best[0]); good += 1
    hits += good; false_pos += len(found) - good; n += 1
    missed = [(v["x"], v["y"]) for k, v in enumerate(s["impacts"]) if k not in taken]
    print(f"{s['photo']:>16} {dt:5.1f}s  found {len(found):2d}  hits {good}/{len(s['impacts'])}"
          f"  false {len(found)-good}  missed {missed}")
    state["series"].append({"n": len(state["series"]) + 1, "photo": s["photo"],
                            "impacts": [dict(i, id=f"v{n}-{k}") for k, i in enumerate(s["impacts"])]})

total = sum(len(s["impacts"]) for s in truth["series"])
print(f"\nTOTAL  hits {hits}/{total}  false positives {false_pos}  time {elapsed:.1f}s "
      f"({elapsed/max(n,1):.1f}s per card)")
