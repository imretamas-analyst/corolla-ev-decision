{{ config(enabled = var('use_routed_highway', false)) }}
with measured as (
    select trip_year, trip_month, sum(highway_km) as measured_hw
    from {{ ref('stg_telematics') }} group by 1, 2
),
routed as (
    select c.trip_year, c.trip_month, sum(r.routed_highway_km) as routed_hw
    from {{ ref('stg_routed_highway') }} r
    join {{ ref('int_trips_classified') }} c on c.trip_id = r.trip_id
    group by 1, 2
),
f as (select calibration_factor from {{ ref('int_highway_calibration_factor') }})
select
    m.trip_year, m.trip_month,
    round(m.measured_hw, 0)                          as measured_hw_km,
    round(ro.routed_hw, 0)                           as routed_hw_km,
    round(ro.routed_hw * f.calibration_factor, 0)    as routed_calibrated_km,
    round(f.calibration_factor, 3)                   as calibration_factor
from measured m
join routed ro on ro.trip_year = m.trip_year and ro.trip_month = m.trip_month
cross join f
order by m.trip_year, m.trip_month
