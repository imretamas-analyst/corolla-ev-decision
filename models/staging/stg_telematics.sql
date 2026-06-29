with source as (select * from {{ ref('raw_telematics') }})
select
    trip_id,
    cast(total_km as double)            as total_km,
    cast(highway_km as double)          as highway_km,
    cast(total_km as double) - cast(highway_km as double) as city_km,
    cast(highway_km as double) / nullif(cast(total_km as double), 0) as highway_share,
    cast(fuel_l_per_100km as double)    as fuel_l_per_100km,
    cast(fuel_liters as double)         as fuel_liters,
    cast(avg_speed as double)           as avg_speed,
    cast(max_speed as double)           as max_speed,
    cast(overspeed_km as double)        as overspeed_km,
    cast(hard_accel as integer)         as hard_accel,
    cast(hard_brake as integer)         as hard_brake,
    cast(night_trip as boolean)         as night_trip,
    cast(idle_sec as integer)           as idle_sec,
    cast(total_sec as integer)          as total_sec,
    cast(trip_year as integer)          as trip_year,
    cast(trip_month as integer)         as trip_month
from source
where cast(total_km as double) > 0
