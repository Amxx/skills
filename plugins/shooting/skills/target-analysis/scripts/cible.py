#!/usr/bin/env python3
"""Analyse de carton de tir : geometrie, detection, decomposition, score, calque.
   Tout en une commande pour eviter les allers-retours."""
import json, math, sys
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from scipy import ndimage as nd
from scipy.signal import fftconvolve
from scipy.optimize import minimize, least_squares

C10 = {"r10_mm": 5.75, "pas_mm": 8, "noir_mm": 29.75, "anneaux": 10, "calibre_mm": 4.5}

def charger(src):
    return np.asarray(ImageOps.exif_transpose(Image.open(src)).convert("RGB")).astype(float).mean(2)

def _fond(g, taille, d=3):
    """Fond local par mediane.  Calculee sur l'image sous-echantillonnee d'un
       facteur d puis re-interpolee : le fond varie lentement a l'echelle du
       calibre, le resultat est indiscernable et le cout chute d'environ x25
       (90 s -> 4 s sur 1450x2576).  C'etait LE goulot du pipeline."""
    gs = g[::d, ::d]
    ms = nd.median_filter(gs, size=max(3, int(taille/d) | 1))
    return nd.zoom(ms, (g.shape[0]/ms.shape[0], g.shape[1]/ms.shape[1]), order=1)

def disque_noir(g):
    # ouverture AVANT etiquetage : sans elle, un trou traversant colle au bord
    # du visuel fait un pont et la bbox part de plusieurs millimetres
    m = nd.binary_fill_holes(nd.binary_opening(g < 90, np.ones((5,5))))
    lab, n = nd.label(m); sz = nd.sum(m, lab, range(1, n+1)); H, W = g.shape
    for i in np.argsort(sz)[::-1][:6]:
        ys, xs = np.nonzero(lab == i+1)
        w, h = xs.max()-xs.min()+1, ys.max()-ys.min()+1
        if w < .1*W or w > .9*W or not .6 < w/h < 1.6 or sz[i] < .45*w*h: continue
        return (xs.min()+xs.max())/2, (ys.min()+ys.max())/2, w/2, h/2
    raise RuntimeError("disque noir introuvable")

def _proj(p, X, Y):
    x0, fx, kx, y0, fy, ky = p; w = 1 + kx*X + ky*Y
    return x0 + fx*X/w, y0 + fy*Y/w

