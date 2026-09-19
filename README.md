# skills — marketplace de plugins Claude Code

Un dépôt, un marketplace, un plugin par dossier dans `plugins/`.

## Installation

```
/plugin marketplace add Amxx/skills
/plugin install tir@amxx
```

`/plugin update <nom>@amxx` ensuite, et `/plugin marketplace update amxx` pour rafraîchir
la liste.

## Plugins

| Plugin | Ce qu'il fait |
|---|---|
| [`tir`](plugins/tir) | Lit une photo de carton de tir (ISSF 10 m / 25 m / 50 m) : distingue les nouveaux impacts des anciens, score la série, mesure le groupement et suit la séance. |

## Organisation

```
.claude-plugin/marketplace.json   le catalogue : une entrée par plugin
.github/workflows/<nom>.yml       une CI par plugin, filtrée sur son dossier
.github/workflows/release.yml     publication, commune à tous les plugins
scripts/package.py                empaquette un plugin : archive, .zip, notes
plugins/<nom>/
├── .claude-plugin/plugin.json    nom, version, licence
├── skills/<nom>/SKILL.md         la fiche, plus ses scripts/ et références
├── scripts/                      outillage de dev : vérification, fumée, empaquetage
└── tests/                        validation mesurée, sur données non versionnées
```

Les archives `*.skill` ne sont pas versionnées : le `build.sh` de chaque plugin les
reconstruit depuis les sources.

## Ajouter un plugin

1. `plugins/<nom>/.claude-plugin/plugin.json` — le `name` doit valoir le nom du dossier ;
2. la skill dans `plugins/<nom>/skills/<nom>/` — c'est là que Claude Code la découvre ;
3. une entrée dans `.claude-plugin/marketplace.json`, `source` pointant sur `./plugins/<nom>` ;
4. un workflow `.github/workflows/<nom>.yml` filtré sur `plugins/<nom>/**`.

Un plugin publiable doit aussi savoir se construire : `plugins/<nom>/scripts/build.sh`
doit produire `<nom>.skill` à la racine du plugin. C'est le seul contrat que la release
attend.

`claude plugin validate plugins/<nom>` et `claude plugin validate .` contrôlent les deux
manifestes. Le `scripts/verify.py` de `tir` vérifie en plus que les trois noms concordent —
c'est la dérive qui casse l'installation le plus silencieusement.

## Publier une version

Poser un tag `<nom>--v<version>` suffit : le workflow `release` construit l'archive,
vérifie qu'elle s'importe, et crée la release GitHub avec les notes du CHANGELOG.

```bash
claude plugin tag plugins/tir     # pose tir--v<version>, en contrôlant les manifestes
git push origin tir--v1.1.0
```

Depuis l'onglet Actions, « release » se déclenche aussi à la main en donnant le nom du
plugin — la version est alors lue dans `plugin.json`.

Chaque release porte deux fichiers identiques : `<nom>.skill` et `<nom>.zip`. Le second
existe parce que l'import de skill sur claude.ai attend l'extension `.zip`.

Pour construire sans publier :

```bash
./scripts/package.py tir          # -> dist/tir.skill, dist/tir.zip, dist/notes.md
```

## Licence

MIT — chaque plugin porte son `LICENSE`.
