# Paysage

La plupart des comparatifs d'outils cartographiques alignent tout sur un
seul axe et classent. Cela masque la seule distinction qui décide vraiment
de quelque chose : **quelle part du dessin l'outil prend-il en charge, et
quelle part vous reste-t-il ?**

- Une **grammaire de graphiques** (Vega-Lite, Altair, Observable Plot) reçoit
  une spécification et un nom de projection ; un moteur d'exécution décide
  ensuite de chaque marque.
- Une **bibliothèque de tracé** (matplotlib avec cartopy ou geopandas)
  dessine dans un canevas de figure conçu pour les graphiques statistiques,
  la cartographie venant par-dessus.
- Une **carte web** (Folium/Leaflet, deck.gl, MapLibre) livre des tuiles et
  une fenêtre, et c'est le lecteur qui déplace et zoome.
- Un **SIG de bureau** (QGIS) est un logiciel qu'un analyste pilote pour
  *analyser* la géographie, et qui sait aussi exporter une carte.
- Un **éditeur hébergé** (Datawrapper, Flourish) échange le contrôle contre
  la rapidité et garde la carte sur le serveur de quelqu'un d'autre.
- Un **écrivain de SVG** produit le XML directement. Aucun moteur, aucun
  canevas, aucune fenêtre : la géométrie sur la page est exactement ce que
  le code a décidé d'écrire.

`sprezzature-maps` appartient à cette dernière famille, et cette famille
n'est pas vide. Dire honnêtement qui d'autre s'y trouve est plus utile que
de revendiquer la catégorie.

## Les écrivains de SVG, précisément

