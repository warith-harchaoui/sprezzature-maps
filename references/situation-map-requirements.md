# What a situation map owes a researcher

Written 2026-10-27, from the standpoint of somebody who would use these
plates in work that gets argued with: a conflict analyst, a desk officer, a
political geographer. The reference standard is the New York Times graphics
desk, with the Institute for the Study of War (ISW) for the evidence model
and the UNHCR mapping guidelines for the furniture.

The short version of the finding: **the renderer already implements most of
what is missing. No plate uses it.** Locator insets, the
assessed/claimed/reported distinction, per feature confidence, label tiering
and small multiples are all in `make_situation_map.py` and all unused by
`build_situation_examples.py`. The cheapest improvement available is not new
code.

| Capability | In the renderer | Used by a plate |
|---|---|---|
| `inset` (locator) | yes | no |
| `assessed` | yes | no |
| `claimed` | yes | no |
| `reported` | yes | no |
| `confidence` | yes | no |
| `tier` (label hierarchy) | yes | no |
| `small_multiples` | yes | no |
| `infrastructure` | yes | one plate |
| `internal_borders` | yes | one plate |

---

## 1. The questions a plate has to answer

A researcher looks at an areas-of-control map to settle one of five things.
Each one is a requirement.

**Who holds this ground, at what level of certainty?** The single most common
failure in conflict cartography is a flat fill that makes a claim and an
observation look identical.

**When was this true?** A control map without a date is a decoration. The
date belongs on the plate, not in the caption of the page that embeds it,
because the plate travels.

**What counts as control here?** Holding a town, passing through it and
shelling it are three different facts that one shade of red erases.

**What is the ground like?** Rivers, ridges and marsh decide where a front
can sit. The Dnieper is why the Kherson line held.

**What changed?** A single frame answers nothing about direction. Two frames
answer most of it.

---

## 2. The evidence model, which is the largest gap

ISW's published methodology is the standard to copy. It is a *data model*
before it is a drawing style. Its core distinction is between **assessed**
control and **claimed** control. The first rests on geolocated visual
evidence matched against satellite imagery; the second rests on a combatant
saying so. ISW also keeps a separate, deliberately more generous layer for
**infiltration**, with an explicitly lower evidentiary threshold for adding
ground than for taking it away. It uses the doctrinal definition of control
throughout, which requires physical influence over an area rather than
presence in it.

The renderer has `assessed`, `claimed` and `reported` already. What is
missing is the obligation to use them.

**Requirement E1.** Every control polygon carries an evidence class. The
schema should refuse a polygon that declares none, rather than defaulting to
a confident fill. A default of "assessed" is the dangerous one, because it is
the strongest claim.

**Requirement E2.** The three classes are visually ordered, so a reader
ranks them without the legend. Solid fill for assessed, hatched for claimed,
outline only for reported. The current plates hatch the contested band, which
is the right instinct applied to the wrong axis: hatching should encode
*confidence*, with contestation encoded by colour.

**Requirement E3.** Each polygon carries its own source and observation
date, rather than one date for the whole plate. A front assembled from six
sources over three weeks is normal. Saying so is what makes it usable.

**Requirement E4.** A `control_definition` field, stated on the plate in one
line. "Control" means something specific and the plate should say which.

---

## 3. Precision is a number, not an adjective

ACLED codes `geo_precision` 1 to 3 and `time_precision` 1 to 3, where 1 is
exact and 3 is "the region is all anybody knows". UCDP GED carries seven
values of `where_prec`. These are the standard vocabularies. A plate that
ingests either should keep the code rather than flatten it.

The package is already partly here: the Ukraine plate marks flashpoints with
`precision: 2` and draws them as a hollow ring rather than a dot, so the
uncertainty is in the ink. That instinct should become a rule.

**Requirement P1.** Point events carry ACLED or UCDP precision codes, with a
declared vocabulary. A ring for precision 2, a ring with a radius for
precision 3, a filled dot for precision 1.

**Requirement P2.** A point whose precision is 3 draws as an area, because
that is what it is. Drawing a province-level report as a dot in the middle of
the province invents a location.

**Requirement P3.** Time precision reaches the plate too. An event known only
to a week is not the same evidence as one known to an hour.

---

## 4. The furniture, which the UNHCR guidelines specify exactly

These are mandatory elements with numbers attached. All of them are cheap.

**Requirement F1. A locator inset.** The guidelines put a globe at 15mm on an
A5 plate and 20mm on A4, with 2mm margins, showing the mapped area in red. No
plate in this package has one. A reader who does not already know where the
Donbas is cannot place it.

**Requirement F2. A date stamp under the title**, in the form "as of DD Month
YYYY". The guidelines put it there; the current plates put the date in the
subtitle, where it competes with the editorial line.

**Requirement F3. A source and method line**, set small, at the foot. The
package does this already and does it well.

**Requirement F4. A disclaimer where one is owed.** The guidelines carry a
standard short form and long form in English, French and Spanish, plus named
special disclaimers for Jammu and Kashmir, for Sudan and South Sudan, for
Abyei.
A package that draws Kashmir without the Line of Control sentence is making a
political statement by omission.

**Requirement F5. A scale bar** at 2mm margins. Present already, in two units,
which is better than the standard asks.

---

## 5. Boundaries, which are where a map takes a side

Natural Earth draws de facto boundaries and ships the de jure claim lines as
a separate layer. The general convention is a solid line for a settled
boundary and a dashed line for one the neighbours disagree about.

