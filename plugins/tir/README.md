# tir — analyse de carton de tir

Skill Claude qui lit une photo de carton de tir (ISSF 10 m / 25 m / 50 m), distingue
les nouveaux impacts des anciens, score la série, mesure le groupement et suit la séance.

Le tireur envoie **une photo et rien d'autre**. Tout le reste est déduit : type de cible,
échelle, perspective, impacts déjà présents.

## Ce que ça produit

- le score de la série, impact par impact, avec la marge à la ligne d'anneau la plus proche
- le groupement : écart maximum, rayon moyen, écart-type par axe
- la position du centre du groupe, comparée aux séries précédentes
- un calque de la cible et une planche-contact pour vérifier la lecture
- un diagnostic qui distingue ce qui relève du réglage de l'arme et ce qui relève du geste

## Installation

**claude.ai / application de bureau**

```bash
./scripts/build.sh          # produit tir.skill
```

Puis : photo de profil → Paramètres → Capacités → Compétences → importer `tir.skill`.
Le `name: tir` du frontmatter est inchangé, donc un réimport remplace la version existante.

**Claude Code — plugin (recommandé)**

```bash
/plugin marketplace add Amxx/skills
/plugin install tir@amxx
```

La skill est alors découverte automatiquement, et `/plugin update tir@amxx` suffit ensuite.
Sans passer par le marketplace, une copie manuelle fait la même chose :

```bash
cp -r skills/tir ~/.claude/skills/tir      # global
cp -r skills/tir .claude/skills/tir        # ou limité à un projet
```

**API Claude** — le dossier `skills/tir/` est un bundle de skill standard, uploadable tel
quel sur `/v1/skills`.

## Utilisation

Envoyer une photo du carton. La skill se déclenche seule ; `/tir` la force.
Préférences en tête de `skills/tir/SKILL.md` : main du tireur, discipline par défaut,
unité de groupement, valeur d'un clic de hausse, nombre de coups par série.

## Fiabilité mesurée

Sur 5 cartons d'une même séance, 50 impacts, vérité établie à la main :

| | avant correctifs | après |
|---|---|---|
| impacts justes | 38/50 | **44/50** |
| faux positifs (pinces prises pour des trous) | 4 | **2** |
| temps de traitement, 5 cartons | > 25 min | **45 s** |

Les scores sont des **estimations photo**, pas un jugement de match. La skill signale
d'elle-même les impacts à cheval sur une ligne d'anneau.

## Limites connues

- **Les amas de trois trous et plus** restent le point faible : la décomposition
  sous-compte. Les six impacts encore manqués sur les 50 y sont tous.
- **Au-delà de 20 trous sur un carton**, changer de carton coûte moins cher que la
  vérification manuelle. Un plomb peut aussi repasser par un trou existant.
- Un `comptage.ok: true` ne garantit pas l'exactitude : un faux positif peut compenser
  un manque.
- Photo la plus perpendiculaire possible, carton entier dans le cadre, éclairage régulier.
  Le résidu de calage géométrique est reporté dans la sortie (`geom.rms_px`) : au-delà
  de 3 px, la lecture devient douteuse et la skill le dit.

## Développement

La skill tient en deux fichiers, chacun source unique de son côté :

- `skills/tir/SKILL.md` — la procédure, ce que Claude lit ;
- `skills/tir/scripts/cible.py` — le moteur, livré tel quel et exécuté depuis le dossier
  de la skill. Il n'est jamais transcrit ni recopié : rien ne peut donc diverger, et la
  fiche reste courte au lieu de traîner 500 lignes de Python dans le contexte.

```bash
./scripts/verifier.py        # manifestes, frontmatter, syntaxe de cible.py, commandes
./scripts/fumee.py           # cible.py s'importe vraiment et expose ses quatre commandes
./scripts/build.sh           # vérifie puis produit tir.skill
```

`tir.skill` est un artefact : il n'est pas versionné, `build.sh` le reconstruit.

Pour rejouer la validation, déposer des photos de cartons dans `tests/cartons/`
et voir `tests/README.md`.

## Licence

MIT — voir `LICENSE`.
