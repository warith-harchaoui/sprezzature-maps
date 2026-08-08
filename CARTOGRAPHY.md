# Cartography methodology

This document is the technical record of how `sprezzature-maps` draws a
map: which projections, which color spaces, which terrain-shading
algorithm, which vendored datasets, and why each choice was made over the
available alternatives. It exists so that a reader (including a future
maintainer of this repository) can reconstruct every rendering decision
from first principles, not just read that a decision was made.

Two generators are covered: `choropleth` (`scripts/make_choropleth.py`,
world scale, per-country fill) and `situation_map`
(`scripts/make_situation_map.py`, regional scale, an auto-centered
layered plate). Both are hand-authored SVG: no charting library, no
raster renderer, no `matplotlib`. Formulas are given in full so the
source files' own docstrings (already extensive) do not have to be
read to follow the reasoning; code references point back to the exact
function for a reader who wants the implementation, not just the theory.

Compiled to `.docx`/`.pdf` with [md2star](https://github.com/warith-harchaoui/md2star):

```bash
md2docx CARTOGRAPHY.md --author "Warith Harchaoui" \
    --bib assets/references.bib --bibliography-name "References"
md2pdf CARTOGRAPHY.md --author "Warith Harchaoui" --bib assets/references.bib
```

## Contents

1. [World scale: choropleth](#world-scale-choropleth)
2. [Regional scale: situation_map](#regional-scale-situation_map)
3. [Terrain shading (shared machinery)](#terrain-shading-shared-machinery)
4. [Data provenance and licensing](#data-provenance-and-licensing)
5. [Storage: the vendored-raster pyramid and Git LFS](#storage-the-vendored-raster-pyramid-and-git-lfs)
6. [Validation methodology](#validation-methodology)
7. [Roadmap](#roadmap)

---

## World scale: choropleth

### Equal Earth projection

A world choropleth encodes a quantity in each country's fill color, so
the *area* the projection assigns to a country is not decorative: a
projection that inflates high-latitude land (the classic failure of
Mercator, and, less obviously, of a plain equirectangular grid, which
inflates Greenland to roughly fourteen times its true relative size on
this dataset) visually overweights whatever that inflated country's
value happens to be. The fix is an *equal-area* projection: one where
every region's projected area is proportional to its true area on the
sphere, by construction.

`choropleth` uses Equal Earth [@savric-equal-earth], a pseudocylindrical
equal-area projection published in 2018 as a deliberately more
visually balanced alternative to the older Mollweide and Robinson
projections (Robinson, for reference, is not equal-area at all; Equal
Earth was designed to keep Robinson's pleasant continental proportions
while actually holding the equal-area guarantee Robinson lacks). It has
a closed-form forward projection with published polynomial constants,
no iteration required.

Forward projection, longitude $\lambda$ and latitude $\varphi$ in
radians:

$$
\theta = \arcsin\!\left(\frac{\sqrt{3}}{2}\sin\varphi\right)
$$

$$
x = \frac{\lambda \cos\theta}{\dfrac{\sqrt3}{2}\left(A_1 + 3A_2\theta^2 + \theta^6\left(7A_3 + 9A_4\theta^2\right)\right)}
$$

$$
y = \theta\left(A_1 + A_2\theta^2 + \theta^6\left(A_3 + A_4\theta^2\right)\right)
$$

with the published constants $A_1 = 1.340264$, $A_2 = -0.081106$,
$A_3 = 0.000893$, $A_4 = 0.003796$. Implemented verbatim in
`_equal_earth_raw` (`scripts/make_choropleth.py:77`). The projected
point cloud's bounding box is fit to the canvas with a single uniform
scale factor, never independent horizontal/vertical stretch, since an
anisotropic stretch would undo the equal-area property the whole
projection was chosen for.

Equal Earth has no closed-form inverse: $y(\theta)$ is a degree-nine odd
polynomial with no algebraic root formula. The relief layer (below)
needs the inverse, to know which real-world (lon, lat) sits under a
given canvas pixel, so `_equal_earth_invert_batch`
(`scripts/make_choropleth.py:97`) recovers $\theta$ by Newton-Raphson on

$$
f(\theta) = \theta\left(A_1 + A_2\theta^2 + \theta^6\left(A_3 + A_4\theta^2\right)\right) - y_{\text{target}} = 0,
$$

started from the small-angle linear approximation $\theta_0 = y / A_1$
(exact at $\theta = 0$, and close enough over Equal Earth's whole valid
range, $|\theta| \lesssim 65°$, that twelve Newton iterations converge
to float64 precision). Longitude then falls out of the forward $x$
formula solved for $\lambda$ at the now-known $\theta$; latitude from
inverting $\theta = \arcsin\!\left(\tfrac{\sqrt3}{2}\sin\varphi\right)$.
Country outlines themselves never need this: they are drawn forward,
from known vertices, so only the relief raster's per-pixel sampling
uses the inverse.

### Perceptually uniform color: OKLab / OKLCH

A choropleth's fill color is the whole message, so the color ramp has
to satisfy a property naive RGB interpolation does not: equal numeric
steps in the data should read as equal *perceived* steps in color, and
a ramp's midpoint should not accidentally pass through a muddy,
desaturated grey-brown that reads as "no data" rather than "the middle
value." Interpolating in raw sRGB fails both. Interpolating in OKLab /
OKLCH (Oklab, a perceptual color space published by Björn Ottosson in
2020 [@ottosson-oklab]; OKLCH is the same space in cylindrical
lightness/chroma/hue form) fixes both, at the cost of a heavier
per-color conversion chain, which is cheap here since ramps are
pre-baked into small lookup tables (256 entries), not evaluated
per-pixel at render time.

The forward chain, `_geo_colors.py` (`scripts/_geo_colors.py`):

1. **sRGB (8-bit) → linear light**, undoing the sRGB transfer function
   (`_srgb_to_linear`).
2. **Linear sRGB → an LMS-like cone-response space**, Ottosson's
   published $3\times3$ matrix:

$$
\begin{pmatrix}l\\m\\s\end{pmatrix} =
\begin{pmatrix}
0.4122214708 & 0.5363325363 & 0.0514459929\\
0.2119034982 & 0.6806995451 & 0.1073969566\\
0.0883024619 & 0.2817188376 & 0.6299787005
\end{pmatrix}
\begin{pmatrix}r\\g\\b\end{pmatrix}_{\text{linear}}
$$

3. **Signed cube root** of each cone response (sign preserved, not
   discarded, since saturated or out-of-gamut colors can produce a
   negative cone response).
4. **Cube-rooted cone space → OKLab** $(L, a, b)$, a second published
   matrix:

$$
\begin{pmatrix}L\\a\\b\end{pmatrix} =
\begin{pmatrix}
0.2104542553 & 0.7936177850 & -0.0040720468\\
1.9779984951 & -2.4285922050 & 0.4505937099\\
0.0259040371 & 0.7827717662 & -0.8086757660
\end{pmatrix}
\begin{pmatrix}l'\\m'\\s'\end{pmatrix}
$$

5. **OKLab → OKLCH**: $C = \sqrt{a^2+b^2}$, $H = \operatorname{atan2}(b, a)$.

Both matrices are inverted exactly (`_oklab_to_linear`,
`scripts/_geo_colors.py:266`) to go back from OKLCH to a hex color once
a ramp stop has been interpolated. Interpolation itself
(`_interpolate_oklch_hex`, `scripts/_geo_colors.py:424`) treats the
three OKLCH channels differently: lightness $L$ and chroma $C$ lerp
linearly, hue $H$ lerps along the *shorter* arc around the color wheel
(so 350° and 10° blend through 0°, not through 180°), and a chroma
threshold ($C < 0.01$) guards against interpolating hue through a
near-achromatic endpoint. That guard is not a theoretical nicety: an
early version of the diverging ramp, terracotta fading to a neutral
grey, read visibly mauve/pink at its midpoint, because `atan2` on two
near-zero numbers returns a noisy, essentially arbitrary hue, and
interpolating *through* that noise pulled the midpoint off-course. The
fix carries the non-grey endpoint's real hue across the whole
near-achromatic segment instead of trusting the noise.

Two ramp shapes are built on top of this primitive:
`sequential_ramp_hex` (pale to navy blue, for magnitude) and
`diverging_ramp_hex` (auto-detects a signed range and picks a
below-zero / above-zero color pair around a neutral midpoint). Every
ramp actually shipped is verified, not merely asserted, against three
kinds of color-vision deficiency (protanopia, deuteranopia,
tritanopia) via `simulate_cvd_hex` (`scripts/_geo_colors.py:627`),
which applies the physiologically derived confusion-line matrices of
Machado, Oliveira and Fernandes [@machado-cvd], and against the WCAG
contrast-ratio formula via `wcag_contrast_ratio`
(`scripts/_geo_colors.py:665`), so a ramp that reads as *technically*
distinct in full color but collapses to two indistinguishable greys
under deuteranopia is caught before it ships, not discovered by a
color-blind reader later.

*Figures 1a and 1b: the sequential ramp (min/median/max magnitude) and
the auto-detected diverging ramp on the same underlying dataset.*

![Choropleth, sequential ramp](web/img/choropleth-sequential.png)

![Choropleth, diverging ramp](web/img/choropleth-diverging.png)

*Figure 1c: the verification claim above, shown rather than asserted.
The shipped diverging ramp, swept end to end, under normal vision and
each of the three simulated color-vision deficiencies. The negative
(terracotta) and positive (navy) extremes stay distinguishable in every
row; only the hue identity of the extremes shifts, never their
separability from the neutral midpoint.*

![CVD simulation of the diverging ramp](web/img/cvd-simulation-diverging.png)

### Boundaries: Natural Earth and TopoJSON

Country outlines come from Natural Earth [@natural-earth], a public
domain vector/raster atlas published at three fixed scales
(1:110m, 1:50m, 1:10m; the number is the map scale the detail level was
drawn for, not a pixel count). `choropleth` uses the 1:50m tier
(`assets/geo/countries-50m.json`); `situation_map`'s tiering is
described below.

The vendored files are TopoJSON, not GeoJSON: a topology-preserving
format that stores shared borders once as reusable *arcs* rather than
once per adjacent polygon, and quantizes each arc's points to
successive integer deltas rather than raw floating-point coordinates,
which is most of why a TopoJSON file is smaller than the equivalent
GeoJSON [@bostock-topojson]. Decoding an arc (`_decode_topojson_object`,
`scripts/make_situation_map.py:140`) walks a topology's own
`scale`/`translate` transform:

$$
x_i = \left(\sum_{k=0}^{i} \delta x_k\right) s_x + t_x, \qquad
y_i = \left(\sum_{k=0}^{i} \delta y_k\right) s_y + t_y
$$

A negative arc index means "walk this arc reversed" (bitwise
complement, `~index`, recovers the real index), the encoding TopoJSON
uses so a shared border can be referenced forward by one polygon and
backward by its neighbor without duplicating the coordinates. Natural
Earth's individual country polygons are occasionally self-touching
(topologically invalid in the strict OGC sense); each is repaired with
Shapely's `make_valid` before use rather than risking a fragile
whole-world union.

### World relief

A faint terrain texture sits under the vector layers so the map reads
as "a real planet," not a flat color diagram. World scale uses a
different, cheaper technique than the regional path below: a
pre-rendered greyscale raster (`assets/geo/relief-lowres.png`, a
1440×720 downsample of Natural Earth's public-domain "Gray Earth"
shaded relief), reprojected by bilinearly sampling it at the (lon, lat)
the Equal Earth inverse recovers for each canvas pixel
(`sample_relief`, `scripts/_relief.py:194`), then retinted through a
warm/cool duotone lookup table rather than left as literal grey. That
retinting is Eduard Imhof's "warm highlights, cool shadows" convention
[@imhof-relief]: low shade values (shadowed terrain) map toward a cool
blue-slate, high values (sunlit ridgelines) toward a warm pale cream,
interpolated through OKLCH for the same reason the choropleth ramps
are. A contrast stretch runs before the duotone lookup, because the
raw raster rarely spans its own full 0-255 range in any single crop
(flat ocean sits at a fixed baseline near 146; even the Himalaya only
reaches roughly 90-245 in the vendored source), and feeding that narrow
band directly into the duotone LUT wastes most of the LUT's contrast on
values the data never actually reaches.

Why not the regional path's real-elevation technique here too: a
world-scale crop is too large to run the FFT-based technique below at
interactive cost, and the fine multi-scale texture it adds would be
invisible at world zoom regardless.

*Figure 1d: the same Alps-arc crop of the vendored world raster, plain
contrast-stretched greyscale next to the shipped Imhof-style duotone.
The duotone version is not just recolored, it reads with more apparent
depth at the same contrast, because the cool-shadow/warm-highlight
split gives the eye a second cue (hue) on top of lightness alone.*

![Plain greyscale vs. Imhof duotone](web/img/relief-duotone-comparison.png)

---

## Regional scale: situation_map

### Lambert Conformal Conic, auto-centered

A regional plate (a single country, or a handful of neighboring ones)
needs the opposite property from a world choropleth: not equal area,
but *conformality*, true local shape and angle, since a viewer reading
a province-level map judges distances and directions locally, not by
comparing total colored area against another country on the far side
of the globe. `situation_map` uses the Lambert Conformal Conic (LCC)
projection, auto-centered on the requested bounding box
(`build_projection`, `scripts/make_situation_map.py:371`):

$$
\lambda_0 = \frac{w+e}{2}, \qquad \varphi_0 = \frac{s+n}{2}, \qquad
\varphi_1 = s + \frac{n-s}{6}, \qquad \varphi_2 = n - \frac{n-s}{6}
$$

for a bounding box $[w, s, e, n]$ (west, south, east, north, degrees).
The two standard parallels $\varphi_1, \varphi_2$ at the one-sixth and
five-sixths latitudes are the classic rule of thumb for an LCC's
standard parallels: placing them a sixth of the way in from each edge,
rather than at the edges themselves, keeps the scale distortion between
the parallels and at the region's own edges comparably small, instead
of concentrating all the error at the top and bottom. The actual
forward/inverse math is delegated to PROJ [@proj] through `pyproj`'s
`Transformer`, not reimplemented: LCC's own formulas (a true conic
projection, unlike Equal Earth's pseudocylindrical family) are well
established and PROJ's implementation is the reference one, so
reimplementing it here would add risk without adding anything Equal
Earth's from-scratch treatment above did not already have covered
(that projection required custom code specifically because Equal Earth
is new enough, 2018, that PROJ's forward LCC support long predates it
and there was no equivalent reference implementation to defer to for
the inverse).

*Figures 2a-2c: three regions at different scales, same generator, same
projection family, auto-centered independently for each.*

![Situation map, Switzerland](web/img/situation-switzerland.png)

![Situation map, Iberia](web/img/situation-iberia.png)

![Situation map, Western Europe](web/img/situation-western-europe.png)

### Boundary tiering

Loading the full 1:10m Natural Earth tier for a whole-continent view
spends detail the output cannot show (individual harbor inlets are
sub-pixel at that zoom) for real cost (a heavier download, slower
decode, slower Shapely operations on more numerous points). Loading
only the coarser 1:50m tier for a single small country, conversely,
visibly under-resolves it: coastlines and small administrative
boundaries read as faceted rather than smooth once a country fills
most of the canvas. `_land_topojson_for_bbox`
(`scripts/make_situation_map.py:101`) picks between the two
algorithmically, on the bounding box's own angular span:

$$
\text{tier} =
\begin{cases}
\text{1:10m} & \max(e-w,\, n-s) < 25° \\
\text{1:50m} & \text{otherwise}
\end{cases}
$$

25° was chosen as roughly "a single country or small cluster of
neighbors, not a subcontinent": Iberia (Spain + Portugal, spanning
about 13° of longitude) and Switzerland (spanning under 3°) both
resolve to the finer tier; Western Europe (spanning roughly 41°,
Ireland to Poland) resolves to the coarser one, where the visible
gain from finer coastline detail would not survive the render's own
pixel density regardless.

### Regional relief

Regional scale replaces the world path's pre-rendered raster with a
technique computed from real elevation data, described in full in the
next section, since it is shared machinery rather than specific to
either generator.

---

## Terrain shading (shared machinery)

`scripts/_relief.py`'s elevation-based path (as distinct from the
world-scale `sample_relief` path above) computes terrain shading from
GMTED2010 [@danielson-gmted2010], the USGS/NGA's public domain global
elevation model, at its finest published grid spacing: 30 arc-seconds
(roughly 925 meters per pixel at the equator; an arc-second is
$1/3600$ of a degree of latitude or longitude). Two shading techniques
are combined, because each covers exactly what the other misses.

**Hillshade** is the familiar technique: a single directional light
source (here, northwest azimuth $315°$, altitude $45°$ above the
horizon) lights a surface derived from the elevation grid's own local
gradient. Slope and aspect at each cell:

$$
\text{slope} = \arctan\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}, \qquad
\text{aspect} = \operatorname{atan2}\!\left(\frac{\partial z}{\partial y}, -\frac{\partial z}{\partial x}\right)
$$

with the gradients taken in real metres (longitude spacing is
converted with a $\cos(\text{latitude})$ correction, since a degree of
longitude shrinks toward the poles while a degree of latitude does
not, and multiplied by a deliberate vertical exaggeration factor,
$2\times$ by default; see "Relief exaggeration strategies" below for
why). The Lambertian shading equation itself:

$$
\text{hillshade} = \operatorname{clip}\Big(\sin(\text{alt})\cos(\text{slope}) + \cos(\text{alt})\sin(\text{slope})\cos(\text{az} - \text{aspect}),\; 0,\; 1\Big)
$$

Hillshade alone supplies believable overall lighting, and nothing
else: it is scale-blind to structure much smaller than the light and
shadow transition itself, so fine ridgelines and drainage networks
within a single lit or shadowed face wash out.

**Texture shading** [@brown-texture-shading] fills exactly that gap.
(Certainty note: Brown's technique was first circulated at the 2010
NACIS cartography conference and formally published at the 2014 ICA
Mountain Cartography Workshop; both dates are given in the
bibliography entry since the earlier one is the technique's real
origin but the later one is what has a citable paper.) It is a
fractional-order Laplacian applied in the frequency domain: Fourier
transform the elevation grid, multiply by the frequency magnitude
raised to a fractional power, inverse transform.

$$
T(x,y) = \mathcal{F}^{-1}\Big[\mathcal{F}[z(x,y)] \cdot |\mathbf{f}|^{\alpha}\Big](x,y), \qquad \alpha = 0.5
$$

with $|\mathbf{f}| = \sqrt{f_x^2+f_y^2}$ the spatial-frequency
magnitude and $\alpha$ in Brown's suggested natural-looking range of
$0.4$ to $0.6$ (implemented at $\alpha=0.5$,
`_compute_terrain_shade`, `scripts/_relief.py:575`). Because this
operator scales the whole frequency spectrum by the same power law
rather than isolating one band, it draws out ridge and drainage
structure at *every* scale simultaneously, which is precisely what
gives texture-shaded relief its engraved, almost etched appearance
compared to a plain lit hillshade. A Hann window is applied to the
elevation crop before the transform, to avoid the ringing a sharp
rectangular crop edge would otherwise inject as spurious high-frequency
content; the crop itself is padded 15% beyond the region actually
needed so that window's own edge fade-out lands in a margin that gets
cropped away before reprojection, not inside the visible map.

The two are blended $0.35 \times \text{hillshade} + 0.65 \times
\text{texture}$ (texture-shading output is unbounded and scale-free,
unlike hillshade's physical $[0,1]$ range, so it is renormalized around
its own standard deviation before blending). That specific ratio, and
the choice to run texture shading at all rather than ship hillshade
alone, was not settled by theory: it was calibrated by direct visual
comparison against editorial, New York Times-style relief cartography
(the print-map house style this project takes its visual cues from)
until the output matched, the Ralph Eyeball Loop described below. The resulting
shade grid is retinted through the same Imhof-style OKLCH duotone
lookup table the world-scale path uses (`_duotone_lut`,
`scripts/_relief.py:133`), so both generators share one visual
language for relief even though they compute it two different ways.

*Figure 3: regional relief on genuinely varied terrain (Himalaya),
where hillshade alone would show the overall light/dark massif but
texture shading is what resolves individual ridgelines within it.*

![Situation map, Himalaya relief](web/img/situation-himalaya.png)

### Relief exaggeration strategies

A perfectly literal, physically accurate render of GMTED2010's real
elevation values would look almost flat. Even the Himalaya, the most
dramatic terrain this dataset has, spans roughly 8800 metres of relief
across hundreds of kilometres: a slope so gentle in true proportion
that a photorealistic light simulation of it reads as a faint grey
haze, not a mountain range. Every relief cartographer's toolkit
therefore includes deliberate departures from physical literalness,
chosen to make the terrain *legible* rather than to simulate a camera.
`_compute_terrain_shade` (`scripts/_relief.py:576`) exposes three such
departures as named parameters
(`vertical_exaggeration`, `texture_alpha`, `hillshade_weight`,
each with a shipped default:
`DEFAULT_VERTICAL_EXAGGERATION = 2.0`,
`DEFAULT_TEXTURE_ALPHA = 0.5`, `DEFAULT_HILLSHADE_WEIGHT = 0.35`,
`scripts/_relief.py:575`), so the same production code path used for
every real render can also produce the comparison figures below,
rather than a separate script re-implementing the algorithm at
different settings.

**Vertical exaggeration** is the oldest and most literal strategy:
multiply the elevation gradient by a constant before it becomes a
hillshade slope angle, so the same light source casts a harder,
more legible shadow than the true slope would produce. It is a
*spatial-domain* exaggeration, applied uniformly to the whole
gradient regardless of the terrain feature's own size.

*Figure 4: the same Everest-massif crop, hillshade only (texture
shading weight zero, isolating this one variable), at true scale
versus the shipped $2\times$ default. Ridgelines that are barely
readable at true scale separate cleanly at the shipped setting,
without yet introducing any of texture shading's own contribution.*

![Vertical exaggeration comparison](web/img/relief-exaggeration-vertical.png)

**Texture shading's fractional order** $\alpha$ (introduced in the
formula above) is a different kind of exaggeration: not spatial but
*spectral*. Instead of stretching every gradient by the same factor
regardless of the feature size it belongs to, it boosts every spatial
frequency of the elevation field by the same power law at once, so a
tiny side-valley's drainage pattern is exaggerated by the same
proportional amount as the main massif's ridgeline, rather than being
swamped by it. This is what lets texture shading resolve structure
*within* a single hillshade-lit face that vertical exaggeration alone
cannot touch, since a spatial gradient stretch cannot separate "this
pixel is on a ridge" from "this pixel is on a valley wall" once both
already fall on the same broad lit slope.

**The blend weight** between the two is the third strategy, and the
one that determines whether the final image reads as a lit photograph
or an engraved diagram. Hillshade alone is the physically motivated,
photograph-like extreme; texture shading alone is the abstract,
frequency-only extreme, which on its own looks more like a printed
circuit board than a mountain, since it discards the overall light and
dark massif shape that only hillshade's directional lighting supplies.
The shipped $0.35/0.65$ split sits deliberately close to the texture
end without discarding hillshade's contribution entirely.

*Figure 5: the same crop decomposed into its two ingredients and their
shipped blend. Hillshade only supplies a believable overall lit
surface but reads soft; texture shading only supplies extraordinary
fine detail but reads abstract, closer to an X-ray than a mountain;
the shipped blend keeps hillshade's photographic legibility while
letting texture shading's drainage-network detail read through it,
which is the combination this project's whole relief system was built
to reach.*

![Hillshade, texture shading, and blend comparison](web/img/relief-exaggeration-blend.png)

Regenerable in one command, against the real vendored elevation data,
whenever any of the three defaults changes:

```bash
python scripts/build_relief_exaggeration_figures.py
```

The world-scale path (`sample_relief`, above) has no elevation grid to
apply a vertical or spectral exaggeration to, since it works from a
single pre-shaded raster, not raw elevation. Its analogous exaggeration
strategy is purely tonal: the contrast stretch described earlier
(`_SHADE_STRETCH_LOW`/`_SHADE_STRETCH_HIGH`, `scripts/_relief.py:113`)
remaps whatever narrow grey-value range a given crop actually occupies
back out to the duotone lookup table's full contrast range, the same
underlying goal (make faint real terrain read clearly) reached through
the one lever a pre-rendered raster leaves available.

### Elevation pyramid and algorithmic tier selection

The finest GMTED2010 tier is a 902-million-pixel grid (about 237 MB as
a 16-bit PNG); loading it for every render, including a whole-continent
view where individual valleys are sub-pixel anyway, spends real time
and memory on detail the output cannot show. `select_elevation_tier`
(`scripts/_relief.py:388`) picks the coarsest of six mipmap-style
pyramid tiers (30 arc-seconds down to 16 arc-minutes, each an exact
$2\times2$ block-average of the tier above it, so the levels stay
mutually consistent rather than being independently resampled from the
source) that still comfortably resolves the requested render:

$$
\Delta_{\text{out}} = \min\!\left(\frac{e-w}{\,w_{\text{px}}\,},\ \frac{n-s}{\,h_{\text{px}}\,}\right), \qquad
\Delta_{\text{budget}} = \frac{\Delta_{\text{out}}}{k}
$$

where $\Delta_{\text{out}}$ is the render's own angular resolution
(degrees per output pixel, taking the more demanding of the two axes),
$k$ is an oversample factor (default $2.0$), and the chosen tier is the
coarsest one whose own pixel spacing (in degrees) is still
$\le \Delta_{\text{budget}}$. Oversampling beyond a literal 1:1 pixel
match matters specifically because texture shading draws out fractal
structure below the output's own pixel size, which then anti-aliases
into the final bilinearly-resampled image; a tier that only just
matches output resolution measurably softens the result, which is
exactly what an earlier, single-fixed-tier version of this system
showed on inspection. The oversample factor of $2.0$ was calibrated
against the same three regions used throughout this document: at that
setting, Iberia and Switzerland's actual bounding boxes still resolve
to the finest 30 arc-second tier, matching what visual comparison
against the editorial reference cartography above showed was needed,
while Western Europe's much larger bounding box drops to 1 arc-minute
with no visible loss at that render scale.

---

## Data provenance and licensing

| Dataset | Source | License | Used by |
|---|---|---|---|
| Country/coastline boundaries (110m/50m/10m) | Natural Earth [@natural-earth] | Public domain | Both generators |
| World relief raster | Natural Earth "Gray Earth" | Public domain | `choropleth` |
| Global elevation grid (GMTED2010, 30 arc-sec) | USGS/NGA [@danielson-gmted2010] | Public domain (U.S. Government work) | `situation_map` |
| Rivers/lake centerlines (1:50m) | Natural Earth | Public domain | `situation_map` |

No dataset in this table requires attribution to use, though Natural
Earth's own suggested short citation ("Made with Natural Earth") is
honored here regardless, since it costs nothing and the map format is
already citing everything else. Nothing currently vendored carries a
share-alike or attribution-required license (OpenStreetMap-derived
data, ODbL, would be the first such case if added; see Roadmap).

---

## Storage: the vendored-raster pyramid and Git LFS

Every raster asset this document describes (`relief-lowres.png`, the
six-tier `elevation-*.png` pyramid) is vendored in the repository
rather than fetched at render time, so a render is reproducible offline
and does not depend on a third-party host staying up. Because these
files range from a few hundred kilobytes to 237 MB, they are tracked
with Git LFS rather than committed as ordinary blobs, via a single
`assets/geo/*.png filter=lfs diff=lfs merge=lfs -text` rule in
`.gitattributes`, so the main repository history stays small and a
clone only pulls the actual raster bytes when they are checked out
(or explicitly fetched). The same pattern (vendor once, keep a
lightweight pyramid of derived tiers, pick a tier algorithmically at
render time rather than by a hardcoded choice) is intended to extend to
boundary data too; see Roadmap.

---

## Validation methodology

Every relief and color change described above went through what this
project calls the Ralph Eyeball Loop: render, inspect the actual PNG
output (not just check that the code ran without raising), critique
against a concrete target (a reference image, or a specific defect like
visible blockiness or a muddy ramp midpoint), edit the source, and
render again, never editing the output image directly. Two smaller
mechanical checks back this at the code level: every public function in
`scripts/_relief.py` and `scripts/_geo_colors.py` carries a doctest
exercising its documented contract (`python -m doctest scripts/_relief.py`,
`scripts/_geo_colors.py`), and the full suite
(`pytest -q`) additionally covers the CLI, HTTP API, and MCP surfaces
end to end. Neither check catches a visually wrong result on its own
(a hillshade that runs without error and returns the right array shape
can still look flat); the Ralph Eyeball Loop is what catches that
category of defect, and the doctest/pytest layer is what keeps a
later refactor (the tier-selection rewrite described above, for one)
from silently breaking a contract the eyeball pass already validated.

---

## Roadmap

Two items are explicitly planned but not yet implemented, listed here
rather than left silently absent, per the principle that a document
like this should mark what is done and what is not with the same
explicitness:

- **OpenStreetMap-derived boundaries, plus national high-precision
  sources (IGN for France, TIGER for the United States).** These would
  sit *above* Natural Earth's 1:10m tier in precision, the same way the
  elevation pyramid's finest tier sits above its coarsest: a fourth
  boundary tier for renders zoomed in far enough to need
  sub-1:10m-scale accuracy. Unlike every dataset in the provenance
  table above, OpenStreetMap data is ODbL-licensed (share-alike,
  attribution-required), which is a real licensing change for this
  repository's data policy, not just a new file to vendor; IGN and
  TIGER each have their own separate licensing and file-format
  particulars (IGN's BD TOPO, TIGER/Line shapefiles) still to be
  worked through.
- **Applying this document's storage pattern (vendor once, keep a
  multi-resolution pyramid, pick a tier algorithmically at render
  time) to boundary data**, generalizing what `_land_topojson_for_bbox`
  already does with two tiers (50m/10m) and what
  `select_elevation_tier` does with six, into one consistent mechanism
  covering both vector and raster assets.