def ajuster(g, cible, n_ech=540):
    """Etage 1 : cale le 'peigne' des anneaux sur la carte de contraste (identifie qui est qui).
       Etage 2 : releve les vrais passages de traits au sous-pixel et refait un moindres
       carres exact, bord du noir inclus.  Un seul appel."""
    r10, pas, noir, nmax = cible["r10_mm"], cible["pas_mm"], cible["noir_mm"], cible["anneaux"]
    cx, cy, ax, ay = disque_noir(g)
    rayons = [r10 + k*pas for k in range(nmax)]
    th = np.linspace(0, 2*np.pi, n_ech, endpoint=False); S, C = np.sin(th), np.cos(th)
    H, W = g.shape
    ech = lambda xx, yy: nd.map_coordinates(g, [np.clip(yy,0,H-1), np.clip(xx,0,W-1)], order=1, mode="nearest")
    fx0, fy0 = ax/noir, -ay/noir
    def score(p):
        # garde-fou : echelle et centre ne peuvent pas s'eloigner du disque noir
        # (sans ca l'optimiseur glisse d'un anneau : la structure est periodique)
        if abs(p[1]/fx0 - 1) > .08 or abs(p[4]/fy0 - 1) > .08: return 1e9
        if abs(p[0]-cx) > 15 or abs(p[3]-cy) > 15: return 1e9
        tot = 0.
        for R in rayons:
            X, Y = R*S, R*C
            w = 1 + p[2]*X + p[5]*Y
            if np.any(w < .4): return 1e9
            xx, yy = p[0] + p[1]*X/w, p[3] + p[4]*Y/w
            nx, ny = p[1]*S, p[4]*C; nn = np.hypot(nx, ny)
            nx, ny = nx/nn*2.2, ny/nn*2.2
            c = (ech(xx-nx, yy-ny) + ech(xx+nx, yy+ny))/2 - ech(xx, yy)
            c = c if R > noir else -c
            ok = (xx > 4) & (xx < W-5) & (yy > 4) & (yy < H-5)
            if ok.sum() < 60: continue
            c = np.clip(c[ok], 0, 60); m = max(10, int(.6*len(c)))
            tot += np.mean(np.sort(c)[-m:])
        return -tot
    p0 = np.array([cx, ax/noir, 0., cy, -ay/noir, 0.])
    best = None
    for s1 in (0.96, 0.98, 1.0, 1.02, 1.04):
        q = p0.copy(); q[1] *= s1; q[4] *= s1
        r = minimize(lambda v: score([v[0], v[1], 0., v[2], v[3], 0.]),
                     [q[0], q[1], q[3], q[4]], method="Nelder-Mead",
                     options={"xatol":.02, "fatol":.02, "maxfev":1500})
        if best is None or r.fun < best.fun: best = r
    p = minimize(score, [best.x[0], best.x[1], 0., best.x[2], best.x[3], 0.],
                 method="Nelder-Mead",
                 options={"xatol":1e-3, "fatol":1e-3, "maxiter":6000, "maxfev":8000}).x

    obs = []
    for R in rayons:
        for sx, sy in ((1,0), (-1,0), (0,1), (0,-1)):
            X, Y = R*sx, R*sy
            a, b = _proj(p, X, Y)
            if not (6 < a < W-7 and 6 < b < H-7): continue
            dx, dy = _proj(p, X*1.01, Y*1.01)
            ux, uy = dx-a, dy-b; un = np.hypot(ux, uy)
            if un < 1e-6: continue
            ux, uy = ux/un, uy/un
            t = np.linspace(-5, 5, 41)
            prof = ech(a + ux*t, b + uy*t)
            prof = prof if R <= noir else -prof
            k = int(np.argmax(prof))
            if k in (0, len(t)-1): continue
            y1, y2, y3 = prof[k-1], prof[k], prof[k+1]
            den = y1 - 2*y2 + y3
            d = 0.5*(y1-y3)/den if abs(den) > 1e-6 else 0.
            if abs(d) > 1: continue
            ts = t[k] + d*(t[1]-t[0])
            if abs(ts) > 4: continue
            obs.append((X, Y, a + ux*ts, b + uy*ts))
    mnoir = nd.binary_fill_holes(nd.binary_closing(g < 90, np.ones((7,7))))
    lb, _ = nd.label(mnoir)
    mnoir = nd.binary_fill_holes(lb == lb[int(cy), int(cx)])
    ey, ex = np.nonzero(mnoir ^ nd.binary_erosion(mnoir))
    if len(ex) > 900:
        idx = np.linspace(0, len(ex)-1, 900).astype(int); ex, ey = ex[idx], ey[idx]
    def inv0(q, x, y):
        x0, fx, kx, y0, fy, ky = q
        w = 1/(1 - kx*(x-x0)/fx - ky*(y-y0)/fy)
        return (x-x0)*w/fx, (y-y0)*w/fy
    if len(obs) >= 12:
        A = np.array(obs)
        def res(q):
            xx, yy = _proj(q, A[:,0], A[:,1])
            X, Y = inv0(q, ex, ey)
            return np.concatenate([xx-A[:,2], yy-A[:,3],
                                   (np.hypot(X, Y) - noir) * q[1] * .5,
                                   [300*q[2], 300*q[5]]])
        sol = least_squares(res, p, loss="huber", f_scale=4.0, x_scale=[1,.01,1e-4,1,.01,1e-4])
        if abs(sol.x[1]/fx0 - 1) < .08 and abs(sol.x[4]/fy0 - 1) < .08: p = sol.x
        for _ in range(2):   # rejet des passages pollues par un impact, puis refit
            xx, yy = _proj(p, A[:,0], A[:,1])
            d = np.hypot(xx-A[:,2], yy-A[:,3])
            garde = d < max(2.5, np.median(d)*2)
            if garde.sum() < 12 or garde.all(): break
            A = A[garde]
            sol = least_squares(res, p, loss="huber", f_scale=3.0, x_scale=[1,.01,1e-4,1,.01,1e-4])
            if abs(sol.x[1]/fx0 - 1) < .08 and abs(sol.x[4]/fy0 - 1) < .08: p = sol.x
        xx, yy = _proj(p, A[:,0], A[:,1])
        rms = float(np.sqrt(np.mean((xx-A[:,2])**2 + (yy-A[:,3])**2)))
    else:
        rms = float("nan")
    tt = np.linspace(0, 2*np.pi, 360, endpoint=False)
    bx, by = _proj(p, noir*np.sin(tt), noir*np.cos(tt))
    ctrl = max(abs(bx.min()-(cx-ax)), abs(bx.max()-(cx+ax)),
               abs(by.min()-(cy-ay)), abs(by.max()-(cy+ay)))
    return p, len(obs), rms, float(ctrl)

def _tpl(rx, ry):
    R = int(np.ceil(max(rx, ry))) + 1
    Y, X = np.mgrid[-R:R+1, -R:R+1]
    return (((X/rx)**2 + (Y/ry)**2) <= 1).astype(float)

