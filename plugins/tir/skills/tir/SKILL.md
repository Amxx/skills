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

**Si le fichier a disparu** alors que la conversation contient déjà des séries — le conteneur est recyclé après une longue inactivité, et il se passe facilement vingt minutes entre deux séries — le **reconstruire depuis la conversation** : les versions précédentes de `etat.json` figurent intégralement dans les appels d'outils antérieurs. Reprendre la dernière, réécrire le fichier, continuer sans rien dire. Le script, lui, est livré avec la fiche : il n'est jamais à recréer. Ne jamais annoncer une remise à zéro pour cette raison : ça se lirait comme un carton neuf.

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

### 0. Le script est livré avec la fiche

`scripts/cible.py`, dans le dossier de cette skill. **Ne jamais le recopier, le réécrire ni
le régénérer** : c'est un fichier de 500 lignes de calcul numérique, une transcription à la
main y glisserait une erreur invisible.

Repérer son chemin absolu **une fois** en début de séance, et le réutiliser tel quel ensuite
— les variables shell ne survivent pas d'un appel à l'autre. Il est noté `CIBLE` ci-dessous.

```bash
ls "$CLAUDE_PLUGIN_ROOT/skills/tir/scripts/cible.py"   # Claude Code, installé en plugin
```

Ailleurs (claude.ai, API), la skill est dépliée dans un dossier du conteneur : `cible.py`
est dans son sous-dossier `scripts/`. Si le chemin reste introuvable, le dire et s'arrêter
là — ne pas reconstruire le script depuis la conversation.

### 1. Un seul appel fait tout le calcul

```bash
python3 <CIBLE> analyse <photo> ~/tir/etat.json ~/tir/vue
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
python3 <CIBLE> overlay ~/tir/etat.json ~/tir/calque.png
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
