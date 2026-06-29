#!/usr/bin/env python3
"""
Fetch real per-trip mean temperature from the Open-Meteo historical archive and
write seeds/trip_temperature.csv (trip_id, date, avg_temp_c).

This REPLACES the climatology stand-in in seeds/monthly_temperature.csv with the
actual temperature each trip was driven in, keyed on departure coordinates + date.

NETWORK NOTE
------------
This calls https://archive-api.open-meteo.com which is NOT reachable from the
sandbox this project was scaffolded in (the egress allowlist only permits package
registries). Run it locally, where outbound HTTPS is available. It needs no API key.

After running, wire it in by:
  1) adding `trip_temperature` as a dbt seed, and
  2) in models/intermediate/int_trip_temperature.sql, join trips to
     trip_temperature on trip_id instead of monthly_temperature on region/year/month.

Usage:
  pip install requests
  python scripts/fetch_temperature.py
"""
import csv
import time
from datetime import datetime
from pathlib import Path

import requests

SEEDS = Path(__file__).resolve().parents[1] / "seeds"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def parse_date(s: str) -> str:
    # raw export has mixed formats, e.g. "2/13/2022 11:25" and "6/3/22 8:00"
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%y %H:%M", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {s!r}")


def fetch_mean_temp(lat: float, lon: float, date: str) -> float | None:
    r = requests.get(
        ARCHIVE,
        params={
            "latitude": round(lat, 3),
            "longitude": round(lon, 3),
            "start_date": date,
            "end_date": date,
            "daily": "temperature_2m_mean",
            "timezone": "auto",
        },
        timeout=30,
    )
    r.raise_for_status()
    vals = r.json().get("daily", {}).get("temperature_2m_mean", [])
    return vals[0] if vals else None


def main() -> None:
    trips = list(csv.DictReader(open(SEEDS / "raw_trips.csv", encoding="utf-8")))
    cache: dict[tuple, float | None] = {}
    out = []
    for t in trips:
        date = parse_date(t["departure_time"])
        lat, lon = float(t["dep_lat"]), float(t["dep_lng"])
        key = (round(lat, 2), round(lon, 2), date)
        if key not in cache:
            cache[key] = fetch_mean_temp(lat, lon, date)
            time.sleep(0.2)  # be polite to the free API
        out.append({"trip_id": t["trip_id"], "date": date, "avg_temp_c": cache[key]})

    with open(SEEDS / "trip_temperature.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trip_id", "date", "avg_temp_c"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to seeds/trip_temperature.csv")


if __name__ == "__main__":
    main()
