# Journal des versions

## 1.3.0 — 19/09/2026

Les résultats s'affichent dans la conversation au lieu d'être livrés en fichier. Le moteur
d'analyse ne bouge pas : les chiffres de détection de la 1.1.0 tiennent toujours.

- **Nouvelle commande `svg`.** Elle produit le calque en SVG autonome sur la sortie standard,
  à rendre inline dans le fil. Sur téléphone, ouvrir un PNG demandait trois manipulations pour
  voir ce qu'un coup d'œil suffit à vérifier. Le SVG suit en prime le thème clair/sombre.
- **Le calque ne passe plus par matplotlib** sur le chemin nominal : il est construit depuis
  les coordonnées déjà présentes dans `etat.json`, donc sans rendu d'image ni écriture disque.
  `overlay` reste là pour qui veut archiver un PNG.
- **Récapitulatif de séance sans image** : `svg … - toutes` superpose les séries, une couleur
  par série, et les courbes passent par le graphe natif de la conversation.
- **La planche-contact est explicitement interne.** La fiche disait de la lire, pas de ne pas
  l'envoyer ; elle ne sert qu'à la vérification et n'a rien à faire chez le tireur.
- **Le calque tient debout hors de la conversation** : espace de noms déclaré, repli de
  couleur en dur derrière chaque variable de thème, titre et description échappés. Le fichier
  produit par `svg etat.json calque.svg` s'ouvre donc tel quel dans un navigateur.

## 1.2.1 — 19/09/2026

Correction de fiche : le moteur ne bouge pas, les chiffres de détection de la 1.1.0 non plus.

- **La sortie d'`analyse` va dans un fichier.** La fiche donnait la commande sans dire quoi
  faire de son JSON — plusieurs centaines de lignes, qu'une lecture à travers `head` ou `tail`
  tronque et perd, imposant un recalcul complet de 40 à 60 s. La commande redirige désormais
  vers `~/tir/analyse.json`, relu ensuite champ par champ, contrôles d'abord.
- **`mkdir -p ~/tir/vue` avant l'appel.** Ni la redirection ni `planche.png` ne créent leur
  dossier : sur un conteneur neuf, le premier appel de la séance échouait.

## 1.2.0 — 19/09/2026

Rien ne change à la lecture des cartons : les chiffres de la 1.1.0 tiennent toujours.
Cette version ne touche qu'à la distribution et au rangement.

- **Plugin Claude Code installable.** Le dépôt est devenu un marketplace :
  `/plugin marketplace add Amxx/skills` puis `/plugin install shooting@amxx`. La copie
  manuelle dans `~/.claude/skills/` reste possible, et l'import sur claude.ai aussi.
- **Renommage — à relire si vous aviez déjà la version 1.1.0.** Le plugin s'appelle
  `shooting` (le domaine) et la skill `target-analysis` (ce qu'elle fait), là où `tir`
  désignait les deux. Conséquences : `tir@amxx` devient `shooting@amxx` et demande une
  réinstallation, et sur claude.ai le nouvel import crée une *seconde* skill à côté de
  l'ancienne — supprimer `tir` à la main après coup. La commande de forçage devient
  `/target-analysis`.
- **Le script sort de la fiche.** Le moteur ne vit plus dans un bloc de code de
  `SKILL.md` mais dans `skills/target-analysis/scripts/cible.py`, livré avec la skill et
  exécuté tel quel. La fiche passe de 723 à 234 lignes, et surtout Claude ne recopie plus
  500 lignes de calcul numérique à la main : une erreur de transcription y était invisible.
- **Archives publiées.** `shooting.skill` n'est plus versionné dans le dépôt ; chaque
  release porte `shooting.skill` et `shooting.zip` — le même fichier, l'extension `.zip`
  étant celle qu'attend l'import de skill sur claude.ai.

## 1.1.0 — 19/09/2026

Traitement ramené de plus de 5 minutes par carton à 6-15 secondes, et détection
nettement plus fiable. Mesuré sur 5 cartons, 50 impacts, vérité établie à la main :
38/50 justes et 4 faux positifs avant, **44/50 justes et 2 faux positifs après**.

- **Fond local par médiane sous-échantillonnée.** La médiane est calculée sur l'image
  réduite d'un facteur 3 puis ré-interpolée. Le fond varie lentement à l'échelle du
  calibre, le résultat est indiscernable : 90 s → 4 s sur une photo 1450×2576.
  C'était le goulot du pipeline.
- **Rejet des pinces.** Un vrai trou a une couronne de papier déchiré plus claire que
  le fond, ou un bord net ; la pince du porte-carton n'a ni l'un ni l'autre.
- **Seuils de détection adaptés au bruit du tirage** plutôt que fixes. C'est ce qui
  récupère le plus d'impacts : un carton passait de 5 détections sur 10 à 10 sur 10.
- **Quatrième polarité.** Un plomb qui arrache le papier sans laisser de plomb donne un
  trou *plus clair* que le beige ; le détecteur ne cherchait que le plus sombre.
  Une garde de rondeur empêche la pointe métallique brillante de repasser par là.
- **Contrôle de comptage.** Le nombre de coups tirés est connu : la sortie expose
  `comptage.ok`. Le script ne fabrique jamais un impact pour faire le compte — il ne
  redécoupe un amas que si son aire le justifie, sinon il signale le manque.

## 1.0.0

Version initiale : calage géométrique sous-pixel, détection, décomposition des amas,
score, groupement, suivi de séance, calque et planche-contact.
