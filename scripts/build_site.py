#!/usr/bin/env python3
"""
Build the static site (site/index.html, site/habits.html, site/decision.html) from
the dbt marts in dev.duckdb. Shared CSS + nav. No server, no Node -> GitHub Pages ready.

Run AFTER `dbt build`, and after `python scripts/build_map.py` (habits.html embeds
site/trip_map.html).

Usage:
  pip install duckdb
  python scripts/build_site.py
"""
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def q(con, sql):
    rows = con.sql(sql)
    cols = [d[0] for d in rows.description]
    return [dict(zip(cols, r)) for r in rows.fetchall()]


def collect():
    con = duckdb.connect(str(ROOT / "dev.duckdb"), read_only=True)
    overview = q(con, "select * from mart_driving_overview")[0]
    monthly = q(con, "select * from mart_monthly_habits")
    decision = q(con, "select * from mart_ev_decision")
    corolla_cmp = q(con, "select source, l_per_100km from agg_corolla_vs_spritmonitor")

    # running cost & CO2 per 100km per car (real-world basis; corolla = actual)
    ladder = q(con, """
        with c as (
            select car_id, source, make, model,
                   round(total_energy_cost_eur/nullif(total_km,0)*100,2) as eur_per_100km,
                   round(total_co2_kg/nullif(total_km,0)*100,2)          as co2_per_100km
            from agg_car_annual)
        select car_id, make, model, eur_per_100km, co2_per_100km from c
        where (car_id='corolla' and source='actual')
           or (car_id<>'corolla' and source='spritmonitor')
        order by eur_per_100km desc
    """)
    by_source = {}
    for r in q(con, "select car_id, source, total_energy_cost_eur c, total_co2_kg co2 from agg_car_annual"):
        by_source.setdefault(r["car_id"], {})[r["source"]] = {
            "cost": round(r["c"] / overview["years_span"]),
            "co2": round(r["co2"] / overview["years_span"]),
        }
    # measured telematics: fuel by road type, behaviour, distance split, hybrid payback
    fuel_road = q(con, "select * from mart_fuel_by_road_type order by fuel_l_per_100km")
    behaviour = q(con, "select * from mart_driving_behaviour")[0]
    dist_split = q(con, "select round(sum(highway_km),0) hw, round(sum(city_km),0) nonhw, "
                        "round(100.0*sum(highway_km)/nullif(sum(total_km),0),0) hw_pct from stg_telematics")[0]
    hybrid_rows = q(con, "select * from mart_hybrid_vs_conventional")
    hybrid = hybrid_rows[0] if hybrid_rows else None

    # routed + calibrated highway (only present if built with use_routed_highway: true)
    routed = None
    try:
        full = q(con, "select round(100.0*sum(h.highway_km)/nullif(sum(h.total_km),0),0) hw_pct, "
                      "round(sum(h.highway_km),0) hw_km, round(sum(h.total_km)-sum(h.highway_km),0) nonhw_km "
                      "from int_trip_highway h")[0]
        factor = q(con, "select round(calibration_factor,3) f from int_highway_calibration_factor")[0]["f"]
        # validation: measured vs calibrated-routed highway, aggregated to year
        valid = q(con, "select trip_year, round(sum(measured_hw_km),0) measured, "
                       "round(sum(routed_calibrated_km),0) calibrated "
                       "from mart_highway_calibration group by trip_year order by trip_year")
        routed = {"full": full, "factor": factor, "valid": valid}
    except Exception:
        routed = None

    con.close()
    return dict(overview=overview, monthly=monthly, decision=decision,
                corolla_cmp=corolla_cmp, ladder=ladder, by_source=by_source,
                fuel_road=fuel_road, behaviour=behaviour, dist_split=dist_split,
                hybrid=hybrid, routed=routed)


