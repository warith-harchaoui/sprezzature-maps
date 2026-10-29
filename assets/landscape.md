# Tools in the Quadrant

## Axes

- **Horizontal: Robustness ↔ Usability** — ~36% of the variance
- **Vertical: Dynamism ↔ Clarity** — ~20% of the variance

In two axes, we preserved ~56% of the information in the table.

## Analysis

The map reveals a fundamental tension between ease of use and the ability to handle complex data and workflows. Options clustered on the left side prioritize robustness, often at the expense of immediate accessibility; features like handling large datasets and a mature ecosystem contribute to this positioning. Conversely, those on the right emphasize usability, making it easier for a wider range of users to create and share maps, though potentially with limitations in scope. The leader, *sprezzature-maps*, occupies the top-right corner, demonstrating a strong balance of both qualities, but several others, like *ArcGIS Pro*, also achieve this combination.

A large group of tools – including *D3 + d3-geo*, *GeoPandas*, *PyGMT*, *Vega-Lite / Altair*, *QGIS*, *tmap (R)*, and *mapsf (R)* – share the top-left corner, indicating a focus on robustness and clarity. These options often require more technical expertise to utilize but offer considerable power and control.  At the opposite end, a collection of tools – *Highmaps*, *Datawrapper*, *Flourish*, *Felt*, and *CARTO* – are grouped in the bottom-right, prioritizing dynamic visuals and ease of use, though perhaps sacrificing some of the depth and control found elsewhere. 

Interestingly, *sprezzature-maps* leads in usability, but not in robustness. Several options, like *Folium / Leaflet*, *Mapbox GL JS*, *OpenLayers*, *deck.gl*, *kepler.gl*, *Plotly maps*, and *Protomaps / PMTiles*, are robust but less usable, and are grouped in the bottom-left. This suggests a trade-off is often necessary when choosing a mapping tool, and the ideal choice depends heavily on the specific project requirements and the skillset of the intended user.
