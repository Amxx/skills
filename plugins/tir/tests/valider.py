#!/usr/bin/env python3
"""Rejoue une seance et mesure justes / faux positifs / temps contre tests/verite.json."""
import json, math, pathlib, subprocess, sys, time

racine = pathlib.Path(__file__).resolve().parent.parent
script = racine / "skills" / "tir" / "scripts" / "cible.py"
verite = json.loads((racine / "tests" / "verite.json").read_text(encoding="utf-8"))
sortie = racine / "tests" / "sortie"; sortie.mkdir(exist_ok=True)
etat = sortie / "etat.json"
nc = verite.get("coups_par_serie", 10)
C10 = {"r10_mm": 5.75, "pas_mm": 8, "noir_mm": 29.75, "anneaux": 10, "calibre_mm": 4.5}

def neuf(n):
    return {"cible": "ISSF 10m pistolet a air", **C10, "series": [], "cartons": n,
            "coups_par_serie": nc}

e, carton, n, justes, faux, total = None, None, 0, 0, 0, 0.
for s in verite["series"]:
    if s.get("carton") != carton:
        carton = s.get("carton"); e = neuf(carton or 1)
    src = "-"
    if e["series"]:
        etat.write_text(json.dumps(e), encoding="utf-8"); src = str(etat)
    photo = racine / "tests" / "cartons" / s["photo"]
    if not photo.exists():
        sys.exit(f"photo absente : {photo}")
    t = time.time()
    r = subprocess.run([sys.executable, str(script), "analyse", str(photo), src, str(sortie)],
                       capture_output=True, text=True)
    dt = time.time() - t; total += dt
    if r.returncode:
        sys.exit(f"{s['photo']} : {r.stderr[-500:]}")
    det = json.loads(r.stdout)["nouveaux"]
    pris, bon = set(), 0
    for d in det:
        meilleur = None
        for k, v in enumerate(s["impacts"]):
            if k in pris: continue
            dd = math.hypot(d["x"] - v["x"], d["y"] - v["y"])
            if dd < 2.5 and (meilleur is None or dd < meilleur[1]): meilleur = (k, dd)
        if meilleur: pris.add(meilleur[0]); bon += 1
    justes += bon; faux += len(det) - bon; n += 1
    manques = [(v["x"], v["y"]) for k, v in enumerate(s["impacts"]) if k not in pris]
    print(f"{s['photo']:>16} {dt:5.1f}s  detectes {len(det):2d}  justes {bon}/{len(s['impacts'])}"
          f"  faux {len(det)-bon}  manques {manques}")
    e["series"].append({"n": len(e["series"]) + 1, "photo": s["photo"],
                        "impacts": [dict(i, id=f"v{n}-{k}") for k, i in enumerate(s["impacts"])]})

att = sum(len(s["impacts"]) for s in verite["series"])
print(f"\nTOTAL  justes {justes}/{att}  faux positifs {faux}  temps {total:.1f}s "
      f"({total/max(n,1):.1f}s par carton)")
