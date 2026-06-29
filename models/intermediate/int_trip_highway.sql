{{ config(enabled = var('use_routed_highway', false)) }}
with c as (select * from {{ ref('int_trips_classified') }}),
r as (select * from {{ ref('stg_routed_highway') }}),
f as (select calibration_factor from {{ ref('int_highway_calibration_factor') }})
select
    c.trip_id,
    c.distance_km                                                          as total_km,
    least(c.distance_km, coalesce(r.routed_highway_km, 0) * f.calibration_factor) as highway_km,
    c.distance_km
      - least(c.distance_km, coalesce(r.routed_highway_km, 0) * f.calibration_factor) as city_km
from c
left join r on r.trip_id = c.trip_id
cross join f
