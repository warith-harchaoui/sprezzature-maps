# The annotation layer: what makes a situation map an argument

Written 2026-10-31, as the companion to `situation-map-requirements.md`.
That document asks what a plate **owes** — evidence classes, precision
codes, locator, disclaimers, label hierarchy. This one asks a narrower
question, the one that comes up when a plate has to run *beside an
article*: what is drawn on the map face that is not geography?

The reference standard is the same, the New York Times graphics desk.

> "The annotation layer is the most important thing we do … otherwise
> it's a case of here it is, you go figure it out."
> — Amanda COX, then graphics editor, The New York Times

## How this was researched, and what that limits

The NYT (The New York Times) builds these graphics with **ai2html**: the artwork is a raster,
but every on-map label, legend entry, annotation sentence, scale bar and
Note line is real HTML text, including the separate desktop and mobile
variants. Read through the Internet Archive, that makes the **wording**
of roughly forty situation maps recoverable verbatim, which is what every
quotation in `code style` below is.

It does **not** recover geometry. Leader lines, highlight-rectangle
strokes, inset connectors and greyed fills live in the raster and are
invisible to this method. Wherever this document says "no arrow", it
means no arrow label, no arrow image asset and no textual trace — not
proof of absence.

## Where this package stands, measured

| Device | In the generator | Used by a plate |
|---|---|---|
| `annotations` (ring, leader, note) | yes | **no, zero of fourteen** |
| `labels.territories` (area name, tracked) | yes | yes |
| `inset` (locator, zooms **out**) | yes | yes, by default |
| Numbered callout keyed to the article | no | — |
| Measured placement for a note | no | — |
| Detail area / emphasis box | no | — |
| Detail inset (zooms **in**) | no | — |

The first row is the headline. The editorial annotation layer — a circled
point, a leader line, a sentence, with a halo so it survives the relief —
was written, documented, validated, and called by **none** of the fourteen
bundled plates. It is this repository's dominant failure mode in its
purest form: the tool exists and nothing calls it.

---

## 1. The examples

### 1.1 "The fight for Mosul", October 2016 — the numbered-marker exemplar

The clearest instance in the corpus of the device this document exists
for. The 1 November 2016 map carries markers **1 to 6** on the map face,
keyed to six numbered sentences beside it:

- `1 Heavy fighting was reported from the neighborhood of Karama on Tuesday.`
- `2 Iraqi forces first entered the city through the industrial Gogjali neighborhood.`
- `4 Iraqi Shiite militias have begun an offensive from the Qayyarah military base to take Tal Afar.`
- `5 If the Islamic State loses control of Tal Afar, its connection to Raqqa in Syria will be severed.`

Three further things on that map face are worth copying exactly:

- **The legend is written onto the coloured area, and every entry is
  dated**: `ISIS-CONTROLLED AREAS NOV. 1`, `AREAS LOST BY ISIS SINCE OCT. 17`,
  `AREAS LOST SINCE OCT. 10`. All caps, on the ground, with a date — not a
  swatch in a box.
- **Annotation blocks with a bold place-name lede**: `Qaiyara Airfield
  West / Thousands of Iraqi Army troops have gathered here.`
- Direction is a bare text label, `to Raqqa`. **No arrows.**

The same device appears on `How Russian troops closed in on Ukraine`
(22 February 2022): four panels marked 1–4, keyed to four numbered
paragraphs, with paragraph 4 handling a contested claim in words
("though U.S. officials disputed this claim").

**And then it largely stops.** Numbered integer markers are absent from
every fire map, every hurricane map, every Gaza map, and from Beirut,
Turkey, Morocco, Derna, Sudan, Syria, Bakhmut and Mariupol. The step
marker survived; the integer did not. What replaced it is a **marker
whose label is its own handle**:

