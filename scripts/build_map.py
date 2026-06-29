#!/usr/bin/env python3
"""
Build an interactive trip map from seeds/raw_trips.csv:
  - a heatmap of everywhere the car has been (weighted by trips), and
  - faint lines for each trip, so recurring corridors show up.

Output: site/trip_map.html  (open in a browser; pulls Leaflet from a CDN).

PRIVACY: this plots your real coordinates, including home. Fine for local viewing.
Before publishing, pass --offset to shift every point by a small fixed amount
(keeps route shapes, breaks the link to your actual address), or --jitter to fuzz.

Usage:
  pip install folium
  python scripts/build_map.py            # real coordinates (local use)
  python scripts/build_map.py --offset   # shifted, safe to publish
"""
import argparse
import csv
from pathlib import Path

import folium
from folium.plugins import HeatMap

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
SITE = ROOT / "site"


def load_points(offset: float, jitter: float):
    import random
    random.seed(42)
    legs = []
    heat = {}
    with open(SEEDS / "raw_trips.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                a = (float(r["dep_lat"]) + offset, float(r["dep_lng"]) + offset)
                b = (float(r["des_lat"]) + offset, float(r["des_lng"]) + offset)
            except (ValueError, KeyError):
                continue
            if jitter:
                a = (a[0] + random.uniform(-jitter, jitter), a[1] + random.uniform(-jitter, jitter))
                b = (b[0] + random.uniform(-jitter, jitter), b[1] + random.uniform(-jitter, jitter))
            legs.append((a, b))
            for p in (a, b):
                key = (round(p[0], 3), round(p[1], 3))
                heat[key] = heat.get(key, 0) + 1
    return legs, heat


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", action="store_const", const=0.01, default=0.0,
                    help="shift all points by a fixed amount (publish-safe)")
    ap.add_argument("--jitter", type=float, default=0.0,
                    help="random fuzz in degrees, e.g. 0.005")
    args = ap.parse_args()

    legs, heat = load_points(args.offset, args.jitter)
    if not legs:
        raise SystemExit("No coordinates found in seeds/raw_trips.csv")

    lats = [p[0] for leg in legs for p in leg]
    lngs = [p[1] for leg in legs for p in leg]
    center = (sum(lats) / len(lats), sum(lngs) / len(lngs))

    m = folium.Map(location=center, zoom_start=5, tiles="CartoDB positron")
    for a, b in legs:
        folium.PolyLine([a, b], weight=1, opacity=0.25, color="#3b6ea5").add_to(m)
    HeatMap([[lat, lng, w] for (lat, lng), w in heat.items()],
            radius=18, blur=12, min_opacity=0.3).add_to(m)

    SITE.mkdir(exist_ok=True)
    out = SITE / "trip_map.html"
    m.save(str(out))
    print(f"wrote {out}  ({len(legs)} trips, {len(heat)} distinct points)")
    if args.offset or args.jitter:
        print("coordinates were shifted/fuzzed -> safe to publish")
    else:
        print("real coordinates -> local use only; re-run with --offset before publishing")


if __name__ == "__main__":
    main()
