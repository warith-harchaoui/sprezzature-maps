# Paysage

`sprezzature-maps` écrit ses cartes en SVG (Scalable Vector Graphics, un
format d'image fait de lignes et de formes décrites en texte plutôt que d'une
grille de pixels), ligne à ligne, sans bibliothèque de dessin en dessous. Il
fait partie de la suite [sprezzature](https://sprezzature.ai/) et il a été
séparé de `sprezzature-figures` pour que les cartes gardent leur propre
rythme de publication. Il vise une seule chose : la planche finie, une figure
qu'on regarde plutôt qu'une carte qu'on pilote.

## Sa place dans l'écosystème

```
suite sprezzature
├── sprezzature-maps          ← ce paquet (des nombres attachés à de vrais lieux)
├── sprezzature-figures       (167 types de graphiques ; tout ce qui n'est pas géographique)
├── sprezzature-colors        (palettes accessibles, OKLCH)
├── sprezzature-accessibility (contrôle statique du HTML, textes alternatifs)
├── sprezzature-publish       (un dossier de Markdown devient un site trouvable)
├── sprezzature-ui            (les écrans où la figure se pose)
└── best-engine-ai-helper     (choix du modèle local)
```

**Ce qui vient avant.** La géographie, quelqu'un d'autre la fait. GeoPandas,
QGIS ou une base spatiale font les jointures, les tampons et les
reprojections ; l'Armed Conflict Location and Event Data Project (ACLED) ou
l'Uppsala Conflict Data Program (UCDP) fournissent les événements ; Natural
Earth fournit les côtes, embarquées ici plutôt que téléchargées. Ce paquet
suppose ce travail terminé et dessine la réponse.

**Ce qui vient après.** La sortie est un fichier SVG. `sprezzature-publish`
le pose sur une page avec ses balises méta ; `sprezzature-ui` construit
l'écran autour ; `sprezzature-accessibility` contrôle la page où il atterrit.
Rien dans cette chaîne n'a de moteur cartographique à lancer, puisqu'il n'y
en a pas.

**La brique sœur.** `sprezzature-figures` est l'autre moitié du même produit,
et les deux partagent encore des primitives de rendu : l'incorporation des
fontes, la balise racine responsive et accessible, le choix entre un SVG
autonome et un SVG qui pointe vers des fichiers externes. Le découpage est
par sujet, pas par technique. Si les nombres sont attachés à de vrais lieux
et que la forme du terrain compte, c'est ce paquet. Sinon, c'est figures, qui
garde les types de cartes schématiques (`hexbin-map`, `spike-map`,
`dotdensity`, `binned-grid-map`, `hexmap`), lesquels tracent des cellules et
non des côtes.

## Quand choisir sprezzature-maps

- **Une revue veut une figure vectorielle et refusera une image matricielle.**
  La sortie est du vrai SVG, s'exporte en PDF et en EPS en vectoriel, et
  porte sa plus petite taille de caractère comme une propriété vérifiée : la
  planche Ukraine embarquée fait 1768 unités de large et sa plus petite
  étiquette en mesure 10,8, ce qui, dans une colonne de 90 mm, donne 1,6 pt,
  le tiers du plancher accepté par n'importe quel grand éditeur. Le paquet le
  signale au lieu de laisser passer, parce qu'un fichier vectoriel, lui, se
  rend toujours.
- **La classification doit être défendable.** Quantiles, intervalles égaux,
  seuils naturels (FISHER et JENKS) et seuils tête-queue (JIANG, 2013) sont
  tous disponibles, aucun n'est choisi en silence, la légende nomme celui qui
  a servi, et une règle statique relit le SVG fini et signale une légende
  classée qui ne dit pas comment ses seuils ont été choisis.
- **Vous cartographiez des événements dont la position est approximative.**
  ACLED et UCDP livrent tous deux un code de précision à côté de chaque
  coordonnée. Ici ce code devient de la cartographie : un disque cerné pour
  un lieu connu, un anneau creux pour une position approchée, un anneau
  brisé pour une région réduite à sa capitale, et les lignes UCDP qui ne
  connaissent que le pays sont écartées et comptées dans la ligne de méthode
  de la planche.
- **Le fichier doit encore marcher dans cinq ans, hors ligne.** Un SVG, les
  fontes incorporées, pas de serveur de tuiles, pas de clé d'API, pas de
  compte, pas de moteur. Le fichier annexe qui consigne ce qui l'a dessiné ne
  porte aucune horloge : deux rendus des mêmes entrées restent identiques.

## Quand prendre autre chose

- **[QGIS](https://qgis.org/) ou [ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview)**
  quand il s'agit d'analyser la géographie plutôt que d'en tirer une
  conclusion. Leurs rendus gradués battent aussi ce paquet sur un point qui
  lui tient à cœur : ils affichent l'histogramme des données avec les lignes
  de seuil dessinées dessus, de sorte que la classification se choisit à
  l'œil contre la distribution. Ce paquet vous fait choisir sans cette image.
- **[svgis](https://github.com/fitnr/svgis)** quand vous voulez la géométrie
  et aucun avis. Il prend de vraies données géographiques dans n'importe quel
  code EPSG et écrit un SVG propre, classé par CSS, exactement le fond de
  carte à finir dans Illustrator. C'est le parent vivant le plus proche, et
  il gagne nettement sur les systèmes de coordonnées quelconques.
- **[deck.gl](https://deck.gl/) ou [kepler.gl](https://kepler.gl/)** quand les
  données sont grosses ou que le livrable bouge. Des millions de lignes, des
  arcs d'origine à destination, des trajets animés, un regroupement par
  niveau de zoom. Ce paquet dessine une planche fixe et ne prétend pas autre
  chose.
- **[MapLibre GL JS](https://maplibre.org/) avec
  [Protomaps](https://protomaps.com/)** quand le lecteur doit se déplacer et
  zoomer sur un vrai fond de carte, auto-hébergé, sans compte chez personne.
  Cette pile est la réponse par défaut en 2026 pour ce travail précis, et le
  fichier unique PMTiles est une meilleure réponse à l'hébergement des tuiles
  que tout ce qui se trouve ici.
- **[Datawrapper](https://www.datawrapper.de/) ou
  [Flourish](https://flourish.studio/)** quand c'est un journaliste qui
  n'écrit pas de code qui doit faire la carte à seize heures. Datawrapper
  livre aussi plus d'accessibilité que ce paquet, au niveau de la page
  publiée plutôt qu'à celui du fichier.
- **[mapsf](https://cran.r-project.org/package=mapsf) ou
  [tmap](https://cran.r-project.org/package=tmap)** si l'analyse est déjà en
  R. `mapsf` est ce qui, dans n'importe quel langage, se rapproche le plus du
  but de ce paquet : de la cartographie thématique où l'habillage (échelle
  graphique, flèche du nord, titre, crédits) fait partie de la carte au lieu
  d'être un ornement.

## Les idées à prendre

Étudier un concurrent sans rien en rapporter, c'est de la lecture perdue.
Sept choses que le champ fait mieux, classées par ce qu'elles rapportent
rapporté à ce qu'elles coûtent. Deux sont des refus, avec leur raison, ce qui
est aussi un résultat.

**[tmap](https://cran.r-project.org/package=tmap) et `classInt` : le style
`pretty`.** tmap nomme ses styles de classification dans l'argument lui-même
(`quantile`, `jenks`, `pretty`, `sd`, `fisher`, `headtails`), et celui qui
manque ici est `pretty` : des seuils sur des nombres ronds, choisis pour que
la légende se lise 0, 20, 40, 60 plutôt que 17,4, 38,9, 61,2. Ici cela fait
une entrée de plus dans `METHODS` et une étiquette de plus dans
`METHOD_LABELS`, les deux dans `scripts/_classify.py`, plus un
`pretty_breaks()` d'une trentaine de lignes de bibliothèque standard et une
ligne de paramètre de plus dans
`tests/test_classify.py::test_every_method_is_named_for_a_reader`. Coût : une
après-midi, aucune dépendance. Le meilleur rapport de la liste, parce que le
dépôt a déjà construit tout ce qui rend une nouvelle méthode sûre.

**[mapclassify](https://pysal.org/mapclassify/) : publier la qualité de
l'ajustement.** Les classificateurs de PySAL exposent à quel point une
partition colle aux données, la qualité de l'ajustement de variance, si bien
qu'on peut dire que les seuils naturels ont séparé ce jeu de données et que
les quantiles ne l'ont pas fait. Ce paquet nomme la méthode et ne dit rien de
savoir si elle a marché. `scripts/_classify.py` gagnerait un
`fit_quality(values, breaks) -> float`, la ligne de méthode de la planche
deviendrait `seuils naturels (k = 5, ajustement 0,91)`, et
`sprezzature_maps/audit.py` gagnerait une règle signalant une méthode choisie
dont l'ajustement est très inférieur au meilleur disponible sur les mêmes
données. Coût : cinquante lignes et une règle d'audit, aucune dépendance,
puisque le solveur de seuils naturels calcule déjà la variance intra-classe.

**[QGIS](https://qgis.org/) et
[ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview) :
l'histogramme sous les seuils.** Les deux montrent la distribution des
données avec les limites de classe tracées dessus, dans la boîte de dialogue
même où la classification se choisit. Le code de légende de
`scripts/make_choropleth.py` imprime déjà un cartouche par classe et les
valeurs limites entre elles ; un `legend_histogram: true` ajouterait une fine
bande de fréquences sous les cartouches, les seuils en graduations, de sorte
qu'un lecteur voie que quatre des cinq classes contiennent trois pays
chacune. Coût : une demi-journée de dessin, et un risque de mise en page dont
le dépôt possède déjà la constante : `_LEGEND_MAX_WIDTH_FRACTION = 0.38` dans
`scripts/make_situation_map.py` existe parce qu'un cartouche de légende
au-delà de 38 % de la largeur de la carte cesse d'être du mobilier et devient
une occultation.

**[Datawrapper](https://www.datawrapper.de/) : une description qui ne soit
pas le titre une seconde fois.** Les graphiques de Datawrapper livrent une
alternative décrite plutôt qu'un titre répété. Ici chaque planche s'ouvre
avec `role="img"` et `aria-labelledby` pointant vers un couple `<title>` et
`<desc>` (`scripts/_svg.py`), et `sprezzature_maps/audit.py` signale déjà une
planche sans nom accessible du tout. Ce qu'il n'attrape pas, c'est l'échec
bien plus courant : un `<desc>` qui répète le `<title>` mot pour mot, qui
passe tous les contrôles automatiques et ne dit rien à un lecteur d'écran.
Une règle, `desc-repeats-title`, plus une modification du générateur qui
écrive dans `<desc>` les extrêmes et le nombre de classes, à partir de
données que le générateur tient déjà. C'est le cas de l'idée à moitié faite,
et ce sont en général les meilleures affaires. Coût : une journée.

**[svgis](https://github.com/fitnr/svgis) : `--data-fields`, déjà pris, et à
finir.** svgis inscrit les champs propres d'une entité en attributs `data-*`
pour que le dessin reste interrogeable une fois dessiné. Les zones de
contrôle et les marqueurs portent les leurs ici. Les régions du choroplèthe,
non, et c'est pourtant la couche où cela compterait le plus : `data-value`,
`data-class` et `data-method` sur chaque tracé de pays permettraient à une
page d'extraire la table hors de l'image, et permettraient à
`sprezzature_maps/audit.py` de vérifier les couleurs dessinées contre les
seuils annoncés au lieu de croire le texte de la légende. Coût : une
après-midi dans `scripts/make_choropleth.py`, et cela referme une boucle que
l'audit ne peut pas fermer aujourd'hui.

**[FlowmapBlue](https://www.flowmap.blue/) et
[flowmap.gl](https://github.com/visgl/flowmap.gl), d'Ilya BOYANDIN : les
rubans d'origine à destination.** Des bandes fuselées entre lieux, la largeur
sur une échelle en racine carrée pour que l'œil lise une aire et non une
longueur, avec un regroupement des lieux quand le lecteur dézoome. La moitié
des pièces est déjà là : `scripts/_svg.py` a des tracés de ruban en courbes
de Bézier cubiques, employés pour les axes de progression de la planche de
situation, et `scripts/_conflict.py` dimensionne déjà ses marques en aire
vraie, sur une racine carrée, pour la même raison perceptive. Un quatrième
type, `make-map flow`, lisant un CSV à deux colonnes origine et destination,
est une vraie possibilité. **Non prise pour l'instant**, et la raison est la
maintenance et non la difficulté : un quatrième générateur, c'est un
quatrième jeu de légendes, de collisions d'étiquettes, d'échelles graphiques
et de règles d'audit, et les trois qui existent sont les trois que ce paquet
sait défendre. La phrase honnête est que la géométrie du ruban existe et que
le type de planche, non.

**[Protomaps](https://protomaps.com/) et PMTiles, de Brandon LIU : tout le
fond de carte en un seul fichier indexé.** PMTiles range une pyramide de
tuiles entière dans un fichier unique et la sert par requêtes HTTP Range,
c'est ainsi qu'un fond de carte mondial se livre sans aucun serveur de
tuiles. Ici, `assets/geo/` pèse 329 Mo répartis sur 26 fichiers vectoriels et
six paliers d'altitude. **Refusé**, et la raison tient à la direction de la
suite plutôt qu'au format : une requête Range est un serveur, et la propriété
que ce paquet vend est qu'une planche se rende depuis un clone, réseau
coupé. Ce qui vaut d'être pris, c'est la moitié plus modeste de la même idée,
le manifeste : `assets/geo/` a un `__init__.py` d'une ligne et aucun index,
donc rien dans le dépôt n'indique, fichier par fichier, d'où il vient, sous
quelle licence, et combien d'octets il coûte. Ce fichier rendrait la mention
de provenance calculable au lieu d'écrite. Coût : une après-midi, et ce
serait l'honnêteté la moins chère du dépôt.

## Comment le domaine se découpe

La plupart des comparatifs d'outils cartographiques alignent tout sur un seul
axe et classent. Cela masque la distinction qui décide vraiment de quelque
chose : **quelle part du dessin l'outil prend-il en charge, et quelle part
vous reste-t-il ?**

- Une **grammaire de graphiques** (Vega-Lite, Altair, Observable Plot) reçoit
  une spécification et un nom de projection ; un moteur d'exécution décide
  ensuite de chaque marque.
- Une **bibliothèque de tracé** (matplotlib avec Cartopy, GeoPandas, PyGMT)
  dessine dans un canevas de figure conçu pour les graphiques statistiques,
  la cartographie venant par-dessus.
- Un **paquet de cartographie thématique** (tmap, mapsf) traite la légende,
  l'échelle graphique et les crédits comme des parties de la carte. Cette
  famille est forte et vit presque entièrement en R.
- Une **carte web** (Leaflet, MapLibre GL JS, OpenLayers, Mapbox GL JS) livre
  des tuiles et une fenêtre, et c'est le lecteur qui se déplace et zoome.
- Une **couche de visualisation sur GPU** (deck.gl, kepler.gl, pydeck)
  compose des millions de lignes par-dessus une de ces fenêtres.
- Une **fourniture de tuiles** (Protomaps et PMTiles, Tippecanoe, Overture,
  Natural Earth, TopoJSON) n'est pas un outil de dessin : c'est ce que les
  outils de dessin lisent.
- Un **système d'information géographique de bureau** (QGIS, ArcGIS Pro) est
  un logiciel qu'un analyste pilote pour analyser la géographie, et qui sait
  aussi exporter une carte.
- Un **éditeur hébergé** (Datawrapper, Flourish, Felt, CARTO) échange le
  contrôle contre la rapidité et garde la carte sur le serveur de quelqu'un
  d'autre.
- Un **écrivain de SVG** produit le XML directement. Aucun moteur, aucun
  canevas, aucune fenêtre : la géométrie sur la page est exactement ce que le
  code a décidé d'écrire.

La deuxième division qui compte est **le moment où l'outil tourne**. Un
écrivain statique tourne une fois, à l'écriture, et le fichier est le
livrable. Une carte web tourne sur la machine de chaque lecteur, à chaque
fois, et le livrable est une page plus une fourniture de tuiles qui doit
rester debout. Le basculement de 2026 dans cette seconde famille vaut d'être
connu même si l'on n'y va jamais : Mapbox GL JS a cessé d'être libre en 2020,
MapLibre est devenu la bifurcation que tout le monde emploie, et PMTiles a
supprimé le serveur de tuiles entièrement, si bien que la pile auto-hébergée
est aujourd'hui MapLibre plus un seul fichier Protomaps.

La troisième division est **qui a le droit de conduire**. Datawrapper,
Flourish, Felt et CARTO existent parce qu'un journaliste pressé n'écrira pas
de Python, et ils sont réellement meilleurs à cela qu'aucune bibliothèque ne
le sera jamais. Toutes les bibliothèques de cette page, celle-ci comprise,
sont plus mauvaises sur cet axe par construction.

`sprezzature-maps` appartient à la famille des écrivains de SVG, et cette
famille n'est pas vide. Dire honnêtement qui d'autre s'y trouve est plus
utile que de revendiquer la catégorie.

### Les écrivains de SVG, précisément

| Outil | Langage | Maintenu ? | Types thématiques | Projection | Planche finie |
|---|---|---|---|---|---|
| **sprezzature-maps** | Python | oui | choroplèthe, carte de situation, densité | Equal Earth / LCC auto-centrée | légende, échelle, relief, mention de provenance |
| [svgis](https://github.com/fitnr/svgis) | Python | oui (0.6.0, septembre 2026) | aucun, géométrie stylée par classe CSS | tout EPSG | non |
| [kartograph.py](https://github.com/kartograph/kartograph.py) | Python | **non**, abandonné, renvoie vers mapshaper | choroplèthe via CSS | plusieurs | non |
| [map-generator](https://github.com/schiste/map-generator) | Rust | oui | aucun | plusieurs | non |
| [map-gen](https://github.com/coxmi/map-gen) | JS | faible | aucun | projections D3 | non |
| py-staticmaps | Python | oui (0.5.0) | marqueurs et lignes | Web Mercator (tuiles) | non |

Lecture utile de ce tableau : la niche a bel et bien des occupants, et ce qui
les sépare n'est pas « écrire du SVG », c'est de savoir si l'outil a un avis
sur la page finie. svgis est le parent vivant le plus proche, et un bon
outil. Il ne classe pas vos données, ne choisit pas d'échelle de couleurs, ne
place pas de légende, ne trace pas d'échelle graphique et n'ombre pas le
relief, parce que ce n'est pas son objet. Kartograph, qui visait justement la
carte thématique mise en forme, n'est plus maintenu depuis des années et son
propre README renvoie vers mapshaper.

## Comment il se compare

Vingt-cinq outils notés de 1 à 5 sur quatorze critères, et plus haut vaut
toujours mieux (⭐ faible à ⭐⭐⭐⭐⭐ le plus fort). Une étoile est un jugement
argumenté, pas un banc d'essai : rien ici n'a été chronométré, et quand un
outil ne fait pas du tout ce que le critère mesure, il reçoit une étoile,
parce que sur une échelle de capacité « ne le fait pas » vaut 1. Chaque
critère est orienté pour que plus d'étoiles veuille dire mieux, d'où
l'absence de colonne de prix et de colonne de poids : il y a une colonne
d'ouverture et une colonne de légèreté à la place. La source lisible par une
machine est [`assets/paysage.csv`](assets/paysage.csv).

| Outil cartographique | Qualité de publication sans reprise | Fichier lisible sans moteur | Texte sélectionnable dans la sortie | Étendue des projections | Classification des valeurs nommée | Cartes de flux et de liens | Interactivité, zoom et tuiles | Grands jeux de données | Libre et sans compte | Installation légère | Reproductibilité | Accessibilité intégrée | Maturité et écosystème | À portée de qui ne programme pas |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| sprezzature-maps | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ |
| svgis | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ |
| D3 + d3-geo | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| Observable Plot | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Vega-Lite / Altair | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| matplotlib + Cartopy | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| GeoPandas | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| PyGMT | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| Folium / Leaflet | ⭐⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| MapLibre GL JS | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| Mapbox GL JS | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| OpenLayers | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| deck.gl | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ |
| kepler.gl | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Plotly maps | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Highmaps | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Datawrapper | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Flourish | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Felt | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| CARTO | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| QGIS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| ArcGIS Pro | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| tmap (R) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ |
| mapsf (R) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ |
| Protomaps / PMTiles | ⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |

Les lignes à une étoile sont les premières à lire. **Maturité et écosystème**
est à une étoile et doit l'être : ce paquet a été publié en 2026, il a un
auteur, et en face se tiennent D3, Leaflet, QGIS et matplotlib, chacun avec
vingt ans et des dizaines de milliers de dépendants. **Grands jeux de
données** est à une étoile : les générateurs parcourent de la géométrie en
Python et écrivent du XML, et un million de points n'est pas la forme de
problème pour laquelle ils existent, là où deck.gl et CARTO l'avalent.
**Interactivité, zoom et tuiles** est à deux étoiles, et c'est généreux : il
y a un bouton plein écran et des infobulles, il n'y a ni déplacement, ni
zoom, ni tuile à aucune échelle. **À portée de qui ne programme pas** est à
deux étoiles : il existe une page de galerie derrière la surface HTTP, et
tout le reste passe par Python, une ligne de commande ou un fichier YAML.
**Étendue des projections** est à deux étoiles contre cinq pour svgis,
OpenLayers, Cartopy et QGIS : deux projections choisies exprès restent deux
projections, et si vos données appartiennent à une grille nationale, ce
n'est pas le bon outil.

### La même table, dessinée

![Vingt-cinq outils cartographiques positionnés sur deux axes issus de la table ci-dessus. sprezzature-maps occupe seul le coin en haut à droite ; mapsf, tmap, PyGMT, svgis et matplotlib avec Cartopy s'alignent en haut de la figure, à sa gauche ; deck.gl lui est diamétralement opposé en bas à gauche, avec kepler.gl, Mapbox GL JS, Felt et CARTO le long du bas ; Datawrapper est à droite, au niveau de l'axe horizontal. L'axe horizontal va d'Autonomie à gauche à Clarté à droite, le vertical de Dynamisme en bas à Rigueur en haut.](assets/paysage.svg)

Cette page s'ouvre en refusant de classer ces outils sur un seul axe. Une
carte est l'autre moitié de ce refus : elle en utilise deux, et elle dit ce
qu'elle laisse de côté.

La source est [`assets/paysage.csv`](assets/paysage.csv), c'est-à-dire la
table en étoiles ci-dessus et rien d'autre, transposée. Régénérer avec :

```sh
python scripts/landscape_to_csv.py ~/sprezzature-maps/PAYSAGE.md \
  --out ~/sprezzature-maps/assets/paysage.csv
standpoint ~/sprezzature-maps/assets/paysage.csv \
  --outdir ~/sprezzature-maps/assets --stem paysage --check
python scripts/date_the_map.py ~/sprezzature-maps/assets/paysage*.svg \
  --asof "octobre 2026" --prefix "Notes à jour en" --source PAYSAGE.md
```

Cette troisième ligne n'est pas décorative. Une figure sans millésime
déclenche la règle `no-provenance` de ce paquet même, qui existe parce qu'une
carte sans date se lit comme actuelle à jamais. La règle s'est déclenchée sur
cette figure la première fois qu'elle a été ajoutée, ce qui est la bonne façon
pour elle d'arriver.

`sprezzature-maps` est la première ligne, et `standpoint` place la première
ligne en haut à droite et oriente tout le reste autour d'elle. C'est une
convention de dessin, pas une prétention de qualité.

La géométrie est une analyse en composantes principales (ACP) sur
corrélations, et elle est **déterministe** : la même table donne la même
carte à chaque exécution. Les quatre mots des bords viennent d'un modèle
local, et ils sont plus vagues que ce qui les porte ; les charges sont donc
le contrôle. Les voici.

**Horizontal.** Accessibilité intégrée (+0,50), qualité de publication sans
reprise (+0,38), à portée de qui ne programme pas (+0,37) et classification
des valeurs nommée (+0,33) tirent d'un côté ; libre et sans compte (−0,29),
grands jeux de données (−0,28) et maturité et écosystème (−0,21) tirent de
l'autre. Le modèle a nommé les deux bouts Autonomie et Clarté. Ce que les
chiffres opposent est plus étroit et plus intéressant que cela : une carte
faite pour être lue contre un système fait pour porter de la charge.
`sprezzature-maps` est tout à droite par construction, puisque c'est la ligne
de référence, et Datawrapper tombe exactement sur la même coordonnée
horizontale, 3,25. C'est la carte en train de reconnaître qu'un outil de
rédaction et ce paquet visent la même chose.

**Vertical.** Fichier lisible sans moteur (+0,38), reproductibilité (+0,38),
texte sélectionnable dans la sortie (+0,35), étendue des projections (+0,30)
et libre et sans compte (+0,26) en haut ; interactivité, zoom et tuiles
(−0,41), grands jeux de données (−0,24), à portée de qui ne programme pas
(−0,23) et installation légère (−0,22) en bas. Le modèle les a nommés
Rigueur et Dynamisme. C'est le fichier contre le service : un objet qu'on
garde contre une chose qu'on pilote, le confort étant du côté de la chose
qu'on pilote. `mapsf` partage exactement la coordonnée du haut, 3,64 ;
`svgis`, PyGMT et matplotlib avec Cartopy se tiennent juste en dessous ;
deck.gl est diamétralement opposé à ce paquet et CARTO est au plancher.
Datawrapper est le seul outil haut sur l'horizontale et bas sur la verticale,
ce qui est exactement ce qu'il échange.

**Deux axes portent 56 %** de la table : 36,0 % sur l'horizontale, 20,2 % sur
la verticale. Les 44 % qui restent sont dans la table et pas sur l'image.
Deux colonnes en particulier ne sont portées par aucun des deux axes : cartes
de flux et de liens (−0,10 et −0,18) et maturité et écosystème (−0,21 et
−0,16). Si vous veniez pour l'une des deux, la carte ne vous répondra pas et
la table, oui.

Les quatre mots des pôles viennent d'un modèle local, et il a nommé chaque
langue séparément : l'anglais dit Robustness, Usability, Dynamism et Clarity,
le français dit Autonomie, Clarté, Dynamisme et Rigueur. La géométrie, elle,
est identique dans les deux, et ce sont les charges ci-dessus qui en
répondent.

`standpoint --check` signale une mise en page qui n'est pas entièrement
lisible : deux paires d'étiquettes de points risquent de se chevaucher,
Vega-Lite / Altair avec QGIS, et MapLibre GL JS avec Protomaps / PMTiles. Les
deux paires sont proches parce que leurs notes le sont réellement, ce qui est
une figure à l'étroit plutôt qu'une figure fausse.

`standpoint` écrit aussi une interprétation en prose à côté de la figure.
Elle n'est pas reprise ici, parce qu'un modèle qui relit des notes écrites
par quelqu'un n'est pas un résultat, et que ce fichier est plus utile si les
jugements restent visiblement les miens.

## Le champ de la recherche sur les conflits, précisément

La table ci-dessus compare des outils de dessin. Un chercheur sur les
conflits ne commence pas par choisir un outil de dessin : il commence par un
jeu de données, et ce jeu de données est presque toujours l'un des deux.

| Jeu de données | Unité | Où il dit que c'est | Quand il dit que c'est | Mis à jour |
|---|---|---|---|---|
| [ACLED](https://acleddata.com/methodology/acled-codebook) | un événement de violence politique ou de protestation | `latitude`/`longitude` plus `geo_precision` de 1 à 3 | `event_date` plus `time_precision` de 1 à 3 | chaque semaine |
| [UCDP GED](https://ucdp.uu.se/downloads/) | un événement de violence organisée avec au moins un mort | `latitude`/`longitude` plus `where_prec` **de 1 à 7** | `date_start`/`date_end` plus `date_prec` de 1 à 5 | chaque année |

Les deux livrent un code de précision à côté de chaque coordonnée, et les
deux veulent dire quelque chose de précis par là. Le 3 d'ACLED est une
capitale provinciale qui tient lieu de province entière. Le 6 d'UCDP veut
dire que seul le pays est connu, et les coordonnées sont un point
représentatif d'un État entier. **Tous les outils de ce champ les dessinent
comme le même point.** `acled` et `acled.api` récupèrent les lignes ;
`acledR` et `conflictr` les remettent en forme ; GeoPandas, Cartopy et QGIS
poseront une couche de points sur un fond de carte ; Datawrapper la rendra
jolie. Aucun ne dessine un `geo_precision` 3 autrement qu'un 1, ce qui veut
dire que chacune de ces cartes affirme un coin de rue que sa source n'a
jamais donné, plusieurs centaines de fois par figure, sans le dire.

C'est l'ouverture de ce projet, et la couche de marqueurs la prend : un
disque cerné pour un lieu nommé, un anneau creux pour une position
approchée, un anneau brisé pour une région réduite à sa capitale, un rayon
dessiné quand le jeu de données en énonce un, avec les mots repris du
codebook d'ACLED lui-même. `scripts/_conflict.py` est les vingt lignes entre
le fichier du chercheur et ce marqueur :

```python
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
```

Ce que la suite laisse encore à d'autres, dit aussi platement que le reste :

| Besoin | Ici | Mieux servi par |
|---|---|---|
| Récupérer les données | non | `acled` (PyPI), `acled.api` et `acledR` (CRAN), l'API d'UCDP |
| Filtrer, agréger, joindre à des unités administratives | non | GeoPandas, QGIS |
| Des frontières historiques pour une carte d'avant 2019 | oui, `frontiers.source` plus `frontiers.as_of`, rien n'est embarqué | vous fournissez [CShapes 2.0](https://doi.org/10.1177/00220027211013563), qui est en CC BY-NC-SA et ne peut pas tenir dans un paquet BSD |
| Une grille de cellules égales pour un modèle statistique | non | [PRIO-GRID](https://doi.org/10.1177/0022343311431287) 0,5° |
| Des polygones infranationaux au-delà des paliers embarqués | en partie (admin-1, admin-2) | geoBoundaries CGAZ, GADM |
| Les symboles d'unité NATO APP-6D | non | `milsymbol` (JS), `mil-sym-java` ; il n'existe aucun rendu en Python |
| Dessiner le résultat en planche finie et citable | **oui** | |

La dernière ligne est la revendication. Celle du dessus est le trou le plus
intéressant du champ : les normes interalliées de symbologie militaire ont
des implémentations libres en JavaScript, en Java, sur Android et en Rust, et
aucune en Python.

## La position de la maison

Posséder la sortie exacte plutôt que la confier à un moteur, et payer cela en
écrivant davantage de code de dessin. C'est le même arbitrage que
`sprezzature-figures`, `sprezzature-accessibility` et `sprezzature-ux-laws`
font ailleurs dans cette suite. Mauvais arbitrage pour l'exploration, bon
arbitrage pour la publication.

## Sources

Notes à jour en octobre 2026, d'après la documentation des projets et
d'après les pages suivantes, lues en octobre 2026 :

- [La pile géospatiale en 2026 : PostGIS, MapLibre, Mapbox, deck.gl, kepler.gl, Protomaps, Overture, H3, S2](https://ttlab.hopto.org/blog/culture/2026-05-16-geospatial-stack-2026-postgis-maplibre-mapbox-deckgl-kepler-protomaps-overture-h3-deep-dive?lang=en)
- [Protomaps, la carte libre dans un fichier](https://protomaps.com/)
- [deck.gl face à MapLibre](https://atlas.co/comparisons/deck-gl-vs-maplibre/)
- [Les meilleurs outils de visualisation géospatiale en 2026](https://atlas.co/blog/best-geospatial-data-visualization-tools-in-2026/)
- [La projection Equal Earth, ŠAVRIČ, PATTERSON et JENNY, 2018](https://en.wikipedia.org/wiki/Equal_Earth_projection)
- [Equal Earth dans PROJ 9.8](https://proj.org/en/9.8/operations/projections/eqearth.html)
- [Choroplèthes, guide de la classification des données](https://gisgeography.com/choropleth-maps-data-classification/)
- [tmap 4.4 sur le CRAN](https://cran.r-project.org/package=tmap) et [mapsf 1.3 sur le CRAN](https://cran.r-project.org/package=mapsf)
- [kepler.gl sous la gouvernance de la fondation OpenJS](https://opensource.foursquare.com/kepler-gl/)
- [FlowmapBlue](https://www.flowmap.blue/)
- [Les exigences d'accessibilité ADA pour les cartes publiques, échéance d'avril 2026](https://dymaptic.com/blog/the-clock-is-ticking)
- [GeoLinter, un cadre de contrôle pour les choroplèthes](https://arxiv.org/pdf/2310.13707)