def decomposer(masque, rx, ry, k, ancres=(), essais=16, graine=0):
    """k disques de calibre sur le masque d'un amas.  Placement glouton par
    convolution du residu + raffinement local, avec redemarrages pour les disques
    libres.  `ancres` = anciens impacts, poses d'office, libres a +-3 px."""
    sh = masque.shape
    Y, X = np.mgrid[0:sh[0], 0:sh[1]].astype(float)
    aire_m = masque.sum()
    def union(sel):
        u = np.zeros(sh, bool)
        for cx, cy in sel: u |= (((X-cx)/rx)**2 + ((Y-cy)/ry)**2) <= 1
        return u
    def iou(sel):
        u = union(sel); i = np.count_nonzero(u & masque)
        return i / (np.count_nonzero(u) + aire_m - i)
    nanc = min(len(ancres), k)
    anc = [tuple(map(float, a)) for a in ancres][:k]
    def raffiner(sel):
        sel = list(sel); cur = iou(sel)
        for pas in (3., 1.5, .75, .375):
            bouge, tours = True, 0
            while bouge and tours < 15:
                bouge = False; tours += 1
                for i in range(len(sel)):
                    for dx, dy in ((pas,0),(-pas,0),(0,pas),(0,-pas),
                                   (pas,pas),(-pas,-pas),(pas,-pas),(-pas,pas)):
                        c = (sel[i][0]+dx, sel[i][1]+dy)
                        if i < nanc and (c[0]-anc[i][0])**2 + (c[1]-anc[i][1])**2 > 9: continue
                        if not (0 <= c[1] < sh[0] and 0 <= c[0] < sh[1]): continue
                        s2 = list(sel); s2[i] = c; v = iou(s2)
                        if v > cur + 1e-6: cur, sel, bouge = v, s2, True
        return sel, cur
    D = _tpl(rx, ry); sel = list(anc)
    for _ in range(k - nanc):
        res = np.clip(masque.astype(float) - union(sel), 0, 1) if sel else masque.astype(float)
        cov = fftconvolve(res, D, mode="same"); cov[~masque] = -1
        cy, cx = np.unravel_index(np.argmax(cov), sh)
        sel.append((float(cx), float(cy)))
    best = raffiner(sel)
    if k > nanc:
        rng = np.random.default_rng(graine); ys, xs = np.nonzero(masque)
        for _ in range(essais):
            lib = [(float(xs[i]), float(ys[i])) for i in rng.integers(0, len(xs), k - nanc)]
            r = raffiner(anc + lib)
            if r[1] > best[1]: best = r
    return best

def inv(p, x, y):
    x0, fx, kx, y0, fy, ky = p
    w = 1/(1 - kx*(x-x0)/fx - ky*(y-y0)/fy)
    return (x-x0)*w/fx, (y-y0)*w/fy

def note(X, Y, c):
    r = math.hypot(X, Y); re = max(0., r - c["calibre_mm"]/2)
    if re <= c["r10_mm"]: return r, 10, c["r10_mm"] - re
    s = max(0, 10 - math.ceil((re - c["r10_mm"])/c["pas_mm"]))
    n = math.ceil((re - c["r10_mm"])/c["pas_mm"])
    m = min(abs(re - (c["r10_mm"] + (n-1)*c["pas_mm"])), abs(c["r10_mm"] + n*c["pas_mm"] - re))
    return r, s, m

def _vrai_trou(g, x, y, cal):
    """Un vrai trou de plomb sur le beige a deux signatures que la pince et son
       ombre n'ont pas : une couronne de papier dechire plus claire que le fond,
       et un bord net.  Rejet seulement si les DEUX manquent (mesure sur les 4
       faux positifs et les 15 trous beige de la seance : pinces <=6,7 et <=4,7,
       trous >=8,2 ou >=6,2 — aucun chevauchement sur la regle combinee)."""
    R = int(cal*3)+2; y0, x0 = int(y), int(x)
    sub = g[max(0,y0-R):y0+R+1, max(0,x0-R):x0+R+1]
    if sub.size < 100: return True
    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
    cy, cx = y0-max(0,y0-R), x0-max(0,x0-R)
    d = np.hypot(yy-cy, xx-cx)
    ext = (d > 2.0*cal) & (d < 3.0*cal); ring = (d > .45*cal) & (d < .95*cal)
    if ext.sum() < 30 or ring.sum() < 30: return True
    bg = np.median(sub[ext])
    couronne = float(np.percentile(sub[ring], 97) - bg)
    gy, gx = np.gradient(nd.gaussian_filter(sub, 1.0))
    bord = (d > .35*cal) & (d < .65*cal)
    nettete = float(np.percentile(np.hypot(gx, gy)[bord], 80)) if bord.sum() else 0.
    return couronne >= 7.5 or nettete >= 6.

