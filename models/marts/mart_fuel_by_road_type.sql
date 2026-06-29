-- Fuel consumption split by the trip's dominant road type.
-- Distance-weighted l/100km = total litres / total km * 100.
--
-- When routed highway is enabled, this uses calibrated routed highway for ALL trips
-- (full multi-year coverage) crossed with each trip's observed fuel. Otherwise it
-- falls back to the measured-telematics subset (2022-2024 only).
{% if var('use_routed_highway', false) %}
with base as (
    select
        c.trip_id,
        c.distance_km,
        c.minutes_driven,
        c.distance_km / 100.0 * c.observed_l_per_100km as fuel_liters,
        h.highway_km / nullif(c.distance_km, 0)        as highway_share
    from {{ ref('int_trips_classified') }} c
    join {{ ref('int_trip_highway') }} h on h.trip_id = c.trip_id
    where c.distance_km > 0 and c.minutes_driven > 0
),
classified as (
    select *,
        case when highway_share >= 0.60 then 'highway'
             when highway_share <  0.05 then 'city'
             else 'mixed' end as road_type
    from base
)
select
    road_type,
    count(*)                                                      as trips,
    round(sum(distance_km), 0)                                    as total_km,
    round(sum(fuel_liters) / nullif(sum(distance_km), 0) * 100, 2) as fuel_l_per_100km,
    round(sum(distance_km) / nullif(sum(minutes_driven) / 60.0, 0), 1) as avg_speed_kmh
from classified
group by 1
{% else %}
with t as (select * from {{ ref('stg_telematics') }}),
classified as (
    select *,
        case when highway_share >= 0.60 then 'highway'
             when highway_share <  0.05 then 'city'
             else 'mixed' end as road_type
    from t
)
select
    road_type,
    count(*)                                                   as trips,
    round(sum(total_km), 0)                                    as total_km,
    round(sum(fuel_liters) / nullif(sum(total_km), 0) * 100, 2) as fuel_l_per_100km,
    round(sum(total_km) / nullif(sum(total_sec) / 3600.0, 0), 1) as avg_speed_kmh
from classified
group by 1
{% endif %}