| Outil | Langage | Maintenu ? | Types thématiques | Projection | Planche finie |
|---|---|---|---|---|---|
| **sprezzature-maps** | Python | oui | choroplèthe, carte de situation, densité | Equal Earth / LCC auto-centrée | légende, échelle, relief, mention de provenance |
| [svgis](https://github.com/fitnr/svgis) | Python | oui (0.6.0, sept. 2026) | aucun — géométrie stylée par classe CSS | tout EPSG | non |
| [kartograph.py](https://github.com/kartograph/kartograph.py) | Python | **non** — abandonné, renvoie vers mapshaper | choroplèthe via CSS | plusieurs | non |
| [map-generator](https://github.com/schiste/map-generator) | Rust | oui | aucun | plusieurs | non |
| [map-gen](https://github.com/coxmi/map-gen) | JS | faible | aucun | projections D3 | non |
| py-staticmaps | Python | oui (0.5.0) | marqueurs et lignes | Web Mercator (tuiles) | non |

Lecture utile de ce tableau : **la niche a bel et bien des occupants, et ce
qui les sépare n'est pas « écrire du SVG » — c'est de savoir si l'outil a un
avis sur la page finie.** svgis est le parent vivant le plus proche, et un
bon outil : il convertit des données géographiques en SVG proprement classé
et vous rend un fond de carte à emporter dans Illustrator. Il ne classe pas
vos données, ne choisit pas d'échelle de couleurs, ne place pas de légende,
ne trace pas d'échelle graphique et n'ombre pas le relief, parce que ce
n'est pas son objet. Kartograph, qui visait justement la carte thématique
mise en forme, n'est plus maintenu depuis des années et son propre README
renvoie vers mapshaper.

`sprezzature-maps` vise précisément la part que ces outils vous laissent :
la planche publiable. Des données entrent, une carte composée sort, avec des
décisions cartographiques prises et argumentées dans `doc/CARTOGRAPHY.tex`
plutôt que laissées ouvertes.

## Le champ plus large

| Outil | Type | Moteur à l'affichage | Fond de carte réel | Auto-hébergeable | Python |
|---|---|---|---|---|---|
| **sprezzature-maps** | SVG écrit à la main | aucun | oui (Equal Earth, LCC) | oui | oui |
| svgis | SVG écrit à la main | aucun | oui (tout EPSG) | oui | oui |
| Vega-Lite `geoshape` | Grammaire | JS (ou `vl-convert`) | oui | oui | via `altair` |
| D3 + d3-geo | Grammaire, plus bas niveau | JS | oui | oui | non |
| matplotlib + cartopy/geopandas | Bibliothèque de tracé | aucun | oui | oui | oui |
| PyGMT | Liaisons GMT | binaire GMT | oui | oui | oui (≥3.12) |
| deck.gl / kepler.gl | WebGL | JS + WebGL | oui (tuiles) | oui | via `pydeck` |
| Folium / Leaflet | Carte web interactive | JS, navigateur | oui (tuiles) | oui | oui |
| Datawrapper / Flourish | Sans code, hébergé | aucun (SaaS) | oui | non | non |
| QGIS | SIG de bureau | application | oui | oui | PyQGIS |

### Là où cet outil est fort, et là où il ne l'est pas

| Dimension | sprezzature-maps | svgis | Vega-Lite | matplotlib+cartopy | Folium/deck.gl | Datawrapper |
|---|---|---|---|---|---|---|
| Fichier lisible sans moteur | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | s.o. |
| Publiable sans reprise graphique | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Carte de situation / zones de contrôle | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ |
| Données quelconques, projection quelconque | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Analyse spatiale | ⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| Panoramique / zoom interactif | ⭐ | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Temps jusqu'à la première carte | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

Les lignes à deux étoiles sont les lignes honnêtes. Cette bibliothèque lit
un petit ensemble de géographies embarquées ; ce n'est pas une chaîne de
traitement géospatiale générale, et si vos données sont un shapefile dans
une projection nationale, vous voulez svgis, geopandas ou QGIS. Elle ne fait
aucune analyse spatiale : elle suppose les jointures, les tampons et les
reprojections déjà faits, et ne dessine que le résultat.

## Quand utiliser quoi

**Utilisez `sprezzature-maps`** quand le livrable est une *figure* — quelque
chose qu'on regarde plutôt qu'on explore — qui doit avoir l'air composée,
tenir dans un fichier autonome sans rien à charger à l'affichage, et rester
géographiquement honnête : Equal Earth pour le monde afin que les
superficies restent justes (contrairement au Web Mercator par défaut de tous
les outils à tuiles), Lambert conique conforme auto-centrée sur une région
pour que les formes et les angles locaux le restent.

Le type `situation_map` est le cas le plus net. Zones de contrôle, ligne de
contact, axes de progression fuselés, relief, rivières et lacs, échelle en
deux unités et mention de provenance, depuis un fichier YAML : c'est un
genre qui ne manque pas de *publications* (ISW, Liveuamap, ACLED) et, à
notre connaissance, pas de *générateur* libre. Ces organisations publient
des cartes et des données ; aucune ne livre une bibliothèque qui transforme
votre propre évaluation en planche.

Ne pas livrer de générateur ne veut pas dire n'avoir rien à enseigner, et
ce qu'elles enseignent n'est pas de la géométrie. C'est **comment être
moins affirmatif à dessein** :

- **ISW** distingue visuellement le contrôle évalué, le mouvement rapporté
  et la revendication non vérifiée d'un belligérant, ce qui permet de
  confronter la carte au communiqué d'un ministère. `areas_of_control`
  accepte un `confidence` valant `assessed` / `reported` / `claimed`, et
  une zone revendiquée ne reçoit aucun aplat.
- **ACLED** consigne un `geo_precision` de 1 à 3 à côté de chaque
  événement parce que la localisation précise est souvent inconnue — la
  précision 3 étant une capitale provinciale qui tient lieu de province
  entière. Les marqueurs acceptent le même code, et un marqueur
  approximatif se dessine en anneau creux plutôt qu'en point affirmatif.
- **Liveuamap** attache une source à chaque événement plutôt qu'à la page.
  Un marqueur accepte son propre `source:`.

Le versant dessin a ses deux leçons. Le `-innerlines` de **mapshaper**
existe parce que parcourir des polygones en traçant le contour de chacun
dessine deux fois chaque frontière partagée ; ce dépôt faisait exactement
cela, à 1,63× sur la planche Ukraine, et le décalage des phases de tiret
avait silencieusement transformé la convention de frontière
internationale en trait plein. Son vocabulaire `fill-pattern=` — hachures,
points, carrés, tirets — est le jeu de trames qui dessine les paliers de
certitude. Le `--data-fields` de **svgis** inscrit les champs d'une entité
en attributs `data-*` pour que le dessin reste interrogeable une fois
dessiné ; les zones et les marqueurs portent désormais les leurs, afin que
l'argument d'une planche s'extraie au lieu de seulement se regarder.

**Utilisez svgis** quand vous voulez la géométrie et aucun avis : des
données réelles en entrée, un SVG propre et classé en sortie, la mise en
forme vous revient.

**Utilisez Vega-Lite** quand la carte est un type de marque parmi d'autres
dans une grammaire que vous employez déjà, et que l'interaction dans le
navigateur compte plus que le fichier.

**Utilisez matplotlib avec cartopy ou geopandas** pour des tracés
géographiques exploratoires dans un carnet, ou quand la carte doit voisiner
des graphiques statistiques de la même bibliothèque. Ce n'est pas fait pour
produire un SVG de publication sans un travail de mise en forme important.

**Utilisez PyGMT** quand il vous faut la profondeur des Generic Mapping
Tools — projections géophysiques, grilles, sorties topographiques
professionnelles — et qu'une installation de GMT est acceptable.

**Utilisez deck.gl, kepler.gl ou Folium/Leaflet** quand le livrable est une
page que le lecteur explore : vrai panoramique, vrai zoom, tuiles à toutes
les échelles. Ce dépôt ne concourt pas là et n'essaie pas.

**Utilisez Datawrapper ou Flourish** quand la rapidité et un flux d'édition
non technique l'emportent sur l'auto-hébergement, le rendu hors ligne et le
contrôle exact.

**Utilisez QGIS** pour *analyser* réellement la géographie — jointures
spatiales, tampons, conversions de systèmes de coordonnées.
`sprezzature-maps` suppose ce travail fait ; il ne dessine que la réponse.

## La position de la maison

Posséder la sortie exacte plutôt que la confier à un moteur, et payer cela
en écrivant davantage de code de dessin. C'est le même arbitrage que
`sprezzature-figures`, `sprezzature-accessibility` et `sprezzature-ux-laws`
font ailleurs dans cette suite. Mauvais arbitrage pour l'exploration, bon
arbitrage pour la publication.
