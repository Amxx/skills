# Validation

Les photos de cartons ne sont pas versionnées : déposer les siennes dans `tests/cartons/`.

`valider.py` rejoue une séance complète et compare la détection à une vérité établie
à la main. Il mesure ce qui compte vraiment : le nombre d'impacts justes, le nombre de
faux positifs, et le temps.

1. Déposer les photos dans `tests/cartons/` (une par série, dans l'ordre de tir).
2. Écrire `tests/verite.json` : pour chaque série, la liste des impacts en millimètres
   dans le repère de la cible (origine au centre, x à droite, y en haut), relevés à la
   main sur les calques.

```json
{
  "coups_par_serie": 10,
  "series": [
    {"photo": "IMG_5417.jpeg", "carton": 1,
     "impacts": [{"x": 4.3, "y": 15.3, "score": 9}]},
    {"photo": "IMG_5418.jpeg", "carton": 1, "impacts": []}
  ]
}
```

   `carton` sert à savoir quand repartir d'un carton vierge : un changement de numéro
   remet l'état à zéro.

3. Lancer :

```bash
python3 tests/valider.py
```

Un impact est compté juste s'il tombe à moins de 2,5 mm de sa position vraie.
