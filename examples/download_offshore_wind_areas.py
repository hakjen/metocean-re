"""
Download the Norwegian offshore wind areas from NVE and save them as one
GeoJSON file for the map in the Streamlit app (app/data/offshore_wind_areas.geojson).

Source: NVE (Norwegian Water Resources and Energy Directorate), map service
HavvindOnline, licence NLOD (Norwegian licence for open government data):
    https://kart.nve.no/enterprise/rest/services/Mapservices/HavvindOnline/MapServer

Layers used:
    17  Åpnet område                 areas opened for offshore wind (Utsira Nord, Sørlige Nordsjø II)
    16  Prosjektområde               project areas awarded inside the opened areas
    18  Utredningsområde for havvind areas identified by NVE in 2023 for further assessment

The file is saved in the repository, so the app works without internet. Run
this script again to update it (from the project root):
    python examples/download_offshore_wind_areas.py
"""

import json
from pathlib import Path
from urllib.request import urlopen

SERVICE = "https://kart.nve.no/enterprise/rest/services/Mapservices/HavvindOnline/MapServer"
OUTPUT = Path(__file__).resolve().parent.parent / "app" / "data" / "offshore_wind_areas.geojson"

# layer id: (category shown in the app, field with the name of the area, field with the technology, web page)
LAYERS = {
    17: ("Opened area", "havvindomr", "teknologi", "urlregj"),
    16: ("Awarded project area", "havvindomr", "teknologi", "urlregj"),
    18: ("Assessment area 2023", "navn", "typeanlegg", "nettsideurl"),
}
TECHNOLOGY = {"Flytende": "floating", "Bunnfast": "bottom-fixed", "Flytende og bunnfast": "floating and bottom-fixed"}


def rounded(coordinates, decimals=4):
    """Round all coordinates (about 10 m at 4 decimals) to keep the file small."""
    if isinstance(coordinates[0], (int, float)):
        return [round(c, decimals) for c in coordinates]
    return [rounded(c, decimals) for c in coordinates]


def download_layer(layer):
    url = f"{SERVICE}/{layer}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
    with urlopen(url, timeout=60) as response:
        return json.load(response)["features"]


if __name__ == "__main__":
    features = []
    for layer, (category, name_field, technology_field, url_field) in LAYERS.items():
        for feature in download_layer(layer):
            p = feature["properties"]
            features.append({
                "type": "Feature",
                "properties": {
                    "name": p[name_field],
                    "category": category,
                    "technology": TECHNOLOGY.get(p[technology_field], p[technology_field]),
                    "area_km2": p["areal_km2"],
                    "url": p[url_field],
                },
                "geometry": {"type": feature["geometry"]["type"],
                             "coordinates": rounded(feature["geometry"]["coordinates"])},
            })

    OUTPUT.parent.mkdir(exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "source": f"NVE, HavvindOnline ({SERVICE}), layers {', '.join(map(str, LAYERS))}. Licence: NLOD.",
        "features": features,
    }
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUTPUT}: {len(features)} areas")
