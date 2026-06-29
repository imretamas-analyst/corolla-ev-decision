#!/usr/bin/env python3
"""
Convert your Google Sheet's trip tab (exported as CSV) into the project's
seeds/raw_trips.csv schema, generating a trip_id for each row.

WHY: the sheet's headers (e.g. "DEP-Latitude", "Distance Driven (km)") don't match
what the dbt models expect (dep_lat, distance_km, ...). This renames them and adds
a trip_id, so the result drops straight into seeds/ and the whole pipeline runs on
your full history instead of the 24-row sample.

HOW TO GET THE INPUT:
  In Google Sheets, open the trip tab (the one with Departure / DEP-Latitude /
  Destination / Distance Driven (km) / ...), then File > Download > CSV.
  Save it next to this script as 'sheet_trips.csv' (or pass a path as argv[1]).

Usage:
  python scripts/prepare_raw_trips.py [path/to/sheet_export.csv]

No network needed; standard library only.
"""
import csv
import sys
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[1] / "seeds"

# sheet header  ->  project column
COLMAP = {
    "Departure": "departure",
    "DEP-Latitude": "dep_lat",
    "DEP-Longitude": "dep_lng",
    "Departure_time": "departure_time",
    "Destination": "destination",
    "DES-Latitude": "des_lat",
    "DES-Longitude": "des_lng",
    "Arrival_time": "arrival_time",
    "Distance Driven (km)": "distance_km",
    "Fuel Consumption (l/100km)": "fuel_l_per_100km",
    "Year": "year",
    "Month": "month",
    "Minutes driven": "minutes_driven",
    "Country visited": "country",
}
OUT_COLS = [
    "trip_id", "departure", "dep_lat", "dep_lng", "departure_time",
    "destination", "des_lat", "des_lng", "arrival_time", "distance_km",
    "fuel_l_per_100km", "year", "month", "minutes_driven", "country",
]


def clean_number(v: str) -> str:
    # strip thousands separators like "1,827.51" -> "1827.51"
    return (v or "").replace(",", "").strip()


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "sheet_trips.csv"
    rows_in = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    missing = [h for h in COLMAP if h not in (rows_in[0].keys() if rows_in else [])]
    if missing:
        print(f"WARNING: these expected headers were not found: {missing}")
        print("Edit COLMAP at the top of this script to match your sheet's headers.")

    out = []
    for i, r in enumerate(rows_in, start=1):
        # skip blank/total rows (no departure or no distance)
        if not (r.get("Departure") or "").strip():
            continue
        rec = {"trip_id": f"t{i:04d}"}
        for sheet_col, proj_col in COLMAP.items():
            val = r.get(sheet_col, "")
            if proj_col in ("dep_lat", "dep_lng", "des_lat", "des_lng",
                            "distance_km", "fuel_l_per_100km", "minutes_driven"):
                val = clean_number(val)
            rec[proj_col] = val
        out.append(rec)

    dest = SEEDS / "raw_trips.csv"
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} trips to {dest}")


if __name__ == "__main__":
    main()