- a **timestamp** — Tubbs 2017, Camp Fire 2018, Maui 2023, Los Angeles 2025;
- a **date** — Kherson 2022, Bakhmut 2023;
- a **distance** — `Approx distance from origin of fire`, `0 miles` … `20 miles`;
- a **place name** — Helene 2024;
- a **named household or victim** — Camp Fire's `Home of the Wiggins
  Family`; Tubbs's `Christina HANSON, 27, who used a wheelchair, died at
  home.`

That is the finding for an implementer, and it is not "do not number
things". It is that the device is *a mark whose label is the article's
handle on it*, and the integer is the strictest special case. It is also
the only case a generator can police: 1..n with no gap is checkable, and
"Thursday, 11 p.m." is not.

### 1.2 The Ukraine maps, 26 February 2022 to May 2024 — the retreat from arrows

Levi Westerveld archived four of them and described the change
([thread, 22 March 2022](https://convopage.com/c/1506253203704356867)):

- **26 Feb** — "Large red arrows and an almost opaque red color shows
  Russian advances in Ukraine. **Suggesting fast, large and controlled
  overtaking.**"
- **3 Mar** — "Arrows are considerably smaller, and the occupied areas are
  shown in a more transparent red color. … **Still, Ukrainian forces
  appear non-existent on the map.**"
- **7 Mar** — "NYT's maps now show **for the first time the Ukrainian
  forces in blue** … **cities under Russian control are now labeled in
  red**."
- **21 Mar** — "**The 'Russian occupied areas' previously shown in red are
  no longer shown on the map.**"

He asked the desk whether this was the war changing or the cartography.
**The desk never answered** — 209 replies, none from NYT staff.

The legends corroborate him independently. 11 March: `Occupied areas /
Past advance / Recent advance / Ukrainian defense / Taken by Russians`.
21 March: `Recent fighting / Past advance / …`. The area-fill occupation
category was genuinely dropped and replaced by an **incident** category,
with the note `Approximate areas of fighting are drawn from reports from
March 13 to 21.`

Read the fourth step carefully, because it is not the step people
remember. The arrows did not merely shrink; the **area fill went away**,
and what carried the claim afterwards was **typography** — named cities,
coloured by who holds them. The desk's own resolution of the honesty
problem was to move the claim out of the geometry and into the annotation
layer. That is the single most transposable finding here, and it is free:
a hand-written SVG (Scalable Vector Graphics, the text-described image format these plates are written in) generator is *better* at placing coloured, haloed,
tiered type than at drawing an honest polygon, because the polygon needs
a source it does not have and the label needs a coordinate and a name.

By 2024 the vocabulary is mature and arrow-free. `Mapping Russia's Sudden
Push Across Ukrainian Lines` (15 May 2024, Marco Hernandez) shows advance
as **two dated bands side by side** — `RUSSIAN ADVANCE AS OF MAY 14` and
`RUSSIAN ADVANCE MAY 11` — and writes the directional claim that would
once have been an arrow as a **sentence on the map face**: `Russia
launched one line of attack near Ohirtseve.` "Line of attack" is a
phrase, not a glyph.

### 1.3 The control definitions, stated on the map face

The NYT publishes almost nothing about its own situation-map method in
essays — no NYT Open, Times Insider, Source or Nieman Lab piece on it
exists. **The reasoning is published in the Note lines of the maps
themselves.** The best of them, from `Russia tightens its grip on
Mariupol`, 13 April 2022:

> `Note: Russian-controlled areas represent territory that Russian forces
> are able to operate freely in, without immediate risk of Ukrainian
> counterattacks, as assessed by the Institute for the Study of War.
> Areas of Russian advances indicate where Russian troops were seen.`

Control means *can operate freely*. Advance means *troops were seen*. Two
epistemic claims, separated in one sentence on the page. That is
`situation-map-requirements.md` §E4 — a stated `control_definition` —
already written by somebody else, and it belongs in a plate's `method`
line.

Alongside it the desk keeps a stable vocabulary of **deliberate
emptiness**, all verbatim: `Approximate` and `Approx.` **in legends, not
in footnotes**; `visibly damaged or destroyed in satellite imagery`;
`appear swept away or buried`; `Russian-claimed control` kept
categorically apart from assessed control; `Control disputed.`; `Status
of residents unknown` as a swatched legend category; `Sparsely populated
areas`; `Last recorded locations`; `may change in subsequent
assessments`; `may differ … by 500 meters or more`; `These maps do not
capture strikes that did not result in damage to manmade structures.`
And per-layer source scoping is universal — `(Russian-occupied areas)`,
`(fire detections)`, `(acres, structures, containment)`, `(populations)`,
`(R.S.F. control)`.

### 1.4 Gaza, 28–31 October 2023 — refusing the arrow where the headline asserts it

`Where Israeli troops are encircling Gaza City` (30 October 2023). The
body says Israel is approaching "from at least three sides". The map face
uses **no arrows at all**. Instead it marks what was observed:
`Where Israeli troops have crossed`, `Large groups of armored vehicles`,
`Armored vehicle seen on major road` — note `seen` — under the legend
`Locations of Israeli troops in northern Gaza`, sourced `Satellite
imagery, videos and photos`.

Two days earlier, `Where Israeli military videos show ground forces
entering Gaza` scopes the claim in its own **headline**, and again in its
legend: `Locations of tanks and strikes inside northern Gaza in videos
released since Thursday`, sourced `Footage released by Israel Defense
Forces`. The annotations date the *posting*, not the event.

This is the strongest single case for the package's standing position:
the desk had an encirclement to draw, four arrows would have drawn it,
and it drew crossing points and vehicle sightings instead.

### 1.5 The fire maps — spread without arrows

`How California's Most Destructive Wildfire Spread, Hour by Hour`
(21 October 2017, Tubbs; Tim Wallace among the bylines) shows the fire's
advance as **labelled hourly isochrones** — `11 p.m.`, `12 a.m.`,
`1 a.m.`, `2 a.m.`, `3 a.m.` ringing the edge — under the legend
`Approximate edge of fire at 10:30 p.m.` Direction is bare text with a
distance: `TO CALISTOGA`, `60 MILES TO SAN FRANCISCO`.