def detecter(g, p, c):
    cal = c["calibre_mm"] * p[1]
    se = np.ones((max(3, int(cal*.28)),)*2)
    noir = nd.binary_fill_holes(nd.binary_closing(g < 90, np.ones((7,7))))
    lb, _ = nd.label(noir)
    noir = nd.binary_fill_holes(lb == lb[int(p[3]), int(p[0])])
    ec = g - _fond(g, int(cal*4) | 1)
    H0, W0 = g.shape; _Y, _X = np.mgrid[0:H0, 0:W0]
    _Xm, _Ym = inv(p, _X, _Y); _R = np.hypot(_Xm, _Ym)
    _v = ec[(~noir) & (_R < 85)]
    mad = float(np.median(np.abs(_v - np.median(_v)))) if _v.size else 2.5
    sb, sn = max(8., 3.4*mad), max(12., 4.5*mad)   # seuils adaptes au bruit du tirage
    brut = np.zeros_like(noir)
    # trois polarites ; fermer AVANT d'ouvrir (ombre interne qui coupe un trou)
    # quatre polarites.  La quatrieme est indispensable : un plomb qui arrache le
    # papier sans laisser de plomb laisse un trou PLUS CLAIR que le beige
    # (4 trous sur 50 dans la seance du 19/09, tous manques sans elle).
    for m in (noir & (ec > sn), (~noir) & (ec < -sb) & (ec > -75),
              (~noir) & (ec <= -75), (~noir) & (ec > sn)):
        brut |= nd.binary_closing(nd.binary_opening(nd.binary_closing(m, se), se), se)
    H, W = g.shape; Yg, Xg = np.mgrid[0:H, 0:W]
    Xm, Ym = inv(p, Xg, Yg); R = np.hypot(Xm, Ym)
    rmax = c["r10_mm"] + (c["anneaux"]-1)*c["pas_mm"]
    brut &= R < rmax + 2
    lab, n = nd.label(brut)
    blobs = []
    for i in range(1, n+1):
        m = lab == i; a = int(m.sum())
        if a < .25*cal**2: continue
        ys, xs = np.nonzero(m)
        w, h = int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)
        if w > 6*cal or h > 6*cal: continue
        if max(w, h)/max(1, min(w, h)) > 2.8: continue          # allonge = pince/trait
        if a < .45*w*h*0.5: continue                            # peu dense = ombre
        if noir[int(ys.mean()), int(xs.mean())] == 0:
            rr = int(cal*1.6); yy0, xx0 = int(ys.mean()), int(xs.mean())
            vois = g[max(0,yy0-rr):yy0+rr, max(0,xx0-rr):xx0+rr]
            if vois.size and np.median(vois) < 140: continue    # entoure de sombre = pince
            if not _vrai_trou(g, xs.mean(), ys.mean(), cal): continue
            # trou CLAIR sur beige : la pince en metal brillant passe les tests
            # precedents.  Elle est en revanche allongee ou effilee, jamais ronde.
            if a < 1.8*cal**2 and np.median(g[m]) > np.median(vois) + 5:
                if a / (np.pi*(max(w, h)/2)**2) < .55: continue
        blobs.append({"i": i, "aire": a, "wh": [w, h],
                      "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                      "px": [float(xs.mean()), float(ys.mean())],
                      "fond": "noir" if noir[int(ys.mean()), int(xs.mean())] else "beige"})
    ref = {}
    for f in ("noir", "beige"):
        iso = [b["aire"] for b in blobs if b["fond"] == f and max(b["wh"]) <= 1.35*cal]
        ref[f] = float(np.median(iso)) if len(iso) >= 3 else .72*cal**2
    for b in blobs: b["k_aire"] = b["aire"]/ref[b["fond"]]
    blobs = [b for b in blobs if b["k_aire"] <= 10]
    return blobs, lab, ref, cal, noir

