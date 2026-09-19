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

`claude plugin validate plugins/<nom>` et `claude plugin validate .` contrôlent les deux
manifestes. Le `scripts/verifier.py` de `tir` vérifie en plus que les trois noms concordent —
c'est la dérive qui casse l'installation le plus silencieusement.

## Licence

MIT — chaque plugin porte son `LICENSE`.
