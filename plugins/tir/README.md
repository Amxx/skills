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

**Claude Code**

```bash
cp -r tir ~/.claude/skills/tir      # global
cp -r tir .claude/skills/tir        # ou limité à un projet
```

**API Claude** — le dossier `tir/` est un bundle de skill standard, uploadable tel quel
sur `/v1/skills`.

## Utilisation

Envoyer une photo du carton. La skill se déclenche seule ; `/tir` la force.
Préférences en tête de `tir/SKILL.md` : main du tireur, discipline par défaut,
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

`tir/SKILL.md` est la **source unique** : le script Python y vit dans un bloc de code.
Rien n'est dupliqué dans le dépôt, il n'y a donc pas de dérive possible entre les deux.

```bash
./scripts/extraire.py        # sort le script dans build/cible.py
./scripts/verifier.py        # vérifie frontmatter + syntaxe du script
./scripts/build.sh           # vérifie puis produit tir.skill
```

Pour rejouer la validation, déposer des photos de cartons dans `tests/cartons/`
et voir `tests/README.md`.

## Licence

MIT — voir `LICENSE`.