def analyser(photo, etat_path, sortie=".", n_coups=None):
    c = dict(C10)
    e = json.load(open(etat_path)) if etat_path != "-" else {
        "cible": "ISSF 10m pistolet a air", **C10, "series": [], "cartons": 1}
    for k in ("r10_mm", "pas_mm", "noir_mm", "anneaux", "calibre_mm"): c[k] = e.get(k, c[k])
    g = charger(photo)
    p, nobs, rms, ctrl = ajuster(g, c)
    blobs, lab, ref, cal, noir = detecter(g, p, c)
    anciens = [(s["n"], i) for s in e.get("series", []) for i in s["impacts"]]
    ry = cal*(-p[4])/p[1]/2
    def decoupe(b, anc=(), kforce=None):
        x0, y0, x1, y1 = b["bbox"]; pad = 7
        ox, oy = max(0, x0-pad), max(0, y0-pad)
        sub = nd.binary_fill_holes(nd.binary_closing(
            lab[oy:y1+pad, ox:x1+pad] == b["i"], np.ones((9,9))))
        k = kforce or max(len(anc), int(round(b["k_aire"])) if b["k_aire"] >= .6 else 1)
        k = max(k, len(anc))
        if k == 1:
            ys, xs = np.nonzero(sub)
            return [(float(xs.mean()+ox), float(ys.mean()+oy))], 1.0, k
        sel, io = decomposer(sub, cal/2, ry, k, [(a-ox, bb-oy) for a, bb in anc],
                             essais=8 if k - len(anc) >= 2 else 0)
        out = []
        for a, bb in sel:   # deux disques quasi confondus = un k de trop
            if any((a-u)**2 + (bb-v)**2 < (.45*cal)**2 for u, v in out): continue
            out.append((a, bb))
        return [(a+ox, bb+oy) for a, bb in out], io, len(out)
    for b in blobs:
        b["disques"], b["iou"], b["k"] = decoupe(b)
    # recalage : les anciens impacts sont autant de points de controle
    nuage = np.array([d for b in blobs for d in b["disques"]])
    def apparier(q):
        pr = np.array([_proj(q, i["x"], i["y"]) for _, i in anciens])
        if not len(nuage) or not len(pr): return [], pr
        d = np.hypot(pr[:, None, 0]-nuage[None, :, 0], pr[:, None, 1]-nuage[None, :, 1])
        j = d.argmin(1); ok = d[np.arange(len(pr)), j] < 2.2*cal
        return [(i, int(j[i])) for i in range(len(pr)) if ok[i]], pr
    for _ in range(3):
        par, pr = apparier(p)
        if len(par) < 8: break
        idx = np.array([a for a, _ in par]); jdx = np.array([b_ for _, b_ in par])
        A = np.array([[anciens[i][1]["x"], anciens[i][1]["y"]] for i in idx])
        T = nuage[jdx]
        def rec(q):
            xx, yy = _proj(q, A[:, 0], A[:, 1])
            return np.concatenate([xx-T[:, 0], yy-T[:, 1]])
        p = least_squares(rec, p, loss="soft_l1", f_scale=.5*cal,
                          x_scale=[1, .01, 1e-4, 1, .01, 1e-4]).x
    par, pr = apparier(p)
    for b in blobs: b["anciens"] = []
    off = 0; bornes = []
    for b in blobs:
        bornes.append((off, off+len(b["disques"]), b)); off += len(b["disques"])
    for i, j in par:
        for a, z, b in bornes:
            if a <= j < z:
                b["anciens"].append((float(nuage[j][0]), float(nuage[j][1]),
                                     anciens[i][0], anciens[i][1]["id"])); break
    nouveaux = []
    for b in blobs:
        anc = [(a, bb) for a, bb, _, _ in b["anciens"]]
        if len(anc) and b["k"] > 1:
            b["disques"], b["iou"], b["k"] = decoupe(b, anc)
        na = len(anc)
        for a, bb in b["disques"][na:]:
            X, Y = inv(p, a, bb); r, s, m = note(X, Y, c)
            nouveaux.append({"px": [round(a, 1), round(bb, 1)], "x": round(X, 1), "y": round(Y, 1),
                             "score": s, "r": round(r, 1), "marge": round(m, 1),
                             "h": round((math.degrees(math.atan2(X, Y)) % 360)/30, 1),
                             "blob": b["i"]})
    # --- comptage contraint : on CONNAIT le nombre de plombs de la serie.
    # Total de disques attendu = anciens reellement retrouves + coups tires.
    # Sans cette contrainte la decomposition sous-compte systematiquement les
    # amas (6/10 puis 5/10 sur les cartons charges de la seance du 19/09).
    trouves = sum(len(b["anciens"]) for b in blobs)
    nc = n_coups if n_coups else int(e.get("coups_par_serie", 10))
    journal = []
    if nc and blobs:
        cible_k = trouves + nc
        bloques = set()
        for _ in range(14):
            obtenu = sum(len(b["disques"]) for b in blobs)
            if obtenu == cible_k: break
            if obtenu < cible_k:
                cand = [b for b in blobs if b["k"] < 6 and b["k_aire"] - b["k"] > .3 and b["i"] not in bloques]
                if not cand: break
                b = max(cand, key=lambda b: b["k_aire"] - b["k"]); nk = b["k"] + 1
            else:
                cand = [b for b in blobs if b["k"] > max(1, len(b["anciens"])) and b["k"] - b["k_aire"] > .3 and b["i"] not in bloques]
                if not cand: break
                b = min(cand, key=lambda b: b["k_aire"] - b["k"]); nk = b["k"] - 1
            anc = [(a, bb) for a, bb, _, _ in b["anciens"]]
            av = len(b["disques"])
            b["disques"], b["iou"], b["k"] = decoupe(b, anc, kforce=nk)
            journal.append({"blob": b["i"], "de": av, "a": len(b["disques"]),
                            "k_aire": round(b["k_aire"], 2), "iou": round(b["iou"], 3)})
            if len(b["disques"]) == av:            # dedup bloque : ecarter ce blob
                bloques.add(b["i"])
        nouveaux = []
        for b in blobs:
            na = len(b["anciens"])
            for a, bb in b["disques"][na:]:
                X, Y = inv(p, a, bb); r, s_, m = note(X, Y, c)
                nouveaux.append({"px": [round(a, 1), round(bb, 1)], "x": round(X, 1), "y": round(Y, 1),
                                 "score": s_, "r": round(r, 1), "marge": round(m, 1),
                                 "h": round((math.degrees(math.atan2(X, Y)) % 360)/30, 1),
                                 "blob": b["i"]})
    res = {"geom": {"p": [round(v, 5) for v in p], "traits": nobs, "rms_px": round(rms, 2),
                    "bord_px": round(ctrl, 1), "px_par_mm": [round(p[1], 3), round(-p[4], 3)]},
           "aire_trou_ref": {k: round(v) for k, v in ref.items()},
           "blobs": len(blobs), "somme_k_aire": round(sum(b["k_aire"] for b in blobs), 1),
           "anciens_attendus": len(anciens), "anciens_retrouves": trouves,
           "comptage": {"coups_attendus": nc, "obtenus": len(nouveaux),
                        "ajustements": journal, "ok": len(nouveaux) == nc},
           "nouveaux": sorted(nouveaux, key=lambda o: -o["score"]),
           "n_nouveaux": len(nouveaux)}
    planche(photo, p, blobs, cal, f"{sortie}/planche.png", c)
    return res, p, blobs, e

