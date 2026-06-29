{{ config(enabled = var('use_routed_highway', false)) }}
-- One number: how the routed motorway estimate must be scaled to match the car's
-- own measured highway distance, over the months where BOTH exist (2022-2024).
with measured as (
    select trip_year, trip_month, sum(highway_km) as measured_hw
    from {{ ref('stg_telematics') }}
    group by 1, 2
),
routed as (
    select c.trip_year, c.trip_month, sum(r.routed_highway_km) as routed_hw
    from {{ ref('stg_routed_highway') }} r
    join {{ ref('int_trips_classified') }} c on c.trip_id = r.trip_id
    group by 1, 2
),
overlap as (
    select m.measured_hw, ro.routed_hw
    from measured m
    join routed ro on ro.trip_year = m.trip_year and ro.trip_month = m.trip_month
)
select sum(measured_hw) / nullif(sum(routed_hw), 0) as calibration_factor
from overlap
