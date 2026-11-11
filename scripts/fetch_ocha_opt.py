#!/usr/bin/env python3
"""Fetch OCHA oPt's current layers for the Israel / Palestine plates.

Author: Warith HARCHAOUI

The plate of today draws what the UN Office for the Coordination of
Humanitarian Affairs in the occupied Palestinian territory maps on its own
server: the West Bank and Gaza outline, the Oslo areas A, B and C, Israeli
settlements, and in Gaza the area under Israeli military presence and the
"yellow line" of the October 2025 ceasefire. The layers declare no licence
(``licenseInfo`` empty); they are used here, credited "© OCHA oPt" on the
plate, at Warith's decision of 2026-11-11.

The Oslo areas are taken from this server and not from the HDX file
"Oslo Agreement in the West Bank": that one labels Area B as a second
Area A and has no class B at all.

    python scripts/fetch_ocha_opt.py

writes ``assets/historical-extents/ocha-<layer>.geojson``, simplified to
about 50 m, each feature carrying ``source`` and ``as_of``.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape

SERVER = "https://gis.unocha.org/server/rest/services/Hosted"
OUT = Path(__file__).resolve().parents[1] / "assets" / "historical-extents"
TOLERANCE = 0.0005

#: name -> (service path, the date OCHA gives the layer, the property to keep)
LAYERS: dict[str, tuple[str, str, str]] = {
    "wb-gaza": ("PalestineGroupLayers1/FeatureServer/25", "2026-03", "name"),
    "oslo-ab": ("Oslo_ABH2NML_NR/FeatureServer/0", "2026-04-02", "class"),
    "oslo-c": ("Oslo_C/FeatureServer/0", "2024-07-08", "class"),
    "military-presence": ("Israeli_Military_Presence/FeatureServer/0", "2026-04-08", "class"),
    "yellow-line": ("YellowLineUnderCeaseFireDeal_15102025/FeatureServer/644", "2026-03-19", "name"),
    "settlements": ("Settlement_Builtup_Area/FeatureServer/1", "2026-04-01", "name_eng"),
}


def _get(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "sprezzature-maps"})
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 (fixed https host)
        return json.load(response)


def fetch(name: str) -> Path:
    path, as_of, keep = LAYERS[name]
    payload = _get(f"{SERVER}/{path}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson")
    features = []
    for raw in payload.get("features", []):
        if not raw.get("geometry"):
            continue
        geom = shape(raw["geometry"]).simplify(TOLERANCE, preserve_topology=True)
        features.append({
            "type": "Feature",
            "properties": {
                "label": (raw.get("properties") or {}).get(keep),
                "source": f"OCHA oPt, {path.split('/')[0]}",
                "as_of": as_of,
            },
            "geometry": mapping(geom),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"ocha-{name}.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return out


def main() -> None:
    for name in LAYERS:
        out = fetch(name)
        print(f"wrote {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
