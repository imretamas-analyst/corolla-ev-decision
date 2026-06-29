#!/usr/bin/env python3
"""
Convert the raw telematics tab (exported as CSV) into seeds/raw_telematics.csv,
generating a trip_id per row. This is the measured behavioural data: highway
distance, speeds, harsh-driving events, idle time, per-trip fuel.

HOW TO GET THE INPUT:
  In Google Sheets, open the raw telematics tab (headers TripID / startTimeGmt /
  totalDistanceInKm / highwayDistanceInKm / ...), File > Download > CSV.

Usage:
  python scripts/prepare_telematics.py "path\to\telematics_export.csv"

No network needed; standard library only.
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[1] / "seeds"

COLMAP = {
    "totalDistanceInKm": "total_km",
    "highwayDistanceInKm": "highway_km",
    "averageFuelConsumptionInL": "fuel_l_per_100km",
    "fuelConsumptionInL": "fuel_liters",
    "averageSpeedInKmph": "avg_speed",
    "maxSpeedInKmph": "max_speed",
    "overspeedDistanceInKm": "overspeed_km",
    "hardAccelerationCount": "hard_accel",
    "hardBrakingCount": "hard_brake",
    "nightTrip": "night_trip",
    "idleDurationInSec": "idle_sec",
    "totalDurationInSec": "total_sec",
}
OUT_COLS = ["trip_id"] + list(COLMAP.values()) + ["trip_year", "trip_month"]


def parse_ym(s):
    for f in ("%m/%d/%Y %H:%M", "%m/%d/%y %H:%M", "%m/%d/%Y %H:%M:%S"):
        try:
            d = datetime.strptime((s or "").strip(), f); return d.year, d.month
        except ValueError:
            continue
    return "", ""


def num(v):
    return (v or "").replace(",", "").strip()


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "telematics.csv"
    if not src.exists():
        sys.exit(
            f"\nInput file not found: {src}\n\n"
            "This script READS your sheet's raw telematics tab (the CSV you export from\n"
            "Google Sheets) and WRITES the seed seeds/raw_telematics.csv.\n"
            "Give it the exported file as an argument:\n\n"
            '  python scripts/prepare_telematics.py "C:\\path\\to\\telematics_export.csv"\n'
        )
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    missing = [h for h in COLMAP if rows and h not in rows[0]]
    if missing:
        print(f"WARNING: headers not found: {missing}\nEdit COLMAP to match your sheet.")

    out = []
    for i, r in enumerate(rows, start=1):
        if not num(r.get("totalDistanceInKm")) or num(r.get("totalDistanceInKm")) == "0":
            continue
        rec = {"trip_id": f"tg{i:04d}"}
        for src_col, dst in COLMAP.items():
            rec[dst] = num(r.get(src_col, ""))
        rec["trip_year"], rec["trip_month"] = parse_ym(r.get("startTimeGmt", ""))
        out.append(rec)

    dest = SEEDS / "raw_telematics.csv"
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} trips to {dest}")


if __name__ == "__main__":
    main()
