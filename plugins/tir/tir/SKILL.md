---
name: tir
description: "Analyse une photo de cible de tir (ISSF 10m/25m/50m) : distingue les nouveaux impacts des anciens, score la série, mesure le groupement et suit la séance. Dès qu'une photo de cible ou de carton est envoyée."
---

# Analyse de cible de tir

Le tireur est au stand, sur téléphone. Il envoie **une photo et rien d'autre**. Tout le reste est déduit. Ne pose une question que si la photo est inexploitable ou si un impact est réellement ambigu — jamais pour du confort.

**Le chemin nominal tient en quatre appels** : `analyse` (tout le calcul), lecture de la planche-contact, lecture du calque, envoi au tireur. Ne pas refaire à la main ce que `analyse` produit déjà.

## Autonomie — aucun ordinateur requis

Tout se fait **dans le conteneur cloud de la session** : la photo arrive par l'upload de la conversation, le calcul tourne en Python dans le conteneur, la réponse repart dans la conversation.

- Ne jamais utiliser d'outil `mcp__remote-devices__*` (ordinateur lié), ni chercher un dossier connecté, ni proposer d'en connecter un. L'ordinateur du tireur peut être éteint — c'est le cas nominal.
- Si la conversation affiche un ordinateur lié et que celui-ci est injoignable, l'ignorer complètement.
- `PIL`, `numpy`, `scipy` et `matplotlib` sont présents ; sinon `pip install pillow numpy scipy matplotlib --break-system-packages`.

## Préférences (à éditer par le tireur)

```yaml
main: droitier          # droitier | gaucher — inverse le diagnostic lateral
discipline_defaut: 10m pistolet a air
unite_groupe: mm        # mm | MOA | les deux
clic_hausse: null       # ex. "1 clic = 2 mm a 10 m" -> correction donnee en clics
coups_par_serie: 10     # taille de serie attendue — sert de controle de comptage
```

## État de la séance

Tout vit dans `~/tir/etat.json`. Attention : `~` n'est pas forcément le répertoire courant du shell — **chemins absolus partout**, pour le fichier comme pour le script. Une nouvelle conversation = une nouvelle séance.

```json
{
  "cible": "ISSF 10m pistolet à air", "r10_mm": 5.75, "pas_mm": 8,
  "calibre_mm": 4.5, "noir_mm": 29.75, "anneaux": 10, "distance_m": 10,
  "series": [
    {"n": 1, "photo": "...", "impacts": [{"x": -12.0, "y": 8.0, "score": 8}]}
  ],
  "cartons": 1
}
```

**Si le fichier a disparu** alors que la conversation contient déjà des séries — le conteneur est recyclé après une longue inactivité, et il se passe facilement vingt minutes entre deux séries — le **reconstruire depuis la conversation** : les versions précédentes de `etat.json` figurent intégralement dans les appels d'outils antérieurs. Reprendre la dernière, réécrire fichier et script, continuer sans rien dire. Ne jamais annoncer une remise à zéro pour cette raison : ça se lirait comme un carton neuf.

**Repère** : origine au centre des anneaux, `x` à droite, `y` en haut, **en millimètres réels sur le carton**. C'est le point clé : exprimer les impacts dans le repère de la cible les rend comparables d'une photo à l'autre quels que soient l'angle et le cadrage.

## Barèmes

`r10` = rayon du 10, `pas` = incrément par anneau, `noir` = rayon du visuel. En mm.

| Cible | r10 | pas | noir | anneaux | calibre |
|---|---|---|---|---|---|
| 10 m pistolet à air | 5,75 | 8 | 29,75 | 10 | 4,5 |
| 10 m carabine à air | 0,25 | 2,5 | 15,25 | 10 | 4,5 |
| 25 m précision / 50 m pistolet | 25 | 25 | 100 | 10 | 5,6 ou 9,0 |
| 25 m vitesse | 50 | 25 | à confirmer | 5→10 | 5,6 |
| 50 m carabine | 5,2 | 4 | 56,2 | 10 | 5,6 |

Le test d'identification le plus sûr est le rapport **`noir / pas`** en pixels, insensible au cadrage : 3,72 au 10 m pistolet, 6,1 au 10 m carabine, 4 au 25/50 m pistolet, 14 au 50 m carabine. Si le doute persiste, prendre `discipline_defaut`, l'annoncer en une demi-ligne, continuer.