CSS = """
:root{--ink:#1b2430;--muted:#6b7785;--line:#e3e8ee;--accent:#3b6ea5;--good:#2e7d57;--bad:#b4543a;--bg:#fafbfc}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
nav{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:9}
nav .in{max-width:900px;margin:0 auto;padding:12px 20px;display:flex;gap:18px;align-items:center}
nav a{color:var(--muted);text-decoration:none;font-size:14px}nav a.on{color:var(--accent);font-weight:600}
nav .brand{font-weight:700;color:var(--ink);margin-right:auto}
.wrap{max-width:900px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 6px}h2{font-size:17px;margin:28px 0 12px}.sub{color:var(--muted);margin:0 0 8px;font-size:15px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0}
.kpi{border:1px solid var(--line);border-radius:10px;padding:14px;background:#fff}
.kpi .v{font-size:21px;font-weight:600}.kpi .l{color:var(--muted);font-size:12px;margin-top:2px}
.good{color:var(--good)}.bad{color:var(--bad)}
.card{border:1px solid var(--line);border-radius:10px;padding:18px;background:#fff;margin-bottom:18px}
.row{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
button{font:inherit;padding:8px 14px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer}
button.on{border-color:var(--accent);background:var(--accent);color:#fff}
.bar{height:20px;border-radius:4px;background:var(--accent)}
.barrow{display:grid;grid-template-columns:130px 1fr 90px;align-items:center;gap:10px;margin:6px 0}
.barrow .nm{color:var(--muted);font-size:13px}.barrow .val{text-align:right;font-variant-numeric:tabular-nums}
.note{color:var(--muted);font-size:13px}.lim li{margin:6px 0}
iframe{width:100%;height:420px;border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600}
"""


def nav(active):
    items = [("index.html", "Overview"), ("habits.html", "Driving stats"), ("decision.html", "EV decision")]
    links = "".join(
        f'<a href="{href}" class="{"on" if href==active else ""}">{label}</a>' for href, label in items
    )
    return f'<nav><div class="in"><span class="brand">Corolla &middot; data project</span>{links}</div></nav>'


