# sprezzature-maps

[🇬🇧 README.md](README.md) · 🇫🇷 LISEZMOI.md

Cette bibliothèque dessine des cartes en SVG (Scalable Vector Graphics,
un format d'image construit à partir de lignes et de formes décrites en
texte plutôt qu'une grille de pixels, ce qui lui permet de rester nette
à n'importe quel niveau de zoom et de garder son texte sélectionnable).
Chaque trait est écrit à la main, par notre propre code de dessin :
aucune bibliothèque de graphiques ne se cache dessous.
`sprezzature-maps` faisait autrefois partie de
[sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures) ;
il en a été extrait pour devenir un produit à part entière, avec son
propre calendrier de sortie et, à terme, son propre éditeur visuel.

Fait partie de la suite [sprezzature](https://sprezzature.ai/).

---

## Ce qu'on trouve ici

Trois générateurs. Deux s'appuient sur un vrai fond de carte avec
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
| `density` (une carte d'accumulation : *où* les événements sont tombés, plutôt qu'une valeur par territoire) | `scripts/make_density.py` | Aucun trait de côte, aucune frontière, aucun graticule. Les événements ponctuels sont agrégés en un champ lumineux ; la terre apparaît parce que des événements y sont tombés et la mer reste sombre parce qu'aucun n'y est tombé, si bien qu'un lecteur reconnaît la forme sans qu'on la lui montre. Vectoriel, agrégé, un tracé par niveau. |

## Installation

```bash
pip install sprezzature-maps                 # les trois générateurs
pip install 'sprezzature-maps[api,mcp]'      # plus l'API HTTP et le serveur MCP
```

`sprezzature-maps` dépend de `sprezzature-figures` pour les primitives de rendu
que les deux produits partagent (intégrer les polices directement dans le
fichier SVG pour qu'il ait le même rendu sur une machine sans ces polices
installées, et choisir entre un SVG autonome et un SVG qui renvoie vers des
fichiers externes). Il réutilise ce code plutôt que d'en garder sa propre
copie, et pip l'installe pour vous.

Pour travailler sur l'un ou l'autre, installez les deux en mode éditable, côte
à côte, pour que toute modification locale prenne effet sans réinstallation :

```bash
git clone https://github.com/warith-harchaoui/sprezzature-figures ~/sprezzature-figures
pip install -e ~/sprezzature-figures

git clone https://github.com/warith-harchaoui/sprezzature-maps ~/sprezzature-maps
pip install -e ~/sprezzature-maps
```

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

Un mot sur le temps que cela prend, puisque rien à l'écran ne vous le dira :
un choroplèthe demande environ une seconde, une carte de situation plutôt
dix. Profilé, ce temps est du travail réel et non du gaspillage — environ
4 s de calcul d'ombrage du relief à partir de la grille d'élévation, 3 s de
découpe géométrique et 1,5 s de chargement des atlas embarqués, chacun lu
exactement une fois. `basemap: {relief: false}` dans la configuration divise
ce temps par deux si le relief ne vous sert pas.

Voir [`EXAMPLES.md`](EXAMPLES.md) pour davantage de recettes, y compris
l'API HTTP. Voir [`doc/CARTOGRAPHY.tex`](doc/CARTOGRAPHY.tex) pour la
méthode complète derrière chaque projection, chaque échelle de couleur
et chaque technique de relief utilisées dans ce dépôt : les
mathématiques sous-jacentes, les diagrammes TikZ, les citations et les
figures en résolution d'impression, compilé avec `xelatex`/`biber`
(le typographe Unicode de LaTeX et son outil de bibliographie) en
[`doc/CARTOGRAPHY.pdf`](doc/CARTOGRAPHY.pdf).

## Pourquoi un dépôt séparé plutôt qu'un type de graphique dans sprezzature-figures

`choropleth` et `situation_map` vivaient autrefois dans le catalogue de
`sprezzature-figures` (126 types à l'époque ; `density` est né ici, après
la scission). Les en extraire a été une
décision de produit délibérée : Sprezzature Studio, l'éditeur de
graphiques conversationnel livré avec `sprezzature-figures`, ne gagnera
pas le support des cartes. Les cartes auront leur propre Studio séparé,
une fois construit. D'ici là, ce dépôt reste bibliothèque et ligne de
commande uniquement, sans interface d'édition.

## État du projet

Publié sur PyPI ([`sprezzature-maps`](https://pypi.org/project/sprezzature-maps/)),
avec une CI au vert (lint, tests et doctests à chaque push et pull
request vers `main` ; voir `.github/workflows/ci.yml`) : `pytest` passe,
les trois types de carte se rendent depuis leurs données de
démonstration intégrées, et les deux lignes de commande produisent de
vrais fichiers SVG. Encore jeune malgré tout : l'API n'est pas figée, et
il n'y a pas de page de catalogue façon FIGURES.md (avec trois types, ce
LISEZMOI en tient lieu).

Cinq cartes de situation complètes vivent dans
`scripts/build_situation_examples.py`, régénérables par
`python scripts/build_situation_examples.py` : l'Ukraine, la Syrie et la
Libye comme instantanés historiques, le Soudan et l'est de la RDC
d'après des sources ouvertes jusqu'à fin septembre 2026. Chacune est
schématique par construction, le dit sur la planche, et garde ses lignes
de revendication en Python lisible plutôt que dans un fichier de données
opaque : un lecteur en désaccord voit exactement quelles coordonnées
contester.

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
vitesse à laquelle le plancher océanique s'enfonce ; un choix
automatique entre le niveau de détail Natural Earth grossier et fin
selon le degré de zoom de la région demandée ; les lacs intérieurs
dessinés comme de l'eau et non comme de la terre (les données de trait
de côte ne connaissent que la terre et l'océan, si bien qu'avant cela le
lac Kivu, le lac Tchad et les réservoirs du Dniepr étaient tous peints
en terrain sec) — avec `lakes.former` pour l'eau qui a disparu depuis,
car un fond de carte embarqué porte une date de levé qu'une carte datée
peut contredire : l'exemple Ukraine dessine le réservoir de Kakhovka en
contour tireté sans remplissage, celui-ci s'étant vidé après la rupture
du barrage du 6 juin 2023, et `lakes.historic` pour l'autre moitié du
problème, un lac qui existe encore mais ne remplit plus qu'une fraction du
polygone en fichier (le lac Urmia est dessiné ainsi par défaut :
remplissage atténué, bord tireté, nom suffixé « historic extent » —
`lakes.historic: []` restitue les étendues du fond de carte) ; et des
**axes de progression** : des flèches fuselées,
cerclées de blanc, le long d'une courbe lisse, pleines pour un mouvement
évalué et en contour pour un mouvement seulement rapporté — l'élément
qui sépare une carte de l'endroit où la ligne *est* d'une carte de
l'endroit où elle *va* :

```yaml
arrows:
  - line: [[30.45, 13.05], [29.55, 14.05], [29.05, 14.45]]
    color: "#2f5d92"
    label: "SAF advance"
  - line: [[34.02, 10.00], [34.12, 10.95]]
    style: dashed          # rapporté, non évalué
    label: "SPLM-N (reported)"
```

### Dire à quel point on est sûr

Une carte incapable de dire « probablement » dit « certainement » par
défaut. Deux options existent uniquement pour permettre à une planche
d'être moins affirmative que son encre ne le laisserait croire.

**Le degré de certitude de l'évaluation**, sur une zone de contrôle. Le
vocabulaire est celui d'[ISW](https://www.understandingwar.org) : leurs
planches de contrôle du terrain distinguent visuellement trois choses
qu'un aplat unique confond — le terrain qu'une force est évaluée comme
tenant, celui où un mouvement est *rapporté* sans être évalué comme tenu,
et celui qu'un belligérant *revendique* sans que personne ne l'ait
vérifié. C'est cette séparation qui permet de confronter la carte au
communiqué d'un ministère. Toute zone peut porter une propriété
`confidence` :

```yaml
areas_of_control:
  confidence_field: confidence     # la valeur par défaut
  palette: { "Gouvernement": "#9cc3d5", "Opposition": "#d98880" }
  source: zones.geojson            # chaque entité porte : confidence: claimed
```

`assessed` est la valeur par défaut et se dessine en aplat plein, comme
avant. `reported` garde la couleur de la classe, abaissée, sous une
hachure diagonale : toujours visiblement le même acteur, visiblement moins
sûr. `claimed` ne reçoit **aucun aplat** : seulement une trame de points
dans un contour tireté, parce que peindre une revendication de la couleur
du terrain tenu affirme précisément ce que personne n'a vérifié. Une
valeur illisible est refusée plutôt qu'arrondie discrètement vers
`assessed`.

**La précision de la localisation**, sur un marqueur. Les codes sont le
`geo_precision` d'[ACLED](https://acleddata.com), que ce projet consigne à
côté de chaque événement « pour refléter le fait que la localisation
précise de l'incident peut ne pas être connue » — la précision 3
signifiant une capitale provinciale qui tient lieu de province entière.
Dessiner les trois comme le même point plein affirme un coin de rue que la
source n'a jamais donné :

```yaml
events:
  - lon: 38.0008
    lat: 48.5947
    precision: 2             # un lieu nommé qui tient lieu de zone générale
    radius_km: 25            # facultatif : tracé à l'échelle de la carte
    date: "mars 2026"
    time_precision: 3        # l'infobulle lit « month of mars 2026 »
    source: "https://example.org/rapport"   # provenance de ce marqueur-ci
```

La précision 1 est le point plein et garde son sens d'origine. Une
position approximative renonce à son centre plein plutôt que de
s'inventer une surface — un anneau creux, le vieux signe cartographique
du « à peu près ici » — et la précision 3 brise en outre l'anneau. Un
rayon n'est tracé que si vous en énoncez un : le générateur ne devinera
pas une incertitude à partir du type d'événement, parce que les tampons
publiés pour cela mesurent la portée d'un effet, non la mauvaise
connaissance d'une position.

### Quand la carte illustre un article

L'article est le livrable ; la carte lui est subordonnée. Cela change
plusieurs réglages par défaut.

**Elle doit tenir dans la colonne.** Un graphique sur une colonne fait 595
pixels de large à The Economist, Datawrapper publie à 600 par défaut, et une
colonne de téléphone fait environ 375. La carte de légende fait 262 pixels
fixes : acceptable à 1000, elle recouvre la carte à 375. `legend_position`
accepte donc `below` (une bande pleine largeur sous la carte) et `auto`, qui
choisit d'après la largeur de la planche :

```yaml
canvas_width: 375
legend_position: auto     # garde la carte flottante tant qu'elle reste petite
```

**La note est l'essentiel.** La pratique des rédactions est unanime : c'est
l'annotation qui fait la carte de presse, les autres couches sont là pour la
soutenir. `annotations:` prend un point, une phrase, et éventuellement un
rayon en kilomètres au sol :

```yaml
annotations:
  - at: [30.5, 51.3]
    text: "Les colonnes se sont retirées au nord de Kyiv en avril 2022."
    place: left
    color: "#2f5d92"
    circle_km: 90
```

Un cercle plutôt qu'une flèche, parce qu'une pointe de flèche désigne un
pixel et revendique une précision qu'une note sur une région n'a pas. La
note prend la couleur de ce qu'elle décrit, pour se poser sur la carte au
lieu d'en sauter.

**Elle devrait dire où c'est sur Terre.** « Dézoomer pour la perspective,
zoomer pour le détail » est la règle unique de la carte de localisation, et
une planche qui ne fait que zoomer n'en honore que la moitié :

```yaml
inset:
  position: top-right     # ou n'importe quel coin
  zoom: 6                 # l'ampleur du dézoom, faute de bbox
```

**La page autour a besoin de mots et de chiffres.** `article_sidecar(svg)`
les relit dans le fichier fini, pour qu'une légende saisie dans un CMS ne
puisse pas diverger de la planche au-dessus :

```python
from sprezzature_maps import article_sidecar
card = article_sidecar(svg)
card["alt"]      # la description, plus une conclusion calculée
card["zones"]    # [{"category", "confidence", "area_share"}, ...]
card["markers"]  # [{"lon", "lat", "precision", "radius_km"}, ...]
```

Le texte alternatif porte une conclusion, ce que la description accessible
n'avait pas — « Ukrainian government control covers the largest mapped
share, 81% » —, calculée sur ce qui a été dessiné et non affirmée, et
formulée « is claimed to cover » lorsque la plus grande part n'est qu'une
revendication.

**Elle doit être assez légère pour être publiée.** La géométrie est allégée à
la résolution du rendu après projection (`simplify: 0` désactive), et le
raster de relief est écrit en palette indexée exacte plutôt qu'en couleur 32
bits. Ensemble, cela divise à peu près par deux le poids d'une planche —
l'Ukraine passe de 2094 Ko à 1006 Ko — sans changement visible.

Comme les deux autres types, la planche s'ouvre désormais sur une racine
accessible (`role="img"` reliée à un couple `<title>`/`<desc>`), et sa
description nomme les classes dessinées, nomme tout palier de certitude
inférieur à `assessed`, et reprend la réserve que porte la mention de
provenance : la carte dessine l'évaluation qu'on lui a donnée, elle ne la
vérifie pas. Chaque zone et chaque marqueur portent en outre leurs propres
attributs `data-*` (`data-confidence`, `data-precision`,
`data-area-share`), pour que l'évaluation se relise hors du fichier fini
au lieu de seulement se regarder.

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
adaptées à une carte éditoriale (Robinson, Mollweide). Le lecteur
TopoJSON partagé unique (TopoJSON est un format compact qui enregistre
chaque frontière commune une seule fois, au lieu d'une fois par pays
voisin) était le troisième point de cette liste ; c'est désormais
`scripts/_topojson.py`.

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

### Crédités par courtoisie, non par obligation

Rien de ce qui suit n'est embarqué ici et rien n'exige de crédit. Si ces
sources sont nommées, c'est parce que le travail leur a emprunté, et que le
dire ne coûte rien.

La planche de nuit, les rivières fuselées, le champ d'accumulation et le
récit défilant sont des formes reprises de
[mapped.earth](https://mapped.earth) (Aaron J. BECKER), qui les réussit
mieux que ceci. Les jeux de données sur lesquels ces cartes sont bâties, si
vous voulez la chose réelle plutôt que nos démonstrations synthétiques :

- **Foudre** : le Geostationary Lightning Mapper de la NOAA sur les
  Amériques, le Lightning Imager d'EUMETSAT sur l'Europe et l'Afrique, et
  les réseaux nationaux au sol. `make_density.py` livre des points
  synthétiques et le dit sur la planche ; il n'a jamais vu un seul éclair.
- **Débit des fleuves** : [GloFAS v4](https://global-flood.emergency.copernicus.eu/)
  (service Copernicus de gestion des urgences) sur le réseau
  [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers). Notre
  `rivers.width: ranked` dimensionne selon le `scalerank` de Natural Earth,
  un rang de proéminence cartographique, et **non** selon le débit — raison
  pour laquelle cela ne s'appelle pas une largeur hydraulique.
- **Bassins versants** : [HydroSHEDS / BasinATLAS](https://www.hydrosheds.org/hydroatlas),
  CC-BY 4.0.
- **Température de l'eau** : climatologie DynQual 1980-2019.

## Licence

BSD-3-Clause.

## Auteur

[Warith HARCHAOUI, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)