**Score.** Un impact compte dans l'anneau supérieur dès qu'il le *touche* (règle de la jauge). Avec `r` = distance centre-du-trou → centre et `re = max(0, r − calibre/2)` : `re ≤ r10` → 10 ; sinon `10 − ceil((re − r10)/pas)`, plancher à 0.

## Procédure

### 1. Un seul appel fait tout le calcul

Écrire `~/tir/cible.py` (script en fin de fiche, à recréer s'il n'est plus là) puis :

```bash
python3 ~/tir/cible.py analyse <photo> ~/tir/etat.json ~/tir/vue
```

Il enchaîne, sans aucun aller-retour : calage géométrique → détection des trous dans les trois polarités → décomposition des amas → recalage sur les anciens impacts → appariement → score → `planche.png`. Compter 40 à 60 s de calcul ; c'est normal, ne pas relancer.

Passer `-` à la place de `etat.json` pour un carton neuf.

Ce qu'il rend :

| Champ | Ce qu'il faut en faire |
|---|---|
| `geom.rms_px`, `geom.bord_px` | auto-contrôle du calage. **rms > 3 px ou bord > 4 px → ne pas faire confiance**, relever les traits à la main (§ 2 bis) |
| `anciens_retrouves / anciens_attendus` | doit être quasi complet. Un seul manquant est un défaut de détection, pas un trou disparu |
| `somme_k_aire` | nombre total de trous estimé par les aires — doit tomber sur `anciens + coups_par_serie` |
| `nouveaux` | **une proposition, pas un verdict** : à confirmer sur la planche |
| `aire_trou_ref` | aire d'un trou isolé, mesurée par fond (noir et beige diffèrent) |

### 2. Confirmer sur la planche-contact — obligatoire

Lire `~/tir/vue/planche.png` : une seule image qui réunit toutes les zones à vérifier, avec les disques ajustés dessinés dessus (rouge = nouveau, bleu = ancien). Une lecture d'image au lieu de six à huit.

Trois choses à y chercher, dans cet ordre :

- **Un disque rouge posé sur rien** — sur une pointe de pince, un bord de carton, une ombre. À supprimer.
- **Un disque rouge dans un creux** entre deux lobes qui se chevauchent. Trois trous qui se touchent laissent un creux concave qu'un disque de trop vient combler : c'est le faux positif le plus fréquent, et l'aire l'aurait écarté. À supprimer.
- **Un lobe rond sans disque** — impact manqué. À ajouter.

Puis les zones que la planche ne montre pas forcément : zoomer à l'œil sur **chaque pince et sur le pourtour du carton** (`zoom`). Un trou qui touche un occultant se fond dans sa composante et sort des listes.

Enfin le **comptage** : le nombre de nouveaux doit valoir `coups_par_serie` (ou 5). Un compte bâtard — 9 au lieu de 10 — n'est pas un résultat à rapporter tel quel, c'est le signal qu'il manque un trou. Si après reprise le compte reste court, le dire et proposer l'explication : sur un carton saturé, une balle peut repasser par un trou existant.

### 2 bis. Si le calage automatique échoue

Relever les traits d'anneaux à la main le long des deux axes (minima sur beige, maxima sur noir) et ajuster `x = x0 + fx·X/(1 + kx·X)` et `y = y0 + fy·Y/(1 + ky·Y)` par moindres carrés. Deux pièges :

- **les chiffres d'anneaux sont imprimés sur les axes** et produisent de faux traits à mi-distance ; vrais traits et chiffres alternent, donc le pas apparent vaut la moitié du pas réel. Vérifier avec `noir = r10 + 3·pas`.
- **le centre de l'ellipse du noir n'est pas le centre de la cible** sous perspective — jusqu'à 2 mm, soit un quart d'anneau. Prendre le centre de l'ajustement, ou à défaut le petit cercle du « dix intérieur ».

Le modèle complet est `x = x0 + fx·X/w`, `y = y0 + fy·Y/w` avec `w = 1 + kx·X + ky·Y` ; son inverse est `w = 1/(1 − kx·(x−x0)/fx − ky·(y−y0)/fy)`.

### 3. Ce que le script fait, et pourquoi

Utile quand il faut le déboguer ou le refaire à la main.