def planche(photo, p, blobs, cal, out, c, f=9):
    """Une seule image : toutes les zones a verifier, disques ajustes dessines.
       Remplace six a huit lectures d'image separees."""
    im = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    vus = [b for b in blobs if b["k"] > len(b["anciens"]) or b["k"] >= 2 or b["k_aire"] > 1.4]
    vus.sort(key=lambda b: (b["px"][1], b["px"][0]))
    if not vus: vus = blobs[:1]
    cw = int(cal*4.2); tuiles = []
    for b in vus:
        cx, cy = b["px"]; s = max(cw, int(max(b["wh"])*.75) + cal)
        box = (int(cx-s), int(cy-s), int(cx+s), int(cy+s))
        t = im.crop(box).resize(((box[2]-box[0])*f, (box[3]-box[1])*f), Image.LANCZOS)
        d = ImageDraw.Draw(t); na = len(b["anciens"])
        for j, (a, bb) in enumerate(b["disques"]):
            X, Y = (a-box[0])*f, (bb-box[1])*f; r = cal/2*f
            col = (255, 60, 40) if j >= na else (110, 160, 200)
            d.ellipse([X-r, Y-r, X+r, Y+r], outline=col, width=3)
            d.line([X-6, Y, X+6, Y], fill=col, width=2); d.line([X, Y-6, X, Y+6], fill=col, width=2)
        d.rectangle([0, 0, t.width-1, t.height-1], outline=(40,40,40), width=3)
        d.text((8, 6), f"#{b['i']}  k={b['k']} (aire {b['k_aire']:.1f})  anciens {na}  IoU {b['iou']}",
               fill=(255,255,0))
        tuiles.append(t)
    n = len(tuiles); cols = min(4, n); rows = (n+cols-1)//cols
    tw = max(t.width for t in tuiles); th = max(t.height for t in tuiles)
    ech = min(1.0, 1500/(cols*tw)); tw, th = int(tw*ech), int(th*ech)
    sheet = Image.new("RGB", (cols*tw, rows*th), (250, 250, 248))
    for i, t in enumerate(tuiles):
        sheet.paste(t.resize((tw, th), Image.LANCZOS), ((i % cols)*tw, (i//cols)*th))
    sheet.save(out)

def tiles(src, out):
    import os
    os.makedirs(out, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size; s = 2000/max(w, h)
    if s > 1:
        im = im.resize((round(w*s), round(h*s)), Image.LANCZOS); w, h = im.size
    im.save(f"{out}/full.png"); noms = []
    for i, (a, b) in enumerate([(0,0),(1,0),(0,1),(1,1)]):
        m = .08
        x0, y0 = max(0, round((a*.5-m)*w)), max(0, round((b*.5-m)*h))
        x1, y1 = min(w, round(((a+1)*.5+m)*w)), min(h, round(((b+1)*.5+m)*h))
        t = im.crop((x0, y0, x1, y1)); t = t.resize((t.width*2, t.height*2), Image.LANCZOS)
        t.save(f"{out}/q{i+1}.png"); noms.append(f"{out}/q{i+1}.png")
    print(json.dumps({"full": f"{out}/full.png", "quadrants": noms, "taille": [w, h]}))

def zoom(src, x0, y0, x1, y1, f, out):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB").crop((x0, y0, x1, y1))
    im.resize((im.width*f, im.height*f), Image.LANCZOS).save(out)
    print(json.dumps({"out": out, "origine": [x0, y0], "facteur": f}))

PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Calque</title>
<style>
:root { --b:#c9c7bd; --t:#73726c; --fond:#fdfdfb;
        box-sizing:border-box; padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
        --b:#4a4944; --t:#9c9a92; --fond:#1f1e1c; } }
:root[data-theme="dark"] { --b:#4a4944; --t:#9c9a92; --fond:#1f1e1c; }
html,body { height:100%%; margin:0; background:var(--fond); }
body { display:flex; align-items:center; justify-content:center; padding:12px; }
svg { width:100%%; max-width:680px; height:auto; }
.ts { font:12px system-ui,sans-serif; fill:var(--t); }
</style>
%s
"""

COULEURS = ["#D85A30", "#1D9E75", "#378ADD", "#BA7517", "#7F77DD"]

def svg(etat_path, out=None, mode="derniere"):
    """Calque vectoriel destine au rendu INLINE dans la conversation, pas a un fichier
       image. Sort un <svg> autonome : espace de noms declare (il s'ouvre donc aussi
       tel quel dans un navigateur), viewBox 680 de large, et le carton dessine dedans.
       Le papier, le noir du visuel, les traits d'anneaux, les impacts et les scores sont
       des couleurs physiques, en dur : elles ne s'inversent pas en mode sombre. Sans le
       papier, le noir du visuel tombait sur le fond du fil — 1,04:1 en theme sombre,
       donc invisible. Seule la legende, ecrite hors du carton, suit le theme
       (class ts, var(--t) avec repli en dur).
       Le score prend la couleur de sa serie, seule lisible aussi bien sur le noir du
       visuel que sur le papier.
       mode derniere = la serie courante en plein, les precedentes en cercles gris.
       mode toutes   = une couleur par serie, pour le recapitulatif de fin de seance.
       Un chemin de sortie en .html emballe le SVG dans une page autonome : hors de
       l'outil de rendu inline, var(--b), var(--t) et la classe ts n'existent pas et
       les traits d'anneaux partiraient en noir. C'est la forme publiable en artefact."""
    from xml.sax.saxutils import escape as esc
    e = json.load(open(etat_path))
    r10, pas = e["r10_mm"], e["pas_mm"]; cal = e.get("calibre_mm", 4.5)
    noir = e.get("noir_mm", r10+3*pas); nmax = e.get("anneaux", 10)
    rmax = r10 + (nmax-1)*pas
    series = e.get("series", [])
    cx, cy, R = 340, 250, 210.0
    s = R/rmax; rp = cal/2*s
    px = lambda X, Y: (cx + X*s, cy - Y*s)
    L = ['<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#fdfdfb" '
         'stroke="#e3e1d9"/>' % (cx-230, cy-230, 460, 460),
         '<circle cx="%d" cy="%d" r="%.1f" fill="#1a1a1a"/>' % (cx, cy, noir*s)]
    for k in range(nmax, 0, -1):
        r = (r10 + (nmax-k)*pas)*s
        col = "#ffffff" if r <= noir*s - .5 else "#3a3a3a"
        L.append('<circle cx="%d" cy="%d" r="%.1f" fill="none" stroke="%s" stroke-width="0.5"/>'
                 % (cx, cy, r, col))
    legende = []
    for i, ser in enumerate(series):
        derniere = ser is series[-1]
        if mode == "toutes":
            col = COULEURS[i % len(COULEURS)]; plein, trace = False, True
        else:
            col = COULEURS[0]; plein, trace = derniere, True
        if not trace: continue
        for imp in ser["impacts"]:
            a, b = px(imp["x"], imp["y"])
            if plein:
                L.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (a, b, rp, col))
                L.append('<text font-size="11" fill="%s" x="%.1f" y="%.1f">%s</text>'
                         % (col, a+rp+2, b-rp-1, esc(str(imp.get("score", "")))))
            else:
                gris = mode != "toutes"
                L.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                         'stroke-width="1.2"/>' % (a, b, rp, "#7a8a99" if gris else col))
        if ser["impacts"] and (mode == "toutes" or derniere):
            n = len(ser["impacts"])
            a, b = px(sum(i["x"] for i in ser["impacts"])/n, sum(i["y"] for i in ser["impacts"])/n)
            L.append('<path d="M%.1f %.1fH%.1fM%.1f %.1fV%.1f" stroke="%s" stroke-width="2.5" '
                     'fill="none"/>' % (a-7, b, a+7, a, b-7, b+7, col))
        if mode == "toutes":
            tot = sum(i.get("score", 0) for i in ser["impacts"])
            legende.append((col, "S%d : %d" % (i+1, tot)))
    H = 500
    if legende:
        H = 524
        x = 340 - (len(legende)*96)//2
        for col, txt in legende:
            L.append('<circle cx="%d" cy="492" r="5" fill="%s"/>' % (x, col))
            L.append('<text class="ts" font-size="11" fill="var(--t, #444444)" x="%d" y="496">%s</text>' % (x+10, esc(txt)))
            x += 96
    nd_ = len(series[-1]["impacts"]) if series else 0
    desc = ("Superposition des %d series de la seance." % len(series) if mode == "toutes"
            else "Serie %d : %d impacts, les series precedentes en cercles gris."
                 % (len(series), nd_))
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" width="100%%" viewBox="0 0 680 %d" '
           'role="img"><title>%s</title><desc>%s</desc>\n%s\n</svg>'
           ) % (H, esc(str(e.get("cible", "cible"))), esc(desc), "\n".join(L))
    if out and out.endswith(".html"):
        doc = PAGE % doc
    if out and out != "-": open(out, "w").write(doc); print(out)
    else: print(doc)

def overlay(etat_path, out):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    e = json.load(open(etat_path))
    r10, pas = e["r10_mm"], e["pas_mm"]; cal = e.get("calibre_mm", 4.5)
    noir = e.get("noir_mm", r10+3*pas); nmax = e.get("anneaux", 10)
    rmax = r10 + (nmax-1)*pas
    fig, ax = plt.subplots(figsize=(6, 6.6), dpi=170); ax.set_facecolor("#fdfdfb")
    ax.add_patch(Circle((0,0), noir, facecolor="#1a1a1a", edgecolor="none", zorder=0))
    for k in range(nmax, 0, -1):
        r = r10 + (nmax-k)*pas
        ax.add_patch(Circle((0,0), r, facecolor="none", zorder=2, lw=.9,
                            edgecolor="#ffffff" if r <= noir+.01 else "#3a3a3a"))
    for s in e.get("series", []):
        rec = s is e["series"][-1]
        for imp in s["impacts"]:
            ax.add_patch(Circle((imp["x"], imp["y"]), cal/2, zorder=4,
                                facecolor="#d1341f" if rec else "none",
                                edgecolor="#d1341f" if rec else "#7a8a99", lw=1.6))
            if rec: ax.annotate(str(imp.get("score", "")),
                                (imp["x"]+cal*.8, imp["y"]+cal*.8),
                                color="#d1341f", fontsize=7, zorder=5)
    der = e["series"][-1] if e.get("series") else None
    if der and len(der["impacts"]) > 1:
        n = len(der["impacts"])
        ax.plot([sum(i["x"] for i in der["impacts"])/n], [sum(i["y"] for i in der["impacts"])/n],
                marker="+", ms=11, mew=2, color="#0b7285", zorder=6)
    lim = rmax*1.05; ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_aspect("equal"); ax.axis("off")
    nd_ = len(der["impacts"]) if der else 0
    ax.set_title(f"{e.get('cible','cible')} - serie {len(e.get('series',[]))} ({nd_} impacts)",
                 fontsize=10, color="#222", pad=8)
    fig.text(.5, .035, "rouge = nouveaux - gris = anciens - + = centre du groupe",
             ha="center", fontsize=7.5, color="#666")
    fig.savefig(out, bbox_inches="tight", facecolor="#fdfdfb"); print(out)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "tiles":     tiles(sys.argv[2], sys.argv[3])
    elif cmd == "zoom":    zoom(sys.argv[2], *[int(v) for v in sys.argv[3:8]], sys.argv[8])
    elif cmd == "overlay": overlay(sys.argv[2], sys.argv[3])
    elif cmd == "svg":     svg(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None,
                               sys.argv[4] if len(sys.argv) > 4 else "derniere")
    elif cmd == "analyse":
        r, p, b, e = analyser(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ".",
                              int(sys.argv[5]) if len(sys.argv) > 5 else None)
        print(json.dumps(r, indent=1))
    else: raise SystemExit("commandes : tiles | zoom | analyse | svg | overlay")
