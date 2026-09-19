# Journal des versions

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