**Détection — trois polarités, jamais une seule fenêtre de luminosité.** Selon le support derrière le carton, l'angle et l'éclairage, un même trou prend trois aspects : clair sur noir, gris sur beige (papier arraché, cas courant), et **sombre sur beige** quand la balle perce net — celui-là est aussi sombre qu'un trait d'anneau. On compare donc au fond local (médian de ~4 calibres) et on garde les écarts dans les deux sens.

**Fermer avant d'ouvrir.** Un trou peut avoir au fond une ombre aussi noire que le visuel, qui le coupe en deux ; l'ouverture réduit chaque moitié sous le seuil de surface et le trou disparaît. Fermeture → ouverture → fermeture, élément structurant `0,28·calibre`, plancher de surface bas.

**Ouverture avant l'étiquetage du disque noir.** Sans elle, un trou traversant collé au bord du visuel fait un pont, la boîte englobante s'étend, et tout le calage vertical part de plusieurs millimètres.

**L'aire décide du nombre de trous d'un amas**, pas le coude de l'IoU : `k = aire du blob / aire d'un trou isolé du même fond`. Cette aire de référence se mesure sur la photo en cours, séparément sur beige et sur noir. L'ajustement de disques ne fait que **placer** les `k` trous.

**Placement glouton puis raffinement.** On convolue le masque résiduel par le disque du calibre, on pose le disque sur le maximum de couverture, on recommence, puis descente locale avec quelques redémarrages. Quelques dizaines de millisecondes par amas, contre plusieurs minutes pour une recherche naïve.

**Recalage sur les anciens impacts.** Une fois les disques trouvés, les impacts déjà connus forment des dizaines de points de contrôle : on réajuste le modèle sur eux. C'est ce qui rattrape le millimètre résiduel du calage et permet d'apparier proprement.

Deux pièges qui restent : un blob **coupé par le bord du noir** apparaît en deux morceaux, un par polarité, et ne vaut qu'un impact ; deux disques **quasi confondus** (< 0,45 calibre) sont toujours un `k` de trop.

### 4. Verdict carton

- **impacts non appariés → nouveaux tirs** : c'est la série à évaluer ;
- **≥ 70 % des anciens retrouvés** → même carton, on continue ;
- **< 50 %, ou moins de trous qu'avant** → des **pastilles de masquage** visibles → même carton rebouché, le cumul de séance est conservé ; aucune pastille → **carton neuf** : archiver, vider les impacts, `cartons += 1`, repartir à la série 1, le dire en une ligne sans demander confirmation ;
- **zéro trou** → carton vierge, on enregistre et on attend.

Ce verdict se fonde sur la **photo**, jamais sur l'état du fichier : un `etat.json` manquant se reconstruit. La position enregistrée d'un impact issu d'un amas dense peut être fausse de 2 à 3 mm — tolérance plus large pour ceux-là. En cas d'ambiguïté réelle (moitié des impacts retrouvés, pas de pastille), demander — c'est le seul cas qui vaut une question.

### 5. Mesurer

- **Score** de chaque nouvel impact et total.
- **Groupement** : *extreme spread* = plus grande distance centre à centre (le préciser). Rayon moyen. Centre du groupe (MPI) avec son écart au centre, en mm et en **position horaire** (12 h = haut) — c'est la langue des tireurs.
- **Écarts-types séparés en X et en Y** : leur rapport dit tout de suite si la dispersion est verticale ou horizontale, là où l'ES seul ne dit rien.
- **MOA** si demandé : `ES_mm / (0,291 × distance_m)`.
- **Correction** : en clics si `clic_hausse` est renseigné, sinon en mm et en sens.

### 6. Diagnostic

Des **hypothèses**, jamais un verdict — une photo ne dit pas ce qu'ont fait les mains. Un tir isolé ne diagnostique rien : ne commenter que ce qui se répète.

Positions pour un **droitier au pistolet** (miroir horizontal si `main: gaucher`) :

| Zone | Piste |
|---|---|
| 6 h, bas | anticipation du départ, « talonnage », crispation à la détente |
| 7–8 h, bas-gauche | trop de doigt sur la queue de détente, serrage de la main au lâcher |
| 9 h, gauche | trop de doigt / détente prise sur la 2ᵉ phalange |
| 3 h, droite | pas assez de doigt, poussée du pouce |
| 12 h, haut | lâcher précipité, guidon trop haut dans la hausse |
| dispersion verticale | respiration, alignement vertical guidon/hausse, rythme irrégulier |
| dispersion horizontale | position/pieds, prise en main inégale, tête mobile |
| dispersion large sans motif | fatigue, accommodation perdue, série trop longue |

À la carabine : vertical → respiration et appui ; horizontal → position et point d'équilibre.

Un groupe **serré mais décalé** est un problème de réglage d'arme, pas de technique — c'est la distinction la plus utile. Mais un décalage ne vaut comme réglage que s'il est **stable d'une série à l'autre** : un MPI qui saute de +20 à +8 puis +21 mm est de la dispersion, pas un zéro faux. Le vérifier sur les séries enregistrées avant de proposer une correction de hausse.

Quand une série est bonne sauf deux coups très à l'extérieur, le dire ainsi : donner le groupe sans eux, et regarder s'ils partagent une dérive ou une hauteur — deux coups à la même dérive et opposés en hauteur désignent l'élévation.

### 7. Calque et envoi

Écrire `etat.json`, puis :

```bash
python3 ~/tir/cible.py overlay ~/tir/etat.json ~/tir/calque.png
```

Parcourir le calque **impact par impact** dans l'ordre horaire, et dans les deux sens : photo → calque rattrape les oublis, calque → photo rattrape les inventions. Puis envoyer `calque.png` avec `SendUserFile` : sur téléphone, c'est le moyen le plus rapide de vérifier d'un coup d'œil.

### 8. Répondre — court

Écran de téléphone : pas de titres, pas de tableau, quelques lignes. **Annoncer le nombre d'impacts** dès la première ligne.

```
Série 3 — 5 nouveaux impacts
9 · 10 · 8 · 9 · 7 → 43/50 (moy 8,6)
Groupe 34 mm centre à centre, centré à 12 mm en 7 h 30
Groupe correct mais décalé bas-gauche → plutôt un réglage qu'un défaut de lâcher.
Séance : 3 séries, 127/150, groupe moyen 31 mm (−6 mm depuis la série 1)
```

À partir de la 3ᵉ série, une ligne de tendance. En fin de séance, proposer un récapitulatif graphique — pas avant.

## Honnêteté

Une lecture photo n'est pas un jugement de match : annoncer les scores comme **estimations**, et signaler tout impact sur une ligne d'anneau ou de lecture douteuse plutôt que de trancher en silence. Si la photo est floue, très inclinée, ou le carton coupé, le dire en une ligne et demander un cliché de face avec le carton entier.

Si le tireur corrige le relevé — impact manqué ou impact inventé : le vérifier sur la photo, le mesurer, et **reprendre tout ce qui en découlait** : total, groupement, tendance, et le diagnostic s'il s'appuyait sur le décompte. Dire en une ligne pourquoi la détection s'est trompée, sans en faire un plat. Le tireur a le carton sous les yeux : sur un désaccord de comptage, il a raison.

### Contrôle de comptage et limites mesurées

`analyse` renvoie un champ `comptage` : `{coups_attendus, obtenus, ajustements, ok}`.
**`ok: false` = le compte ne tombe pas juste : ouvrir la planche-contact et vérifier avant de répondre.**
Le script ne fabrique jamais un impact pour faire le compte : il ne redécoupe un amas
que si son aire le justifie (`k_aire - k > 0.3`), sinon il signale le manque.

Mesuré sur les 5 cartons de la séance du 19/09/2025 (50 impacts, vérité établie à la main) :

| | avant | après |
|---|---|---|
| impacts justes | 38/50 | **44/50** |
| faux positifs (pinces) | 4 | **2** |
| temps pour 5 cartons | > 25 min | **45 s** |

Ce qui reste fragile, et qu'il faut vérifier à l'œil :
- **les amas de 3 trous et plus** — la décomposition en sous-compte encore (4 manques sur 6) ;
- **un carton chargé** : au-delà de 20 trous, changer de carton coûte moins cher que la vérification.

Un `ok: true` ne garantit pas l'exactitude : il peut masquer un faux positif qui compense un manque.

## Script `~/tir/cible.py`

```python
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
    elif cmd == "analyse":
        r, p, b, e = analyser(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ".",
                              int(sys.argv[5]) if len(sys.argv) > 5 else None)
        print(json.dumps(r, indent=1))
    else: raise SystemExit("commandes : tiles | zoom | analyse | overlay")
```