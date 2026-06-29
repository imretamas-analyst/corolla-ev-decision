#!/usr/bin/env python3
"""
Estimate per-trip highway distance by routing each trip's departure -> destination
with OpenRouteService and measuring the motorway portion of the FASTEST route.
Writes seeds/trip_routed_highway.csv (trip_id, routed_total_km, routed_highway_km).

Why fastest routing reproduces your real split (and isn't circular): for the long
hauls the fastest route IS the motorway route you actually drive; for town hops it
has ~0 motorway. So default routing matches behaviour without forcing a preference.

Needs a free OpenRouteService key:
  1. sign up: https://openrouteservice.org/dev/#/signup
  2. create a token, then set it in PowerShell:  $env:ORS_API_KEY = "your-key"

NETWORK NOTE: calls api.openrouteservice.org (blocked in the build sandbox; run locally).
Caches in scripts/.ors_cache.json so re-runs resume and don't re-spend quota.

Usage:
  pip install requests
  python scripts/route_highway.py
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
CACHE = Path(__file__).parent / ".ors_cache.json"
URL = "https://api.openrouteservice.org/v2/directions/driving-car"
KEY = os.environ.get("ORS_API_KEY")
SHORT_KM = 3.0       # below this, assume 0 highway and skip the API call
SLEEP = 1.6          # ~37 req/min, under the free 40/min limit
HIGHWAY_BIT = 1      # ORS waycategory bitfield: 1 = Highway (motorway)


def parse_waycategory(route: dict):
    """Return (total_km, highway_km) from an ORS route object."""
    total_km = route["summary"]["distance"] / 1000.0
    hw_m = 0.0
    for seg in route.get("extras", {}).get("waycategory", {}).get("summary", []):
        if int(seg["value"]) & HIGHWAY_BIT:
            hw_m += seg["distance"]
    return total_km, hw_m / 1000.0


def route_od(dep, des):
    body = {"coordinates": [[dep[1], dep[0]], [des[1], des[0]]],  # ORS is [lon, lat]
            "extra_info": ["waycategory"]}
    r = requests.post(URL, json=body, timeout=40,
                      headers={"Authorization": KEY, "Content-Type": "application/json"})
    r.raise_for_status()
    return parse_waycategory(r.json()["routes"][0])


def main():
    if not KEY:
        sys.exit("Set ORS_API_KEY first (see the header of this file).")
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    trips = list(csv.DictReader(open(SEEDS / "raw_trips.csv", encoding="utf-8")))
    out, calls = [], 0
    for t in trips:
        try:
            dep = (float(t["dep_lat"]), float(t["dep_lng"]))
            des = (float(t["des_lat"]), float(t["des_lng"]))
            dist = float(t.get("distance_km") or 0)
        except (ValueError, KeyError):
            continue
        key = f"{round(dep[0],3)},{round(dep[1],3)}|{round(des[0],3)},{round(des[1],3)}"
        if key not in cache:
            if dist and dist < SHORT_KM:
                cache[key] = [round(dist, 3), 0.0]            # too short for motorway
            else:
                try:
                    cache[key] = [round(x, 3) for x in route_od(dep, des)]
                    calls += 1
                    time.sleep(SLEEP)
                    if calls % 25 == 0:
                        CACHE.write_text(json.dumps(cache))   # checkpoint for resume
                        print(f"  routed {calls} new OD pairs...")
                except Exception as e:
                    print(f"  skip {t['trip_id']}: {e}")
                    continue
        tot, hw = cache[key]
        out.append({"trip_id": t["trip_id"], "routed_total_km": tot, "routed_highway_km": hw})

    CACHE.write_text(json.dumps(cache))
    with open(SEEDS / "trip_routed_highway.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trip_id", "routed_total_km", "routed_highway_km"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to seeds/trip_routed_highway.csv "
          f"({calls} API calls, {len(cache)} unique OD pairs cached)")


if __name__ == "__main__":
    main()
