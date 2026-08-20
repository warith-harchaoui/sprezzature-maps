# Paysage

Les outils qui dessinent une vraie carte géographique se distinguent
par la part du pipeline de rendu qu'ils possèdent vraiment. Un outil
**piloté par une grammaire** (Vega-Lite, D3 avec une bibliothèque de
projections) reçoit une spécification de données et un nom de
projection, et laisse un moteur d'exécution transformer cela en pixels :
c'est ce moteur qui prend chaque décision de dessin. Un outil de **SIG
de bureau** (QGIS) est un logiciel interactif pensé pour qu'un analyste
explore ses données, pas pour qu'un script l'appelle sans supervision.
Un outil **hébergé sans code** (Datawrapper, Flourish) échange le
contrôle contre la rapidité : on choisit un modèle, on charge ses
données, la carte vit sur le serveur de quelqu'un d'autre.
`sprezzature-maps` appartient à une quatrième famille : une petite
bibliothèque Python qui écrit directement le texte XML du SVG, sans
moteur de grammaire de graphiques, sans navigateur, sans compte, si
bien que la géométrie exacte qui finit sur la page est entièrement
décidée par le code de ce dépôt.

## Comparaison des outils

| Outil | Type | Moteur requis | Fond de carte réel (pas schématique) | Auto-hébergeable | Python |
|---|---|---|---|---|---|
| **sprezzature-maps** | SVG écrit à la main | Non | Oui (Equal Earth, LCC) | Oui | Oui |
| Vega-Lite `geoshape` | Grammaire de graphiques | JS (ou `vl-convert` sans tête) | Oui | Oui | Via `altair` |
| D3.js + bibliothèque de projections | Grammaire, plus bas niveau | JS | Oui (toute projection D3) | Oui | Non |
| matplotlib + cartopy/geopandas | Bibliothèque de tracé | Non (Python pur) | Oui | Oui | Oui |
| deck.gl / kepler.gl | Visualisation WebGL | JS, navigateur/WebGL | Oui (par tuiles) | Oui | Via `pydeck` |
| Folium / Leaflet | Carte web interactive | JS, navigateur | Oui (par tuiles) | Oui | Oui (`folium`) |
| Datawrapper / Flourish | Sans code, hébergé | Aucun (SaaS) | Oui | Non | Non |
| QGIS | SIG de bureau | Application de bureau | Oui | Oui | Scriptable (PyQGIS) |

### Notes par dimension

| Dimension | sprezzature-maps | Vega-Lite | matplotlib+cartopy | Folium/deck.gl | Datawrapper |
|---|---|---|---|---|---|
| Rendu sans moteur d'exécution | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | N/A |
| Taille du fichier produit (SVG statique) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ (HTML+JS) | N/A |
| Panoramique/zoom interactif | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Contrôle de la précision de projection | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ (Web Mercator uniquement) | ⭐⭐ |
| Contrôle du design (typographie, palette, légende) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Rapidité pour une première carte | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## Quand utiliser quoi

`sprezzature-maps` convient quand la carte est une figure statique (ou
avec une interactivité légère en CSS/JS) qui doit avoir l'air
délibérément conçue, tenir dans un seul fichier SVG autonome sans
dépendance d'exécution à l'affichage, et rester honnête sur le plan
géographique : Equal Earth conserve, pour la vue mondiale, la
proportionnalité réelle des surfaces des pays (contrairement à la
projection de Mercator sur laquelle reposent par défaut tous les outils
à tuiles ci-dessus, qui gonfle les pays des hautes latitudes), et la
conique conforme de Lambert conserve les formes et les angles locaux
pour une vue régionale. C'est le même arbitrage que font ailleurs dans
cette suite `sprezzature-accessibility` et `sprezzature-ux-laws` :
posséder exactement la sortie plutôt que la confier à un moteur
d'exécution, au prix d'écrire soi-même une plus grande part du code de
dessin.

La marque `geoshape` de Vega-Lite s'impose quand la carte n'est qu'un
type de graphique parmi d'autres qu'un analyste produit déjà dans la
même grammaire, et que l'interactivité côté navigateur (brossage, vues
liées) compte davantage que le contrôle au pixel près du fichier
produit.

matplotlib avec cartopy ou geopandas convient aux tracés géographiques
exploratoires et jetables dans un notebook, ou quand la carte doit
cohabiter avec des graphiques statistiques de la même bibliothèque dans
une seule figure. Ce n'est pas un outil pensé pour produire un SVG
soigné et publiable sans un effort de mise en forme manuel conséquent.

deck.gl, kepler.gl et Folium/Leaflet occupent le créneau de la carte web
interactive que ce dépôt évite délibérément : un vrai panoramique, un
vrai zoom, des fonds de carte par tuiles à toute échelle. On s'y tourne
quand le livrable est une page que l'utilisateur explore, pas une
figure que le lecteur regarde.

Datawrapper et Flourish offrent le chemin le plus rapide d'un tableur à
une carte publiée, quand l'auto-hébergement, le rendu hors ligne et le
contrôle exact du design comptent moins que la rapidité et un flux
d'édition accessible à un non-technicien.

QGIS est un SIG de bureau complet : le bon outil pour analyser
réellement des données géographiques (jointures spatiales, analyse de
zones tampons, conversion de système de coordonnées), pas pour scripter
une figure reproductible. `sprezzature-maps` part du principe que
l'analyse géographique est déjà faite ; il ne fait qu'en dessiner le
résultat.
