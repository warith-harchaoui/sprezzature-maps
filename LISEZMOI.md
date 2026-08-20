# sprezzature-maps

[🇬🇧 README.md](README.md) · 🇫🇷 LISEZMOI.md

Cette bibliothèque dessine des cartes en SVG (Scalable Vector Graphics,
un format d'image construit à partir de lignes et de formes décrites en
texte plutôt qu'une grille de pixels, ce qui lui permet de rester nette
à n'importe quel niveau de zoom et de garder son texte sélectionnable).
Chaque trait est écrit à la main, par notre propre code de dessin :
rien ici ne passe par Vega (un moteur de graphiques piloté par JSON) ni
par matplotlib (la bibliothèque de tracé classique de Python).
`sprezzature-maps` faisait autrefois partie de
[sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures) ;
il en a été extrait pour devenir un produit à part entière, avec son
propre calendrier de sortie et, à terme, son propre éditeur visuel.

Fait partie de la suite [sprezzature](https://harchaoui.org/warith/sprezzature/).

---

## Ce qu'on trouve ici

Deux générateurs. Tous deux s'appuient sur un vrai fond de carte avec
une vraie projection géographique (une projection est la recette
mathématique qui aplatit la Terre ronde sur une image plate ; chaque
recette déforme quelque chose, et le choix ci-dessous n'a rien
d'arbitraire). C'est ce qui les distingue des types de cartes
schématiques par points ou par grille restés dans `sprezzature-figures`
(`binned-grid-map`, `dotdensity`, `hexbin-map`, `hexmap`, `spike-map`) :

| Type | Script | Ce qu'il dessine |
|---|---|---|
| `choropleth` (une carte où chaque région est remplie d'une couleur qui code un nombre, la carte classique du « quel pays a le score le plus élevé ») | `scripts/make_choropleth.py` | Une carte du monde, une couleur de remplissage par pays sur une seule échelle allant du pâle au bleu marine ; les pays sans donnée retombent sur un gris neutre. |
| `situation_map` | `scripts/make_situation_map.py` | Une planche en couches « qui contrôle quoi » pour n'importe quelle région : la carte se recentre automatiquement sur cette région via une projection conique conforme de Lambert (voir plus bas), trace de vrais contours nationaux depuis un fond de carte Natural Earth intégré, ombre le plancher océanique près des côtes, remplit les zones par catégorie en couleurs pastel, marque les points chauds, et ajoute une échelle en deux unités à la fois (kilomètres et miles). |

## Installation (locale, avant publication sur PyPI)

Ni `sprezzature-maps` ni `sprezzature-figures` ne sont encore publiés
sur PyPI (l'index officiel des paquets Python, celui que `pip install
<nom>` interroge par défaut). Installez les deux en mode éditable, l'un
à côté de l'autre, pour que toute modification locale de l'un ou
l'autre prenne effet immédiatement sans réinstallation :

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps ~/sprezzature-maps
pip install -e ~/sprezzature-maps
```

`sprezzature-maps` dépend de `sprezzature-figures` pour les
primitives de rendu que les deux produits partagent (intégrer les
polices directement dans le fichier SVG pour qu'il ait le même rendu
sur une machine sans ces polices installées, et choisir entre un SVG
autonome et un SVG qui renvoie vers des fichiers externes). Il
réutilise ce code plutôt que d'en garder sa propre copie.

## Utilisation

```python
from sprezzature_maps import make_choropleth, make_situation_map

make_choropleth(out="world.svg")          # données de démonstration si rien n'est fourni
make_situation_map(out="region.svg")      # configuration de démonstration intégrée
```

```bash
make-map choropleth --out world.svg
make-map situation_map --config my-region.yaml --out region.svg
```

Voir [`EXAMPLES.md`](EXAMPLES.md) pour davantage de recettes, y compris
l'API HTTP. Voir [`doc/CARTOGRAPHY.tex`](doc/CARTOGRAPHY.tex) pour la
méthode complète derrière chaque projection, chaque échelle de couleur
et chaque technique de relief utilisées dans ce dépôt : les
mathématiques sous-jacentes, les diagrammes TikZ, les citations et les
figures en résolution d'impression, compilé avec `xelatex`/`biber`
(le typographe Unicode de LaTeX et son outil de bibliographie) en
[`doc/CARTOGRAPHY.pdf`](doc/CARTOGRAPHY.pdf).

## Pourquoi un dépôt séparé plutôt qu'un type de graphique dans sprezzature-figures

Les deux générateurs vivaient autrefois dans le catalogue de 126 types
de graphiques de `sprezzature-figures`. Les en extraire a été une
décision de produit délibérée : Sprezzature Studio, l'éditeur de
graphiques conversationnel livré avec `sprezzature-figures`, ne gagnera
pas le support des cartes. Les cartes auront leur propre Studio séparé,
une fois construit. D'ici là, ce dépôt reste bibliothèque et ligne de
commande uniquement, sans interface d'édition.

## État du projet

Encore jeune. Fraîchement extrait de `sprezzature-figures`, avec une CI
au vert (lint, tests et doctests à chaque push et pull request vers
`main` ; voir `.github/workflows/ci.yml`) : `pytest` passe, les deux
types de carte se rendent depuis leurs données de démonstration
intégrées, et la ligne de commande produit de vrais fichiers SVG pour
les deux. Pas encore de publication sur PyPI, pas encore de page de
catalogue façon FIGURES.md (avec seulement deux types pour l'instant,
ce LISEZMOI en tient lieu).

`choropleth` dessine avec : une projection Equal Earth (une projection
qui conserve la surface relative réelle de chaque pays, si bien qu'une
masse continentale immense mais visuellement aplatie comme le
Groenland ou la Russie n'est pas exagérée comme sur une Mercator
classique) ; des frontières Natural Earth à l'échelle 1:50 000 000 (un
niveau de simplification adapté à une vue du monde entier, plus
grossier que le niveau de détail 1:10 000 000 utilisé pour une seule
région) ; une échelle de couleur calculée dans l'espace colorimétrique
OKLCH (une façon de décrire la couleur choisie ici parce que des pas
égaux en OKLCH se voient comme des pas égaux de luminosité perçue, si
bien que l'échelle reste lisible même pour quelqu'un qui ne distingue
pas le rouge du vert, la forme la plus courante de daltonisme) pour les
valeurs qui ne font que croître, plus une seconde échelle « divergente »
choisie automatiquement (deux couleurs qui s'écartent d'un point neutre
central, pour des valeurs qui peuvent être au-dessus ou en dessous d'un
seuil de référence) quand les données l'exigent ; une grille de
méridiens et parallèles tous les 30 degrés ; une légende affichant le
minimum, la médiane et le maximum ; des info-bulles au survol qui
ajoutent le rang de chaque pays et sa part du total ; et une image de
relief ombré du terrain terrestre, reprojetée pour correspondre,
placée sous les remplissages des pays. `situation_map` dessine avec :
une projection conique conforme de Lambert autocentrée (une projection
qui conserve les formes et les angles locaux autour d'un centre choisi,
le choix standard pour un seul pays ou une seule région plutôt que pour
le globe entier) ; une bande ombrée le long de la côte montrant la
vitesse à laquelle le plancher océanique s'enfonce ; et un choix
automatique entre le niveau de détail Natural Earth grossier et fin
selon le degré de zoom de la région demandée.

La bibliothèque se joint de cinq façons : par import Python ; par la
ligne de commande argparse (la bibliothèque standard de Python pour
analyser les arguments de ligne de commande) `make-map`, installée par
défaut ; par une ligne de commande Click plus riche,
`sprezzature-maps` (`sprezzature-maps[cli]`), qui ajoute l'ingestion de
CSV et le mappage de colonnes par-dessus ce que lit `make-map` ; par une
API HTTP (`sprezzature-maps[api]`) qui publie un schéma OpenAPI (une
description de chaque point d'entrée lisible par une machine,
permettant à d'autres outils de générer automatiquement de la
documentation ou du code client) et une petite page de galerie à sa
racine ; et par une surface MCP (Model Context Protocol, le standard
qui permet à un assistant IA d'appeler un outil directement) sous
`sprezzature-maps[api,mcp]`.

## Feuille de route

`situation_map` ombre déjà un relief réel sur sa projection conique
conforme de Lambert, activé par défaut (`_relief_layer` dans
`scripts/make_situation_map.py`), la même technique d'ombrage de
terrain que `choropleth` utilise pour la vue du monde entier en Equal
Earth, adaptée à l'inverse propre à cette autre projection. Quelques
points de moindre priorité du plan cartographique complet restent
consignés mais non planifiés : un relief construit à partir du jeu de
données d'élévation mondial ETOPO, des projections alternatives mieux
adaptées à une carte éditoriale (Robinson, Mollweide), et un lecteur
TopoJSON partagé unique (TopoJSON est un format compact qui enregistre
chaque frontière commune une seule fois, au lieu d'une fois par pays
voisin).

## Crédits des données

Le code est sous licence BSD-3-Clause (voir plus bas). Les données
géographiques intégrées sous `assets/geo/` portent leurs propres
licences séparées ; la liste complète avec les sources se trouve dans
`doc/CARTOGRAPHY.tex`, § Data provenance and licensing. La majeure
partie (Natural Earth, le jeu de données d'élévation GMTED2010 de
l'USGS/NGA, les frontières TIGER/Line du bureau du recensement
américain) est dans le domaine public et ne demande aucun crédit. Deux
sources en demandent un :

- Les limites régionales et départementales françaises : © IGN
  (l'institut géographique national français), jeu de données ADMIN
  EXPRESS, via le miroir
  [`gregoiredavid/france-geojson`](https://github.com/gregoiredavid/france-geojson),
  sous licence Ouverte / Etalab 2.0 (la licence française officielle
  d'ouverture des données).
- Les limites administratives de premier niveau de la Suisse, de
  l'Allemagne et de l'Italie (régions, cantons, Länder) : ©
  [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributeurs, sous licence ODbL 1.0 (Open Database Licence).

  Chaque fois que `situation_map` dessine à partir de l'une de ces deux
  sources, il ajoute automatiquement le crédit requis directement sur
  la carte ; voir `_attribution_layer` dans
  `scripts/make_situation_map.py`.

## Licence

BSD-3-Clause.

## Auteur

[Warith Harchaoui, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)