**Requirement B1.** International boundaries, disputed boundaries and lines
of control are three styles, not one. Dashed for disputed, dotted for a line
of control, solid for settled.

**Requirement B2.** A disputed boundary carries the name of the dispute, so
the plate can be audited against a policy rather than against taste.

**Requirement B3.** The de jure claim line is available as an optional layer.
On a Crimea plate, the difference between the two lines is the subject.

---

## 6. Label hierarchy, which is most of what makes a NYT map look like one

The UNHCR examples show the hierarchy plainly: the mapped country in
letterspaced capitals at the largest size, neighbouring countries in grey
letterspaced capitals, first level administrative names in grey capitals at a
smaller size, settlements in sentence case with a symbol, the capital with a
distinct symbol, water bodies in blue italic.

The renderer has `tier` and no plate uses it.

**Requirement L1.** Four settlement tiers by population, with size, weight
and symbol varying together. A city of two million and a village should not
share a type size.

**Requirement L2.** Label suppression by zoom. A plate that fits every name
it knows is a plate nobody reads.

**Requirement L3.** Halos on every label that crosses a fill. The current
plates do this.

**Requirement L4.** Collision detection with a stated policy for what loses.
A settlement label should beat a river label; a flashpoint ring should beat
both.

---

## 7. Terrain, because it explains the front

The package already carries GMTED2010 relief and draws it well. What is
missing is the military reading of it.

**Requirement T1.** Rivers classed by whether they are crossable, which is a
function of width and season rather than of name.

**Requirement T2.** An optional slope layer, because a ridge line and a
contour are different arguments.

**Requirement T3.** Marsh and flood extent as a seasonal layer. The Kakhovka
drainage is already handled on the Ukraine plate, thoughtfully;
the generalisation is a `former` and `seasonal` state for any water body.

---

## 8. Change over time, which is the question a single frame cannot answer

`small_multiples` is implemented and unused.

**Requirement C1.** Two or three frames on one plate, same projection, same
extent, with the dates in the frame. This is the NYT house move and it
carries more than any arrow.

**Requirement C2.** A difference layer: ground gained, ground lost, ground
unchanged, over a stated interval. Gains and losses are different colours,
and the interval is on the plate.

**Requirement C3.** Arrows are refused by default. Early Ukraine maps used
large arrows and read as a blitzkrieg that was not happening; the NYT moved
away from block gains towards showing fluidity for exactly this reason. An
arrow asserts intent, momentum and success at once, while evidencing none
of the three.

---

## 9. Data I would need, with licences

| Layer | Source | Licence |
|---|---|---|
| Small scale basemap | Natural Earth | public domain |
| Administrative boundaries, humanitarian standard | OCHA Common Operational Datasets | varies, usually open |
| Administrative boundaries, open | geoBoundaries | CC BY |
| Conflict events | ACLED | free for non-commercial, attribution and registration |
| Conflict events, academic | UCDP GED | CC BY |
| Terrain | GMTED2010, Copernicus DEM | public domain, open |
| Roads, rail, ports, airfields | OpenStreetMap | ODbL, share-alike, which infects derived data |
| Population | WorldPop, GHSL | CC BY |
| Damage assessment | UNOSAT, Copernicus EMS | varies |
| Areas of control | ISW, no machine readable feed | non-commercial reuse with attribution |

Two things to flag for a package that ships figures.

**The OpenStreetMap share-alike does not reach the SVG, and this package
already knew that.** The first draft of this document said that shipping an
SVG with an OSM layer puts the ODbL on the output. That is wrong. ODbL
distinguishes a *Derivative Database* from a *Produced Work*: share-alike
binds the first, a rendered map is the second, and a produced work may carry
any licence its author likes. What is owed is attribution.

`make_situation_map.py` had this right before the question was asked. Its
vendoring note states the distinction in those terms, `_attribution_layer`
adds "© OpenStreetMap contributors (ODbL)" automatically whenever an OSM
layer would actually draw for the given bounding box rather than leaving it
for a caller to remember, and `test_attribution_layer_only_credits_osm_when_in_view`
checks both directions: the credit appears inside the covered bounds and
stays absent outside them.

So the requirement is discharged, and the remaining obligation is narrow. The
three vendored admin-1 extracts *are* derivative databases, so those files
carry ODbL themselves. The plates do not.

**No open, machine readable, daily areas-of-control feed exists.** ISW
publishes maps rather than data. Any plate claiming current positions is
either hand built from reporting, which is what the package honestly says it
does today, or scraped from somebody else's rendering, which is worse. This
is the single hardest requirement and the honest answer is to keep saying
"schematic, hand drawn from open source reporting" in the method line.

---

## 10. Priority

**First, use what exists.** Locator inset, evidence classes, label tiers on
the six shipped plates. That takes no new code. It closes the largest gap
between these plates and a NYT one.

**Second, make the evidence model compulsory.** A polygon with no evidence
class should fail the schema rather than render confidently.

**Third, the two frame plate.** Change over time is the question a researcher
actually brings. `small_multiples` is already written.

**Fourth, boundaries and disclaimers as policy.** Three line styles, the
named special disclaimers, the de jure layer.

**Fifth, the terrain reading.** Crossable rivers, slope, seasonal water.

---

## Sources

- Institute for the Study of War, cartographic methodology for the Russian
  invasion of Ukraine
- UNHCR Mapping Guidelines, February 2024
- ACLED Codebook, `geo_precision` and `time_precision`
- UCDP Georeferenced Event Dataset Codebook, `where_prec`
- Natural Earth disputed boundaries policy