Wallace on that map, to GeoHipster, is the best first-person statement on
drawn uncertainty in the whole corpus:

> "We tried our best not to imply any more precision than we had. **You
> may notice the lines aren't sharp**, for example. Their gradient is
> meant to visually display the fuzziness of the precision of our
> timeline based on our amalgam of sources."

And, on a control map of ISIS (the Islamic State of Iraq and Syria), to the magazine Wired in 2014:

> "**You don't want to put a hard line around that.** It's not like you
> cross a river and all of a sudden it's sparsely populated."

`'Hell on Earth': The First 12 Hours of California's Deadliest Wildfire`
(18 November 2018, Camp Fire) is the only NYT fire map found that shipped
arrows at all — three scroll-triggered PNGs, one of which is **disabled
in the published code**, an arrow step killed during editing. Its markers
are **red, bold and named, not numbered**: `Home of Jason PORTILLO and
Lidia ROSALES`, `Ridgewood Mobile Home Park`, `Fire extent at 10:45 a.m.`
It replaces the scale bar with a **distance ladder** — `Approx distance
from origin of fire`, `0 miles` … `20 miles` — and defines its own key
term on the map face: `Over 10,000 buildings, shown in red, were more
than 50 percent destroyed.`

The 2025 Los Angeles maps carry no arrows at all — the string does not
occur on the page — on a piece about where the fire went. They do carry
**two different "as of" times for two layers of one map**, and a
legend-gloss sentence correcting a predictable misreading: *"A fire's
'containment' is an indication of its potential for growth, not how much
of it has been extinguished."*

### 1.6 Hurricane Ian, September 2022 — uncertainty as a number, not a shape

The tracker's legend says `Forecast path`. **The word "cone" does not
appear on the page.** Storm motion is a line with timestamped dots and no
arrowhead. The surge legend is `Potential storm surge flooding` with an
open-ended ramp `1 3 6 9+ feet`, and underneath it the strongest
uncertainty statement found anywhere in the corpus:

> `Note: There is about a 10 percent chance that flooding could exceed the
> levels shown.`

This matters because the cone is the most-deployed uncertainty graphic in
the world and is routinely misread: a 2022 survey of more than 2,800
Floridians found nearly half believed it showed *all* possible tracks,
and others read its width as the storm's size. A device that encodes
uncertainty in its **shape** gets read as a statement about extent. A
device that encodes it in **texture, line style or a stated number** is
harder to misread. That is an argument for the confidence tiers and
against inventing a geometric uncertainty primitive.

### 1.7 The label system, measured

The Ukraine tracker's ai2html stylesheet carries **290 paragraph
styles**: ten sizes from 9 to 18 px, three weights (700 / 500 / 300),
23 `text-transform: uppercase` rules, and the colours `#000`, `#fff`,
`#c00`, `#606060`, `#9b9b9b`.

Two rules in it are directly transposable:

- **The non-subject landscape is pushed back with opacity, not with a
  grey fill** — the Camp Fire graphic uses 0.2 / 0.36 / 0.4 / 0.5 / 0.6 /
  0.8. A grey wash changes every colour under it; opacity on the labels
  does not.
- **Italic is reserved for hydrography.** This package already does that.

The casing convention is stable across every example: all capitals for
countries, seas, oblasts, the subject settlement, and — the part worth
stealing — **status areas**: `HELD BY RUSSIA`, `ISIS-CONTROLLED AREAS
NOV. 1`, `RUSSIAN POSITIONS AS OF JAN. 24`, `SITE OF EXPLOSIONS`. Title
case for context cities, streets, rivers and individual buildings. This
package's `labels.territories` draws exactly that register — tracked,
wide, all-caps, faint — and the plates use it only for physical regions.