def shell(title, active, body, data=None, script=""):
    data_block = f"<script>const D = {json.dumps(data)};</script>" if data is not None else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>{CSS}</style></head><body>{nav(active)}<div class="wrap">{body}</div>
{data_block}<script>{script}</script></body></html>"""


def page_index(d):
    o = d["overview"]
    body = f"""
    <h1>Should this Corolla go electric?</h1>
    <p class="sub">A data project on {o['years_span']} years of real trips from one hybrid car &mdash;
    what the driving actually looks like, and whether replacing it with an EV makes sense.</p>

    <div class="grid">
      <div class="kpi"><div class="v">{o['total_km']:,.0f}</div><div class="l">km driven</div></div>
      <div class="kpi"><div class="v">{o['total_trips']:,}</div><div class="l">trips</div></div>
      <div class="kpi"><div class="v">{o['countries_visited']}</div><div class="l">countries</div></div>
      <div class="kpi"><div class="v">{o['avg_speed_kmh']}</div><div class="l">km/h avg</div></div>
    </div>

    <h2>The question</h2>
    <p>The car is a Toyota Corolla 1.8 Hybrid. Switching to an EV is tempting, but the honest
    test isn't "is electricity cheaper than petrol" (per km it is) &mdash; it's whether replacing a
    paid-off, already-efficient hybrid pays off, and at what cost per tonne of CO&#8322; avoided.
    This project answers that with real driving data instead of brochure figures.</p>

    <h2>What's inside</h2>
    <p><a href="habits.html"><b>Driving stats</b></a> &mdash; four years of real habits: seasonality,
    speeds, the holiday-season multi-country pattern, and a map of every trip.<br>
    <a href="decision.html"><b>EV decision</b></a> &mdash; each candidate car costed on your own driving,
    with the green-premium (&euro; per tonne of CO&#8322; avoided) front and centre.</p>

    <h2>Data &amp; method</h2>
    <p>Trip telematics come from the car's connected-services export. Two layers are used: a cleaned,
    geocoded trip table (for mapping and energy cost) and the raw telematics tab (measured highway
    distance, speeds, harsh-driving events, per-trip fuel). The car only recorded highway distance
    through 2022&ndash;24, so for full coverage each trip's motorway portion is routed with
    <b>OpenRouteService</b> and calibrated against the measured data (see the validation on the driving-stats
    page). Models are built with <b>dbt</b> on a local <b>DuckDB</b> warehouse; real-world consumption is
    anchored to community <b>Spritmonitor</b> averages rather than WLTP; per-trip temperature comes from the
    <b>Open-Meteo</b> historical archive. CO&#8322; is derived from real fuel use (2.31 kg/l); as a
    cross-check, that puts real-world emissions a little above the car's official WLTP figure
    (~100&ndash;103 g/km), mirroring the real-vs-lab fuel gap.</p>

    <h2>Honest limitations</h2>
    <ul class="lim note">
      <li><b>Highway distance after 2024</b> is routed-and-calibrated, not measured &mdash; trustworthy in
      aggregate (it tracks the measured data within a few percent year by year) but noisier per trip.</li>
      <li><b>Average speed and idle time</b> are whole-trip figures, so time spent stopped is included.</li>
      <li><b>Road-type fuel</b> is bucketed by each trip's dominant road type; very short cold-start trips
      read high regardless of road type.</li>
      <li><b>Map routes are straight lines</b> between endpoints, not actual road geometry.</li>
      <li><b>Temperature region</b> is approximated by destination country; per-trip measured temps are
      used where available, monthly climatology as fallback.</li>
      <li><b>Car prices and some real-world consumption figures</b> are list/approximate and flagged for
      verification in the seeds.</li>
      <li><b>Green premium</b> assumes an 8-year horizon and current German energy prices.</li>
      <li><b>Privacy</b>: the home address is collapsed to a single node; the published map can be
      coordinate-shifted.</li>
    </ul>
    """
    return shell("Overview &middot; Corolla data project", "index.html", body)


def _calibration_card(rt):
    rows = "".join(
        f"<tr><td>{v['trip_year']}</td><td>{v['measured']:,.0f}</td>"
        f"<td>{v['calibrated']:,.0f}</td></tr>" for v in rt["valid"])
    return f"""
    <div class="card"><h2 style="margin-top:0">How the highway estimate was validated</h2>
      <p class="note">The car only recorded highway distance through 2022&ndash;24. For full coverage,
      every trip's motorway portion is routed with OpenRouteService and scaled by a single calibration
      factor of <b>{rt['factor']}</b>. That factor was set so the routed estimate reproduces the car's
      own measured highway over the overlap &mdash; and it tracks year by year:</p>
      <table><thead><tr><th>Year</th><th>Measured km</th><th>Routed &amp; calibrated km</th></tr></thead>
      <tbody>{rows}</tbody></table>
      <p class="note">Measured and calibrated-routed stay within a few percent every year, so the same
      method is trusted for the post-2024 trips the car never recorded.</p>
    </div>"""


def page_habits(d):
    o = d["overview"]
    b = d["behaviour"]
    ds = d["dist_split"]
    fr = d["fuel_road"]
    rt = d.get("routed")
    by_road = {r["road_type"]: r for r in fr}
    city_fuel = by_road.get("city", {}).get("fuel_l_per_100km", 0)
    hw_fuel = by_road.get("highway", {}).get("fuel_l_per_100km", 0)
    # headline highway share: full-coverage routed+calibrated if available, else measured subset
    hw_share = rt["full"]["hw_pct"] if rt else b["highway_share_pct"]
    hw_label = "distance on highway" if rt else "highway (2022-24 only)"
    coverage = ("Highway is measured for 2022-24 and routed-and-calibrated for the whole period; "
                "everything else (speeds, harsh events) is measured telematics from 2022-24."
                if rt else "all figures below use measured telematics (2022-24)")
    body = f"""
    <h1>Driving stats</h1>
    <p class="sub">{o['years_span']} years &middot; {o['total_km']:,.0f} km &middot; {o['total_trips']:,} trips
    &middot; {coverage}</p>

    <div class="grid">
      <div class="kpi"><div class="v">{hw_share:.0f}%</div><div class="l">{hw_label}</div></div>
      <div class="kpi"><div class="v">{b['avg_speed_kmh']}</div><div class="l">km/h average</div></div>
      <div class="kpi"><div class="v">{b['top_speed_kmh']:.0f}</div><div class="l">km/h top speed</div></div>
      <div class="kpi"><div class="v">{o['countries_visited']}</div><div class="l">countries visited</div></div>
    </div>

    <div class="card"><h2 style="margin-top:0">Fuel: highway vs city</h2>
      <p class="note">A hybrid is least efficient at steady highway speed and best in town
      (electric assist + regen) &mdash; so the usual pattern flips.</p>
      <div id="fuelbars"></div>
      <p class="note">{(rt['full']['hw_pct'] if rt else ds['hw_pct']):.0f}% of the distance is highway, where the
      hybrid is at its thirstiest ({hw_fuel} l/100&nbsp;km) &mdash; yet it still averages ~5, which is
      the headline: a strong number precisely <i>because</i> so much of the driving is the kind hybrids
      handle least well.</p>
    </div>

    <div class="card"><h2 style="margin-top:0">Driving behaviour <span class="note" style="font-weight:400">&middot; measured 2022-24</span></h2>
      <div class="grid">
        <div class="kpi"><div class="v">{b['overspeed_share_pct']}%</div><div class="l">distance over the limit</div></div>
        <div class="kpi"><div class="v">{b['idle_time_pct']}%</div><div class="l">time idling</div></div>
        <div class="kpi"><div class="v">{b['hard_brake_per_100km']}</div><div class="l">hard brakes / 100 km</div></div>
        <div class="kpi"><div class="v">{b['night_trip_pct']:.0f}%</div><div class="l">night trips</div></div>
      </div>
    </div>
    {_calibration_card(rt) if rt else ""}

    <div class="card"><h2 style="margin-top:0">Distance by month</h2>
      <p class="note">Holiday season stands out &mdash; months reaching more than one country are highlighted.</p>
      <div id="kmbars"></div>
    </div>
    <div class="card"><h2 style="margin-top:0">Where the car has been</h2>
      <p class="note">Heatmap of all trips; recurring corridors show up darkest.
      (<a href="trip_map.html" target="_blank">open full map</a>)</p>
      <iframe src="trip_map.html" title="trip map"></iframe>
    </div>
    """
    script = r"""
    const MN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const byM={}; D.monthly.forEach(r=>byM[r.month]=r);
    function bars(el,rows,fmt){const max=Math.max(...rows.map(r=>r.v))||1;
      el.innerHTML=rows.map(r=>`<div class="barrow"><div class="nm">${r.nm}</div>
      <div><div class="bar" style="width:${Math.max(2,100*r.v/max)}%;background:${r.color||'var(--accent)'}"></div></div>
      <div class="val">${fmt(r.v)}</div></div>`).join('');}
    const fuel=D.fuel_road.map(r=>({nm:r.road_type+' ('+Math.round(r.total_km).toLocaleString()+' km)',
      v:r.fuel_l_per_100km,color:r.road_type==='highway'?'var(--bad)':'var(--good)'}));
    bars(document.getElementById('fuelbars'),fuel,v=>v.toFixed(1)+' l/100km');
    const km=[];
    for(let m=1;m<=12;m++){const r=byM[m];
      km.push({nm:MN[m-1],v:r?r.total_km:0,color:(r&&r.distinct_countries>1)?'var(--bad)':'var(--accent)'});}
    bars(document.getElementById('kmbars'),km,v=>v.toLocaleString()+' km');
    """
    return shell("Driving stats &middot; Corolla data project", "habits.html", body, d, script)


def page_decision(d):
    body = """
    <h1>EV decision</h1>
    <p class="sub">Every car costed on the real trips. Baseline = the actual hybrid driving.</p>

    <div class="card"><h2 style="margin-top:0">First: was the hybrid worth it?</h2>
      <p class="note">Before comparing EVs, the same logic applied to the hybrid vs a conventional petrol
      Corolla &mdash; on your actual driving. Unlike the EV, this premium actually pays back.</p>
      <div class="grid" id="hybridkpis"></div>
    </div>

    <div class="card"><h2 style="margin-top:0">The efficiency ladder</h2>
      <p class="note">Running cost per 100 km, real-world. Petrol &rarr; hybrid &rarr; electric &mdash;
      the hybrid is already far ahead of a conventional petrol car before any EV enters the picture.</p>
      <table id="ladder"><thead><tr><th>Car</th><th>&euro;/100&nbsp;km</th><th>kg CO&#8322;/100&nbsp;km</th></tr></thead><tbody></tbody></table>
    </div>

    <div class="row" id="cars"></div>
    <div class="row" id="srcs"><span style="align-self:center;color:var(--muted);font-size:13px;margin-right:4px">EV figures:</span></div>
    <div class="grid" id="kpis"></div>
    <div class="card"><h2 style="margin-top:0">Annual energy cost</h2><div id="costbars"></div></div>
    <div class="card"><h2 style="margin-top:0">Green premium &mdash; &euro; / tonne CO&#8322; avoided</h2>
      <div id="co2bars"></div>
      <p class="note">Lower is better. All are far above the ~&euro;80/t price of carbon on the EU market &mdash;
      replacing a working hybrid is an expensive way to cut CO&#8322;.</p></div>
    <div class="card"><h2 style="margin-top:0">Your Corolla vs the world (l/100&nbsp;km)</h2><div id="cmpbars"></div></div>
    """
    script = r"""
    let car=D.decision[0].car_id, src='spritmonitor';
    const eur=n=>'\u20ac'+Math.round(n).toLocaleString();
    const h=D.hybrid;
    document.getElementById('hybridkpis').innerHTML = h ? [
      ['Annual fuel saving','good',eur(h.annual_saving_eur)],
      ['Hybrid premium','',eur(h.hybrid_premium_eur)],
      ['Payback','good',(h.payback_years>0?h.payback_years.toFixed(1)+' yrs':'\u2014')],
      ['Annual km','',Math.round(h.annual_km).toLocaleString()],
    ].map(([l,c,v])=>`<div class="kpi"><div class="v ${c}">${v}</div><div class="l">${l}</div></div>`).join('')
      : '<p class="note">No conventional-car comparison yet \u2014 the non-hybrid car id must match conventional_car_id (default corolla_ice).</p>';
    document.querySelector('#ladder tbody').innerHTML=D.ladder.map(r=>{
      const hl=r.car_id==='corolla'?' style="background:#eef4fb"':'';
      return `<tr${hl}><td>${r.make} ${r.model}</td><td>${r.eur_per_100km.toFixed(2)}</td><td>${r.co2_per_100km.toFixed(1)}</td></tr>`;}).join('');
    const cr=document.getElementById('cars');
    D.decision.forEach(d=>{const b=document.createElement('button');
      b.textContent=d.make+' '+d.model.replace(/ \d.*$/,'');b.dataset.car=d.car_id;
      b.onclick=()=>{car=d.car_id;render();};cr.appendChild(b);});
    const sr=document.getElementById('srcs');
    [['spritmonitor','real-world'],['wltp','optimistic (WLTP)']].forEach(([s,l])=>{
      const b=document.createElement('button');b.textContent=l;b.dataset.src=s;
      b.onclick=()=>{src=s;render();};sr.appendChild(b);});
    function bars(el,rows,fmt,color){const max=Math.max(...rows.map(r=>r.v))||1;
      el.innerHTML=rows.map(r=>`<div class="barrow"><div class="nm">${r.nm}</div>
      <div><div class="bar" style="width:${Math.max(2,100*r.v/max)}%;background:${r.color||color||'var(--accent)'}"></div></div>
      <div class="val">${fmt(r.v)}</div></div>`).join('');}
    function render(){
      document.querySelectorAll('#cars button').forEach(b=>b.classList.toggle('on',b.dataset.car===car));
      document.querySelectorAll('#srcs button').forEach(b=>b.classList.toggle('on',b.dataset.src===src));
      const d=D.decision.find(x=>x.car_id===car);
      const evCost=D.by_source[car][src].cost, coCost=d.corolla_annual_cost_eur, saving=coCost-evCost;
      document.getElementById('kpis').innerHTML=[
        ['Annual saving',(saving>=0?'good':'bad'),eur(saving)],
        ['CO\u2082 avoided / yr','',Math.round(d.annual_co2_avoided_kg).toLocaleString()+' kg'],
        ['Capital premium','',eur(d.capital_premium_eur)],
        ['Payback','',(d.payback_years>0?d.payback_years.toFixed(0)+' yrs':'\u2014')],
        ['\u20ac / tonne CO\u2082','bad',eur(d.green_premium_eur_per_tonne)],
      ].map(([l,c,v])=>`<div class="kpi"><div class="v ${c}">${v}</div><div class="l">${l}</div></div>`).join('');
      bars(document.getElementById('costbars'),[
        {nm:'Corolla (your driving)',v:coCost,color:'#6b7785'},
        {nm:d.make,v:evCost}],eur);
      bars(document.getElementById('co2bars'),
        D.decision.map(x=>({nm:x.make,v:x.green_premium_eur_per_tonne,
          color:x.car_id===car?'var(--bad)':'#d8b4a8'})),eur);
      bars(document.getElementById('cmpbars'),
        D.corolla_cmp.map(c=>({nm:c.source,v:c.l_per_100km,
          color:c.source==='actual'?'var(--accent)':'#c9d3dd'})),v=>v.toFixed(2));
    }
    render();
    """
    return shell("EV decision &middot; Corolla data project", "decision.html", body, d, script)


def main():
    d = collect()
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page_index(d), encoding="utf-8")
    (SITE / "habits.html").write_text(page_habits(d), encoding="utf-8")
    (SITE / "decision.html").write_text(page_decision(d), encoding="utf-8")
    print("wrote site/index.html, site/habits.html, site/decision.html")
    if not (SITE / "trip_map.html").exists():
        print("note: run scripts/build_map.py so habits.html can embed the map")


if __name__ == "__main__":
    main()
