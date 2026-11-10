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

## Comment ça marche

![Schéma de flux. En haut, une valeur par territoire, des événements ponctuels ou une configuration de planche alimentent deux voies. La voie de gauche dessine : elle centre et projette sur un vrai fond de carte, classe les valeurs et nomme la méthode employée, et trace l'une des trois planches, puis rend un SVG, avec une échelle en deux unités sur une planche régionale. La voie de droite contrôle : onze règles statiques relisent la planche rendue et demandent si elle nomme sa classification, imprime ses seuils, dit quand elle était vraie et se lit mot à mot. Les deux se rejoignent en un seul résultat, une planche avec laquelle un lecteur peut discuter.](https://raw.githubusercontent.com/warith-harchaoui/sprezzature-maps/main/assets/comment-ca-marche.svg)

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
| `choropleth` (une carte où chaque région est remplie d'une couleur qui code un nombre, la carte classique du « quel pays a le score le plus élevé ») | `scripts/make_choropleth.py` | Une carte du monde, une couleur de remplissage par pays sur une échelle allant du pâle au bleu marine, ou sur une échelle divergente quand les valeurs changent de signe ; les pays sans donnée retombent sur un gris neutre. |
| `situation_map` | `scripts/make_situation_map.py` | Une planche en couches « qui contrôle quoi » pour n'importe quelle région : la carte se recentre automatiquement sur cette région via une projection conique conforme de Lambert (voir plus bas), trace de vrais contours nationaux depuis un fond de carte Natural Earth intégré, ombre le plancher océanique près des côtes, remplit les zones par catégorie en couleurs pastel, marque les points chauds, et ajoute une échelle en deux unités à la fois (kilomètres et miles). |
| `density` (une carte d'accumulation : *où* les événements sont tombés, plutôt qu'une valeur par territoire) | `scripts/make_density.py` | Aucun trait de côte, aucune frontière, aucun graticule. Les événements ponctuels sont agrégés en un champ lumineux ; la terre apparaît parce que des événements y sont tombés et la mer reste sombre parce qu'aucun n'y est tombé, si bien qu'un lecteur reconnaît la forme sans qu'on la lui montre. Vectoriel, agrégé, un tracé par niveau. |

## Installation

```bash
pip install sprezzature-maps
```

Une seule ligne, et elle installe tout : les trois générateurs, la
bibliothèque, la ligne de commande, l'API HTTP, le serveur MCP et l'éditeur.
Il n'y a pas d'extra de fonctionnalité. `[dev]` porte l'outillage de test
(pytest, ruff, mypy et le reste) et n'ajoute aucune fonctionnalité. Python 3.10
à 3.13.

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
from sprezzature_maps import make_choropleth, make_density, make_situation_map

make_choropleth(out="world.svg")          # données de démonstration si rien n'est fourni
make_situation_map(out="region.svg")      # configuration de démonstration intégrée
make_density(out="where.svg")             # points de démonstration synthétiques
```

```bash
make-map choropleth --out world.svg
make-map situation_map --config my-region.yaml --out region.svg
make-map density --points events.json --out where.svg
```

Commencer une planche régionale tient en une commande, et ce qu'elle écrit
porte déjà le mobilier qu'une planche doit à son lecteur :

```bash
make-map situation-new --country Moldova --out moldova.yaml
make-map situation_map --config moldova.yaml --out moldova.svg
make-map audit moldova.svg          # propre, telle quelle
```

Le format de sortie suit l'extension de `--out` : `.svg`, `.png`, `.jpg`,
`.pdf`, `.eps`, ou `.html` (le SVG dans une page minimale). Sans `--out` (ou
`out=` en Python), `choropleth`, `density` et `situation-map` écrivent
`choropleth.svg`, `density.svg` ou `situation_map.svg` dans le répertoire
courant ; ils n'écrasent jamais les exemples du paquet.
`make-map -V` (ou `--version`) affiche la version installée.

## Cinq façons d'y accéder

Un seul moteur, joint de cinq façons. Les cinq s'installent avec le paquet, et
chacune appelle les mêmes fonctions de la bibliothèque.

### 1. La bibliothèque Python

`import sprezzature_maps` exporte :

| Nom | Ce qu'il fait |
|---|---|
| `make_choropleth`, `make_situation_map`, `make_density` | Rendent une planche et renvoient le chemin écrit |
| `classification_methods()` | Les méthodes de seuils qu'accepte un choroplèthe : `quantile`, `equal`, `jenks`, `headtail` |
| `acled_events`, `ucdp_events` | Transforment un export ACLED ou UCDP GED en fragment de configuration de carte de situation |
| `article_sidecar(svg)` | Relit le titre, le texte alternatif, la description, les zones, les marqueurs et les renvois numérotés d'une planche finie |
| `plate_provenance(svg)`, `replay_report(svg, cfg, files)` | Lisent le tampon de provenance d'une planche, et vérifient qu'une configuration et des fichiers sont bien ce qui l'a dessinée |
| `KINDS`, `MapKind`, `kind`, `kind_names` | Le registre des trois types de carte que lit chaque surface |

### 2. La ligne de commande

Construite avec Click, une bibliothèque Python pour les outils en ligne de
commande à sous-commandes. Elle répond à deux noms, `sprezzature-maps` et
`make-map`, qui pointent vers la même fonction. Deux sous-commandes prennent
aussi deux orthographes : `situation-map` ou `situation_map`, et
`situation-new` ou `situation_new`. Jusqu'au 2026-10-25, il y avait deux
commandes distinctes, une en argparse et un jumeau Click plus riche derrière
un extra `[cli]`, d'où le compte différent des notes plus anciennes.

| Sous-commande | Ce qu'elle fait | Options principales |
|---|---|---|
| `list` | Imprime les trois types de carte | aucune |
| `choropleth` | Rend un choroplèthe du monde | `--data` (CSV, TSV, JSON ou JSONL ; `-` lit du CSV sur l'entrée standard), `--map id=COL --map value=COL`, `--classes 2..12`, `--method`, `--diverging/--no-diverging`, `--relief/--no-relief`, `--simplify`, `--title`, `--out` |
| `situation-map` | Rend une carte de situation depuis une configuration YAML | `--config`, `--title`, `--out` |
| `situation-new` | Écrit une configuration de départ pour une nouvelle planche de situation | `--country` ou `--bbox ouest,sud,est,nord`, `--title`, `--subtitle`, `--as-of AAAA-MM-JJ`, `--out` |
| `density` | Rend une carte d'accumulation | `--points` (liste JSON de `[lon, lat]`), `--bins`, `--title`, `--out` |
| `audit` | Vérifie qu'une planche finie dit comment elle a été faite | `TARGET` (un fichier ou un dossier), `--format text\|json` |
| `improve` | Rend une carte, la fait lire par un modèle de vision, n'applique que les réparations sûres | `--kind`, `--data` / `--config` / `--points`, `--map`, `--out` (un `.png`), `--title`, `--rounds` |

`improve` demande un modèle de vision local. Il ne change jamais de lui-même
la méthode de classification, le nombre de classes ni le cadre : il les
imprime pour qu'une personne décide.

La bibliothèque et l'API HTTP prennent des options que la ligne de commande
n'expose pas, comme `breaks`, `cities`, `rivers`, `width` et `height` pour un
choroplèthe, ou `bbox`, `width` et `caption` pour une carte de densité. Sans
`bbox`, la bibliothèque et la route HTTP découpent sur la fenêtre de la
démonstration, les États-Unis contigus, et écartent ce qui tombe dehors ;
`make-map density --points` et l'éditeur cadrent sur les points reçus. Le titre
sur la foudre et la légende « synthétique » appartiennent à la démonstration :
vos propres points n'y ont pas droit, donc une planche ne dit d'où viennent ses
événements que si vous passez `caption`, et `make-map audit` le signale sinon.

### 3. L'API HTTP, avec Docker et compose

FastAPI, un cadriciel web Python, sert les générateurs en HTTP :

```bash
uvicorn sprezzature_maps.api:app --host 127.0.0.1 --port 8000
```

| Route | operation_id | Ce qu'elle fait |
|---|---|---|
| `GET /health` | `health` | Sonde de vie, renvoie `{"status": "ok"}` |
| `GET /v1/kinds` | `list_kinds` | `["choropleth", "density", "situation_map"]` |
| `POST /v1/choropleth` | `render_choropleth` | Rend un choroplèthe depuis des lignes JSON `{"id", "value"}`, ou la démonstration |
| `POST /v1/situation-map` | `render_situation_map` | Rend une carte de situation depuis un objet de configuration, ou la démonstration Europe |
| `POST /v1/density` | `render_density` | Rend une carte d'accumulation depuis des points `[lon, lat]`, ou la démonstration |
| `GET /` | aucun | La page de galerie |
| `GET /docs`, `GET /redoc` | aucun | La documentation interactive tirée du schéma OpenAPI |

Chaque champ du corps est facultatif, et `format` choisit `svg`, `png`, `pdf`
ou `jpg`. Le dépôt porte un `Dockerfile` et un `docker-compose.yml`.
`docker compose up -d` construit l'image et sert la même application sur le
port 8000, avec `./work` monté sur `/work` pour les fichiers qui entrent et
qui sortent. Le conteneur lance `sprezzature-maps-mcp` : le même port répond
donc aussi au point d'accès MCP sur `/mcp` (section 4).

### 4. Le serveur MCP

MCP, le Model Context Protocol, est le standard qui permet à un assistant IA
d'appeler un outil directement. `sprezzature-maps-mcp` sert l'application HTTP
avec un point d'accès MCP monté sur `/mcp`, sur `127.0.0.1:8000` par défaut
(`--host`, `--port`, ou les variables `SPREZZATURE_MAPS_HOST` et
`SPREZZATURE_MAPS_PORT`). Ses outils sont les cinq routes de l'API ci-dessus,
nommés par leur `operation_id` : `health`, `list_kinds`, `render_choropleth`,
`render_situation_map` et `render_density`. L'audit, la configuration de
départ et `improve` n'ont pas d'outil MCP, parce qu'ils travaillent sur des
fichiers posés sur le disque de l'appelant. L'image Docker et le fichier
compose lancent ce serveur sur `0.0.0.0:8000` : un seul conteneur sert à la
fois les routes `/v1/...` et `/mcp`.

### 5. Le skill

Le skill d'agent `sprezzature-maps` est livré avec le dépôt central
[sprezzature](https://github.com/warith-harchaoui/sprezzature), pas avec
celui-ci. Il oriente un agent vers les appels ci-dessus.
[`TRIGGERS.md`](TRIGGERS.md) porte les règles de routage qu'il suit.

### Et l'éditeur, pour une personne

`sprezzature-maps` ouvre un éditeur sur `http://127.0.0.1:8010/`
(`--host`, `--port`, `--reload`). On y colle des lignes, une configuration ou
des points, on rend, et on peut lancer la même boucle de relecture et de
réparation que `improve`. C'est une page qu'une personne ouvre plutôt qu'une
surface qu'un programme appelle. La raison de son existence à part de l'éditeur
de figures est expliquée [plus bas](#pourquoi-un-dépôt-séparé-plutôt-quun-type-de-graphique-dans-sprezzature-figures).

## Recettes

### Une planche composée comme dans un journal

`style: editorial` donne le registre de la carte de conflit d'un quotidien
plutôt que d'une planche d'atlas. Il ne remplit que ce que la config a
laissé vide :

```yaml
style: editorial
title: "Russia holds nearly a fifth of Ukraine"   # la trouvaille, pas le sujet
legend_position: below                            # la clé sous la carte, les sources sous la clé
areas_of_control:
  baseline: "Ukrainian government control"        # le statu quo : du papier, hors légende
  palette: {"Russian-occupied (approx.)": "#e07a6c"}
labels:
  territories:                                    # la zone nommée sur la zone
    - {lon: 39.05, lat: 49.3, text: "Russian-controlled", color: "#8e3328",
       weight: "700", halo: "none"}
```

Le statu quo est dessiné en papier et les voisins en sol gris : la seule
couleur saturée de la planche est le terrain qui a changé de main. La planche
est plate, sans flèche du nord, et sa ligne de sources passe dans la police
du texte, sous la clé.

Dans un navigateur, la planche raconte aussi son histoire à l'ouverture : le
terrain changé apparaît, le front se trace, les points chauds tombent, en
deux secondes et demie (`animate`). C'est du CSS : `prefers-reduced-motion`
l'arrête, dans un `<img>` compris, et chaque image-clé ne fait que mener à
l'état dessiné. Un rasteriseur ne la joue jamais : le PNG est la carte
finie, à 1/255 près de la même planche avec `animate: false`.

### Ce qui a bougé entre deux dates

La question qu'un chercheur apporte vraiment, et celle à laquelle une
image fixe ne répond pas. La réponse du paquet était une flèche, et une
flèche est la mauvaise réponse : elle affirme à la fois l'intention,
l'élan et le succès sans prouver aucun des trois — les premières cartes
de l'invasion de 2022 en portaient de grosses et se lisaient comme une
guerre éclair qui n'avait pas lieu.

Une couche de différence n'affirme rien. Deux étendues, soustraites :

```yaml
change:
  before: 2022-avril.geojson     # l'étendue antérieure
  after:  2024-decembre.geojson  # par défaut, areas_of_control.source
  actor: "forces russes"         # le terrain de qui ; filtre LES DEUX côtés
  from: "avril 2022"
  to:   "décembre 2024"
```

`actor` est la part facile à oublier et impossible à oublier sans
conséquence. Une différence porte sur le terrain de *quelqu'un*, et
`after` retombe par défaut sur toute la source de contrôle — les zones de
tous les camps à la fois. Les camps d'une couche de contrôle pavent le
même théâtre aux deux dates : leur union bouge à peine, et soustraite
d'elle-même elle annonce que rien ne s'est passé pendant que la ligne
entre eux traversait la carte. Mesuré sur un théâtre à deux camps où l'un
prend une demi-unité de terrain, la couche rendait **`taken` = 0,0** et
donnait tout le rectangle à `held`. Un côté qui épelle plus d'un camp est
donc refusé jusqu'à ce qu'`actor` dise lequel, apparié contre la propriété
qu'`areas_of_control.category_field` nomme déjà, et appliqué aux deux
côtés par l'unique appel qui filtre l'un ou l'autre.

Tenu, pris, perdu en trois couleurs, l'intervalle imprimé au pied avec
l'acteur nommé — « Taken » énonce un sens et ne peut pas énoncer un camp —
et
**chaque classe légendée avec la part de terrain disputé qu'elle
couvre** — « Held throughout — 46 % », « Taken — under 1 % », « Lost —
54 % ». La part se calcule sur l'union des deux étendues, pas sur la
planche : la question porte sur le terrain que l'un ou l'autre a tenu, pas
sur un cadre qui est surtout de la mer. C'est aussi ce qui empêche un
éclat de prendre une ligne muette qu'un lecteur cherchera ensuite sur la
carte.

Deux relevés d'une même frontière, numérisés par des mains différentes, ne
partagent jamais leurs sommets : leur différence est un liseré le long de
toute la frontière, et la planche de Munich a d'abord légendé « Taken —
under 1 % » pour un État qui n'a rien pris en 1938. Tout morceau de terrain
pris ou perdu plus étroit que trois kilomètres est écarté en entier
(`sliver_km: 1.5`, la moitié de cette largeur ; `0` garde tout).

Dans le registre éditorial (`style: editorial`), les trois classes sont
une seule teinte : le terrain tenu en ton pâle, le terrain pris en accent
plein — le rouge foncé du FT pour le récent, le rouge clair pour le tenu
de longue date — et le terrain perdu en contour vide, parce que ce qui est
dessiné là est une absence. Survoler ou atteindre une classe au clavier dit
ce qu'était ce terrain à chaque date (« held in September 1938, not in
October 1938 ») : l'avant et l'après du lieu sous le pointeur, plutôt
qu'une seconde image à comparer de mémoire. Dans un navigateur, la planche
s'ouvre sur le terrain de la première date, puis la perte se vide jusqu'à
son contour et le gain arrive ; le PNG et `prefers-reduced-motion`
reçoivent la planche finie.

Les deux planches de changement livrées soustraient deux relevés, pas un
relevé et un souvenir. `munich-1938` et `serbia-1913` prennent chaque côté
dans une relation OpenHistoricalMap qui porte ses propres `start_date` et
`end_date` — domaine public (CC0), une seule source, un seul schéma de
balisage — téléchargée par `scripts/fetch_historical_extent.py <id de
relation>…` dans `assets/historical-extents/`, si bien que n'importe qui
peut les reprendre. Les frontières actuelles et les noms de villes
d'aujourd'hui sont coupés sur les deux : sur la planche d'une année passée,
ce serait une autre affirmation.

### Une valeur par unité administrative

Un choroplèthe du monde s'indexe sur l'ISO-3166-1 numérique. Une analyse,
non : c'est un taux par région française, un compte par État américain, un
score par Kreis allemand. Ces atlas étaient vendorisés ici depuis toujours
et lus seulement par les couches qui tracent les *lignes* ; `values`
remplit ce qu'il y a dedans :

```yaml
values:
  by: us-states          # ou fr-regions, admin1, admin2, countries
  data: densite.csv      # ou des lignes en place ; un chemin est relatif au config
  key: name              # la colonne qui porte le nom de l'unité
  field: value           # la colonne qui porte le nombre
  classes: 6
  method: jenks          # quantile · equal · jenks · headtail, ou `breaks:`
  label: "HABITANTS AU KILOMÈTRE CARRÉ"
```

Les noms sont appariés à la casse, aux accents et à la ponctuation près,
parce qu'un tableur écrit Provence-Alpes-Côte d'Azur à sa façon. Une table
qui n'apparie **rien** arrête la planche plutôt que de dessiner une carte
grise et confiante d'une faute de nom de colonne, et une cellule qui n'est
pas un nombre l'arrête aussi plutôt que d'être jetée comme si l'unité
n'avait pas de donnée. La légende imprime les bornes et nomme la méthode :
la planche satisfait l'audit par construction — et elle compte les classes
que les données ont **permises**, pas celles que le config a demandées. Les
ex æquo font fusionner des bornes, ce qui est ordinaire : `classes: 6` sur
des comptages avec une longue série de zéros ne fait pas six classes, et une
légende qui l'affirmerait sous six pastilles serait une clé de rien.

Vivre dans la carte de situation plutôt que dans un générateur à soi, c'est
tout l'intérêt : elle hérite de la projection conique, du relief texturé, des
conventions de frontière, des étiquettes qui s'évitent, de l'échelle, du
carton de localisation, du pied de planche et des clauses.

### Puis relire la planche

```bash
make-map audit world.svg            # sort 1 au moindre constat
```

Onze règles statiques sur une planche rendue, parce qu'une carte se relit
comme un texte. Six valent pour toute planche. A-t-elle **nommé sa méthode de
classification** (`method-unnamed` : les mêmes chiffres en quantiles et en
seuils naturels racontent deux histoires différentes) ? Imprime-t-elle ses
bornes de classes (`breaks-missing`) ? Nomme-t-elle le remplissage « sans
donnée », pour que l'absence ne se lise pas comme une valeur basse
(`no-data-hidden`) ? Dit-elle quand elle était vraie, ou qu'elle est
schématique (`no-provenance`) ? A-t-elle un titre (`untitled`) et un nom
accessible (`unlabelled`) ? Une planche qui passe n'en devient pas bonne pour
autant. Elle devient discutable, ce qui est le but.

Une septième, `text-unreadable`, vaut aussi pour toute planche et est décrite
plus bas : elle mesure si chaque mot peut se lire.

Quatre autres ne valent que pour une planche **régionale** (`no-locator`,
`undated-control`, `evidence-unclassed`, `disputed-unflagged`), et viennent des
normes contre lesquelles on la lit — les UNHCR Mapping Guidelines pour le
mobilier, l'Institute for the Study of War pour le modèle de preuve.
Porte-t-elle un **carton de localisation**, pour qu'un lecteur qui ignore où
c'est puisse le situer. Une carte de contrôle dit-elle **à quelle date** — et
la règle large ne suffit pas ici, parce qu'une année d'édition citée en
source n'est pas la date à laquelle un front était vrai. Ses zones sont-elles
**graduées en preuve**, ou la revendication d'un belligérant ressemble-t-elle
exactement à une observation géolocalisée. Et porte-t-elle la **clause** que
son étendue lui impose, pour les trois frontières à phrase standard ? Le
générateur fournit désormais la première et la dernière tout seul ; les deux
autres sont des phrases que seul un auteur peut écrire.

### Depuis un jeu de données de conflit, en un appel

Les deux jeux de données sur lesquels repose la recherche sur la paix et les
conflits, [ACLED](https://acleddata.com/methodology/acled-codebook) et
l'[UCDP Georeferenced Event Dataset](https://ucdp.uu.se/downloads/),
consignent chacun, à côté de chaque coordonnée, **à quel point cette
coordonnée est connue** : le `geo_precision` 1 à 3 d'ACLED, le `where_prec`
1 à 7 d'UCDP. Le 3 d'ACLED signifie une capitale provinciale qui tient lieu de
province entière ; le 6 d'UCDP signifie que seul le pays est connu. Les outils
qui tracent ces données les dessinent toutes comme le même point, ce qui
affirme un coin de rue que la source n'a jamais donné, une fois par ligne.

Les marqueurs de ce générateur font déjà la distinction : un disque plein
cerclé pour un lieu nommé, un anneau creux pour un lieu approximatif, un
anneau brisé pour une région épinglée sur sa capitale, un rayon tracé quand le
jeu de données en énonce un. Les chargeurs sont l'étape entre le fichier et la
marque :

```python
from sprezzature_maps import acled_events, make_situation_map

cfg = {"title": "Soudan : violence politique enregistrée, 2024"}
cfg.update(acled_events("sudan-2024.csv", derive_region=True))
make_situation_map(config=cfg, out="sudan.svg")
```

Une planche est aussi un document navigable : ses polygones de revendication,
ses marques d'événement et ses commandes de légende sont atteignables au
clavier, et chacun se nomme auprès d'un lecteur d'écran, y compris **à quel
point la position d'une marque est connue**, pour qu'un lecteur qui ne voit
pas un anneau brisé apprenne en mots ce qu'il signifie. Avec
`print_width: "90mm"`, le fichier arrive à la largeur de colonne d'une revue,
et la planche dit en points la taille à laquelle sa plus petite étiquette
s'imprimera vraiment.

`ucdp_events` fait de même pour GED, ramène ses sept degrés de précision aux
trois dans une table écrite en clair dans `scripts/_conflict.py`, et **refuse
de placer les lignes connues seulement au niveau du pays** : il les compte sur
la ligne de méthode de la planche plutôt que de les jeter en silence. Voir
[`EXAMPLES.md`](EXAMPLES.md#conflict-event-data-acled-and-ucdp-ged).

### Un panneau par fenêtre de temps

Une planche est un instantané ; l'essentiel de ce que la recherche dit d'un
conflit est un changement. `small_multiples` découpe la même configuration en
un panneau par année, trimestre, mois, semaine ou jour :

```python
cfg = {"title": "Violence politique enregistrée, par trimestre"}
cfg.update(acled_events("export.csv", derive_region=True, size_by="fatalities"))
cfg["small_multiples"] = {"by": "quarter", "columns": 4}
make_situation_map(config=cfg, out="by-quarter.svg")
```

Chaque panneau vient de cette seule configuration, si bien que l'étendue, la
projection et l'échelle des marqueurs ne peuvent pas diverger d'une image à
l'autre comme lorsqu'on exporte une planche par fenêtre, et la feuille dessine
une seule fois le titre, la légende, la règle et les crédits. Deux règles ne
plient pas. **Une fenêtre vide reste un panneau** : la supprimer referme le
trou, et les panneaux voisins se lisent alors comme consécutifs. **Une marque
n'est placée que là où son propre `time_precision` le permet** : une ligne
datée *mois de mars* va dans un panneau de mars et dans aucun panneau de
semaine, et ce qui ne tient dans aucune fenêtre est compté sur la feuille
plutôt que rangé quand même.

Un mot sur le temps que cela prend, puisque rien à l'écran ne vous le dira.
Un choroplèthe demande environ une seconde. Une carte de situation dépend de
la quantité de monde dans le cadre : la démo Europe embarquée demande une
dizaine de secondes à froid, une planche régionale comme l'est de la RDC
environ trois une fois le processus chaud. Sur le temps de la démo, environ
2 s vont à l'ombrage du relief, environ 2 s au chargement des atlas embarqués
et aux imports — payés une fois par processus, donc un serveur rend sa
deuxième planche plus vite que la première — et le reste est de la géométrie
réelle. `basemap: {relief: false}` supprime le coût du relief si vous n'en
avez pas besoin.

### Prouver quelles entrées ont dessiné une planche

Une planche imprime déjà `method`, `source` et `as_of` : ce dont elle a été
tirée, en prose, pour un lecteur. Rien de cela ne répond à la question qu'une
relecture pose vraiment à une figure publiée : *est-ce l'image que ces entrées
produisent ?* Le dessin est fonction de trois choses, le code, la
configuration et le fichier qu'un chargeur a lu en chemin. `provenance` prend
donc l'empreinte de chacune dans `<metadata>`, qui ne dessine aucun pixel :

```python
cfg = {"title": "Violence politique enregistrée", "provenance": True}
cfg.update(acled_events("export.csv", derive_region=True))
make_situation_map(config=cfg, out="plate.svg")
```

```python
from sprezzature_maps import plate_provenance, replay_report

plate_provenance(svg)   # {"version", "config_sha256", "inputs": [...]}

report = replay_report(svg, cfg, ["export.csv"])
report["replays"]       # True seulement si tout ce que le tampon nomme correspond
report["differences"]   # ["export.csv differs: 3f2a91c0d4e8 on the plate, …"]
```

Trois choix, chacun l'inverse de l'évidence. **Le tampon consigne des
empreintes, pas les entrées** : une configuration `areas_of_control` porte des
coordonnées et une `source` porte un chemin qui nomme la machine de quelqu'un,
donc embarquer l'une ou l'autre la publierait, alors qu'une empreinte ne
publie rien et laisse quiconque détient les entrées prouver la
correspondance. **Il ne porte aucune horloge**, puisqu'une heure de rendu
ferait différer deux rendus des mêmes entrées et détruirait la propriété que
le champ existe pour consigner. Et **il est désactivé par défaut**, parce
qu'il porte la version du paquet : l'activer pour tout le monde changerait
chaque planche versionnée à chaque nouvelle version.

Une entrée tamponnée que personne ne fournit revient sous `unchecked`, pas
comme une correspondance : la planche est alors non réfutée, ce qui n'est pas
la même chose que reproduite. Les chargeurs de conflit remplissent la liste
des entrées pour vous : au moment où `make_situation_map` voit la
configuration, les lignes sont en place et le CSV a disparu, et le chargeur
est le seul point de la chaîne qui sait encore de quel export il s'agissait.

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
décision de produit délibérée : the editor, l'éditeur de
graphiques conversationnel livré avec `sprezzature-figures`, ne gagnera
pas le support des cartes. Les cartes ont donc le leur, séparé, et il est
ici :

```sh
sprezzature-maps          # http://127.0.0.1:8010/
```

Ce qui sépare les deux, c'est la donnée et non l'image de marque. un éditeur de
graphiques peut supposer un tableau et demander quelle colonne joue quel rôle.
Ces trois types prennent trois choses différentes — des lignes par territoire
pour un choroplèthe, une *configuration* de région sans aucun tableau dedans
pour une carte de situation, et une liste nue de positions `[lon, lat]` pour
une carte de densité. Apprendre les trois à un seul panneau d'entrée aurait
rendu l'éditeur des graphiques moins bon en graphiques pour le rendre médiocre
en cartes.

Il est en FastAPI et HTML rendu côté serveur, et non en NiceGUI comme celui de
figures. Mesuré avant de décider : NiceGUI coûte **20 paquets** que rien
d'autre dans ce graphe n'apporte, soit une pile websocket pour la vue d'une
seule surface, alors que FastAPI et uvicorn sont déjà en dépendances de base
ici. Et les chiffres de l'éditeur de figures disent que la vue est la moitié bon
marché à choisir : 117 de ses 5397 lignes touchent NiceGUI, et ses
sous-paquets `ingest`, `recommendation`, `export` et `ralph` le touchent dans
**0 fichier sur 34**. C'est cette séparation qu'il faut copier, donc tout ce
qui *décide* quelque chose dans `sprezzature_maps.editor` est importable et
testable sans serveur.

## État du projet

Publié sur PyPI ([`sprezzature-maps`](https://pypi.org/project/sprezzature-maps/)),
avec une CI au vert (lint, vérification des types, tests et doctests à
chaque push et pull request vers `main`, plus une vérification
d'installation et d'import sous Python 3.10 ; voir
`.github/workflows/ci.yml`) : `pytest` passe,
les trois types de carte se rendent depuis leurs données de
démonstration intégrées, et la ligne de commande produit de vrais fichiers
SVG. Il n'y a pas de page de catalogue façon FIGURES.md (avec trois types, ce
LISEZMOI en tient lieu).

Dix-sept cartes de situation complètes vivent dans
`scripts/build_situation_examples.py`, régénérables dans
`assets/situation-maps/` par `python scripts/build_situation_examples.py` (ou
une seule par son nom, par exemple
`python scripts/build_situation_examples.py sudan`). Six sont thématiques :
l'Ukraine, le bas Dniepr (la planche qui accompagne un article, avec ses
repères numérotés), la Syrie et la Libye comme instantanés historiques, le
Soudan et l'est de la RDC d'après des sources ouvertes jusqu'à fin septembre
2026, et deux planches de changement, la Tchécoslovaquie à travers Munich en
1938 et la Serbie à travers les guerres balkaniques, chacune la différence
entre deux relevés datés d'OpenHistoricalMap. Chacune des six premières est
schématique par construction, le dit sur la planche, et garde ses lignes de revendication en Python lisible plutôt que
dans un fichier de données opaque : un lecteur en désaccord voit exactement
quelles coordonnées contester. Les neuf autres sont des planches de référence
sans couche thématique : la Suisse, la péninsule Ibérique, l'Europe de
l'Ouest, l'Himalaya, les Caraïbes, les Andes, le Sahel, le détroit d'Ormuz, et
la mer de Chine méridionale, dessinée sans aucune ligne de revendication.

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
colonne de téléphone fait environ 375. La carte de légende fait au moins 262
unités de large : acceptable à 1000, elle recouvre la carte à 375. `legend_position`
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

**La direction peut être mesurée plutôt que devinée.** `place` accepte les
quatre côtés et les quatre diagonales — chaque trait d'appel tombe donc à
90 ou 45 degrés, la règle de Datawrapper d'après Beck — et `place: auto`
les essaie dans cet ordre et retient la première dont chaque ligne évite
les noms déjà posés sur la planche. `annotations` était ici la seule
couche de texte qui ne consultait jamais le registre d'encre, et une main
qui se trompait écrivait une phrase au travers d'un toponyme — au plus
visible, puisque la note est dessinée au-dessus de toutes les couches de
carte. Une note qui n'a nulle part où aller est refusée nommément, pas
dessinée dans la direction la moins mauvaise.

**Un repère numéroté est la moitié d'un renvoi dont l'autre moitié est un
paragraphe.**

```yaml
annotations:
  - at: [32.6250, 46.6425]
    number: 1
    text: "Kherson, reprise en novembre 2022."
    place: auto
```

Les numéros doivent courir de 1 à n, sans trou ni répétition : une planche
qui affiche 1, 2 et 4 envoie le lecteur chercher sur la carte un 3 qui a
été coupé de l'article. Et ils ressortent de la planche finie, pour que la
page imprime la liste qu'on lui donne plutôt qu'une liste retapée à côté :

```python
from sprezzature_maps import article_sidecar
for note in article_sidecar(svg)["callouts"]:
    print(f"{note['number']}. {note['text']}")
```

Le badge est atteignable au clavier et annonce les mots de la note, pas
son chiffre : un renvoi ne sert à rien à un lecteur qui l'atteint et
entend « 3 ».

**Et un rectangle dit où est l'histoire.** L'étendue doit rester assez
large pour se situer — c'est l'argument du carton de localisation — et le
sujet se passe en général dans un dixième :

```yaml
detail_area:
  bbox: [32.3, 46.15, 35.0, 47.75]
  label: "Lower Dnieper"
```

Un contour et une étiquette, rien d'autre. Assombrir le contexte autour a
été essayé puis refusé : un voile sur le relief, les aplats de contrôle et
l'eau change toutes les couleurs que la légende explique, donc la légende
montrerait des teintes que la planche ne dessine plus.

Les exemples dont ces trois dispositifs sont tirés — huit cartes de
situation du New York Times, nommées, lues à travers leur propre couche de
texte — sont dans
[`references/situation-map-annotation.md`](references/situation-map-annotation.md),
avec la raison pour laquelle ce paquet refuse toujours les flèches de
mouvement alors que la rédaction qui a inventé la forme moderne de ces
planches a passé 2022 à les abandonner.

**Elle dit où c'est sur Terre, sans qu'on le demande.** « Dézoomer pour la
perspective, zoomer pour le détail » est la règle unique de la carte de
localisation, et une planche qui ne fait que zoomer n'en honore que la
moitié. Une planche régionale trace donc un carton de localisation par
défaut — la zone cartographiée en rouge sur une vue plus large, sur
15 % de la largeur. Une planche déjà assez large pour se situer
elle-même n'en reçoit pas, et on peut toujours refuser :

```yaml
inset:
  position: top-right     # ou n'importe quel coin ; omis, il prend celui
                          # que la légende et l'échelle n'ont pas pris
  zoom: 6                 # l'ampleur du dézoom, faute de bbox
  show: false             # pas de carton sur cette planche
```

**Sa date est estampillée sous le titre, pas seulement au pied.** Les
guidelines mettent « as of DD Month YYYY » juste sous la ligne de
chapeau, parce que c'est le fait le plus important d'une planche de
contrôle et celui qu'un lecteur veut avant tout le reste. Le pied garde
la ligne entière — la copie qui voyage avec une capture d'écran ;
l'estampille est celle qu'on voit en décidant de croire la carte.

**Chaque mot y est lisible, et c'est mesuré.** Une carte est surtout de
la typographie, et ce paquet plaçait déjà ses *étiquettes* avec de vraies
métriques de fonte. Pas son mobilier : la barre d'échelle, la carte de
légende, les bornes sous une bande de couleurs et le pied de planche
étaient chacun posés par un calcul juste sur la planche où il avait été
réglé. `make-map audit` reconstruit désormais la boîte d'encre de chaque
`<text>` et signale celles qui se touchent, qui débordent ou qui sont
trop petites — c'est ainsi que la règle imprimée à travers une bande de
couleurs, un pied qui perdait onze mots sur la planche du Kivu, et quatre
noms de villes enterrés sous ce pied ont été trouvés d'un coup.

**Elle porte la clause que son étendue lui impose.** Trois frontières ont
une phrase standard attachée — le Jammu-et-Cachemire, le Soudan et le
Soudan du Sud, Abyei. Tracer une de ces lignes sans rien dire est une
position prise par omission, donc la phrase s'ajoute au pied de planche dès
que la région atteint la frontière, au même titre que la mention
OpenStreetMap automatique : une obligation qu'un appelant doit se rappeler
est une obligation que les planches ne tiendront pas. Refuser le pied de
planche ne refuse pas la phrase.

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

Les cinq façons d'atteindre tout cela sont décrites sous
[Cinq façons d'y accéder](#cinq-façons-dy-accéder).

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
  l'Allemagne et de l'Italie (régions, cantons, Länder), et le Vardar
  (que Natural Earth range sous le nom de son affluent) : ©
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