Responsive triage is aggressive and visible: `MEDITERRANEAN SEA` →
`MED. SEA`, `POLAND` → `POL.`, `5 miles` → `5 mi.` The furniture
**abbreviates rather than disappears**.

### 1.8 Detail areas, scale bars and north arrows

The detail-inset label vocabulary is tiny and fixed: `Detail area`,
`Area of detail`, `Detail below`, `Detail`, `Area shown`, `SHOWN ON MAP`,
`Location of fire`. (One article uses `Detail area` on its first map and
`DETAIL AREA` on its second — the house style is not perfectly enforced.)

Scale bars are near-universal and **always worded** — `¼ mile`,
`HALF MILE`, `One mile`, `100 ft`, `200 MILES` — never a bare numeral
with a glyph.

**North arrows appear almost never**: only on rotated satellite or aerial
bases — the Gaza maps, the Turkey quake map, the Los Angeles before/after pairs.
The Ian and Helene hurricane maps carry neither a scale bar nor a north
arrow. The working rule is: a north arrow on a north-up thematic map
tells the reader something they already assumed. Every plate this package
draws is north-up and every one carries an arrow; that is a defensible
house choice and it is not the reference standard's.

### 1.9 Datawrapper's callout lines — the one geometric rule recoverable

Their locator callout lines have a "built-in tendency to be in 90° or 45°
angle", so a reader asking for a right angle gets 90° and not "91° or
89°", explicitly after Harry BECK's underground map
([Datawrapper](https://www.datawrapper.de/blog/locator-maps-callout-lines-swoopy-arrows)).
Their annotation guidance adds: for a region rather than a point, "use
circles instead of arrows"; "reusing your data colors for the annotations
helps them sit back onto the map"; and — the rule this package needed
most — **get rid of the place labels the annotations already name**,
because "extra text steals attention from your annotations".

---

## 2. The arrow question, settled

`situation-map-requirements.md` §C3 and the `change` layer's changelog
hold that an arrow "asserts intent, momentum and success at once while
evidencing none of the three", and refuse arrows by default. The brief
for this document asked whether that is too strict, given that the NYT
does draw arrows. **It is not too strict. The evidence sharpens it.**

What the NYT actually does:

- **Military advance, February to April 2022 only** — and every arrow
  carried a text label naming what it meant: `Russian troop movements`,
  `Directions of recent Russian advances toward Kyiv`, and a declared
  legend category `Possible advance` with modal sentences beside it
  ("hope to move south", "may push north").
- **Abandoned for territorial advance from 2023.** Advance becomes a
  **dated shaded area with an all-caps caption**: `RUSSIAN ADVANCE
  (FEB. - MARCH)`, `RUSSIAN ADVANCE AS OF MAY 14`, `Territorial gains
  since June 1`. *That is this package's `change` layer, arrived at
  independently.*
- **Refused for ground incursion** in Gaza, where the headline asserted
  encirclement (§1.4).
- **Refused for wind** — streaks and particles, with the device named in
  the caption — and **refused for storm motion** (§1.6).
- **Still used for a route**: `Evacuation route toward Kyiv`,
  `Direction of water along wadi`, aircraft paths. The *territorial*
  arrow went away; the *route* arrow did not.

And one correction, published, that settles what an arrow is:

> `Jan. 30, 2025: Arrow direction error corrected (pointing south, not
> north).`

An arrow's geometry is a factual claim the desk will issue a correction
for.

The scholarship agrees. Specht and Kent in *Geographical* (1 April 2022)
name the paper directly: "**The New York Times has avoided marking blocks
of territorial gains, but rather produces maps that show the fluidity of
the situation on the ground**", and on arrows generally: "an arrow can
imply a threat to a destination, whether its subject is a body of
refugees or an invading army." Cheshire and Kent, *The Cartographic
Journal* (2023), go further: "It is difficult to separate a sense of
threat from even the thin and fletched designs of the first arrows on
maps", and note that the conditions producing arrow maps — thin data, a
broad audience, speed — "are the same conditions that underpinned
Schumacher's 1935 symbology guide that rallied against nuance and
detail". The BBC (British Broadcasting Corporation) replaced its refugee arrows with circles after
criticism; the FT (Financial Times) abandoned refugee-flow arrows for proportional circles.

The honest counter-position exists and should be recorded: Tom FISH
argues arrows are *preferable* to control zones because they show
movement without the messy question of who controls what. This package
answers that with the `change` layer — a difference asserts nothing about
intent and is still about movement — which is exactly the answer the NYT
reached in 2023.

**Conclusion: keep the refusal, and stop trying to replace the arrow with
a better arrow.** One amendment to the existing position, from §1.2: the
package's stated alternative has been *geometric* (a difference layer,
two frames). The NYT's is also **typographic** — the dated, all-caps
status label written on the ground. That is the gap this document closes.

---

## 3. What was built

**A1. The numbered callout.** `annotations[].number` draws a numbered
badge at the point and heads the article's paragraph with the same
integer. The numbers must be 1..n with no gap and no repeat, because a
plate showing 1, 2 and 4 sends a reader hunting for a 3 that was cut from
the prose. The badges are stamped `data-callout` and read back out of the
finished plate by `article_sidecar`, so the page's numbered list is
generated from the same artefact that drew the map — the one half of
"accompanying an article" a generator can actually guarantee. The badge is
focusable and announces the note's words, because a reference whose other
half is a paragraph is useless to a reader who reaches it by keyboard and
hears a digit.

Per §1.1 the integer is the strictest form of the device and not the
desk's current default; the looser forms — a mark labelled with a
timestamp, a date or a name — are the annotation layer's existing `text`
with no `number`, and need no new code.

**A2. Measured placement.** `place: auto` chooses among eight compass
directions — 45° and 90° only, per §1.9 — the first whose every line
clears the ink already on the plate and stays on the drawn map; and
refuses, naming the note, when none does. `annotations` was the only text
layer in the generator that never consulted the ink ledger.

Building it surfaced a second defect that only a rendered plate shows:
the notes were placed one at a time against a plate that was not
finished, so note 1 took paper that note 2's badge then landed on. Every
mark is now down and in the ledger before any sentence is placed.

**A3. The detail area.** `detail_area: {bbox, label, color, label_at}`
draws a labelled rectangle around the ground the article is about, with
`Detail area` as its default wording per §1.8. The plate stays wide
enough to place itself — which is what the locator argues — and says in
one mark that the story is in a tenth of it.

### Deliberately not built, and why

**The detail inset** (a magnified medallion of a sub-extent with a
connector back) is the device I most wanted and the most expensive here:
it needs the whole geographic stack re-projected and re-drawn at a second
scale inside a clip, with its own label pass and its own ledger.
`_inset_layer` only zooms out and draws a land outline and a rectangle,
so there is nothing to extend. A3 declares the area such an inset would
magnify, which is the half that costs nothing; the magnification is
separate work and should be sized as such.

**Dimming the non-subject area.** §1.7 says the NYT pushes context back
with opacity on the *labels*. A wash over the relief, the control fills
and the water would change every colour the legend keys — the defect
`_change_blend` exists to prevent, reintroduced for an effect.

**A swoopy or curved leader** is in Datawrapper's feature set and is
against §1.9's own rule, which is the part of that feature worth having.

**A geometric uncertainty primitive** — a cone, a fan, a soft edge — is
refused on §1.6's evidence. `circle_km` and the confidence tiers encode
uncertainty in texture, which is harder to misread as a measurement.

### Recorded, not acted on

- **The north arrow on every plate** (§1.8) is not the reference
  standard's practice for north-up thematic maps. Changing it touches all
  fourteen shipped plates and is a separate decision.
- **The dated, all-caps status label** (§1.2, §1.7) — `RUSSIAN ADVANCE AS
  OF MAY 14` written on the ground — needs no new code: it is
  `labels.territories`, which the plates use only for physical regions.
- **The control definition on the plate** (§1.3) is
  `situation-map-requirements.md` §E4, and belongs in `method`.

---

## Sources

- Internet Archive snapshots of roughly forty NYT situation maps, 2016–2025,
  read through their ai2html text layer
- Amanda COX, interviewed in *Simply Statistics*, 1 June 2012
- Levi Westerveld, thread on NYT Ukraine map symbology, 22 March 2022
- Doug SPECHT and Alexander J. Kent, "How maps tell the story of war in
  Ukraine", *Geographical* (Royal Geographical Society), 1 April 2022
- James CHESHIRE and Alexander J. Kent, "Getting to the Point? Rethinking
  Arrows on Maps", *The Cartographic Journal*, 2023,
  doi:10.1080/00087041.2023.2178134
- The Conversation, "Maps show and hide key information about Ukraine war"
  and "How maps are used and abused in times of conflict"
- Tim Wallace, interviewed by GeoHipster, 15 January 2018, and by Wired,
  October 2014 (quoted in FlowingData, 24 October 2014)
- Datawrapper, "Fix my chart: Map annotations"; "New in locator maps:
  Point to locations & markers with callout lines"
- Yale Climate Connections on the 2026 cone-of-uncertainty redesign, and
  the 2022 Florida survey on cone misreadings
