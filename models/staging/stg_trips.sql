-- Cleaned trip facts. We keep year/month as the time grain (departure_time
-- in the raw export has inconsistent date formats, so we don't parse it here).
with source as (
    select * from {{ ref('raw_trips') }}
)
select
    trip_id,
    departure,
    cast(dep_lat as double)            as dep_lat,
    cast(dep_lng as double)            as dep_lng,
    destination,
    cast(des_lat as double)            as des_lat,
    cast(des_lng as double)            as des_lng,
    cast(distance_km as double)        as distance_km,
    cast(fuel_l_per_100km as double)   as observed_l_per_100km,
    cast(year as integer)              as trip_year,
    cast(month as integer)             as trip_month,
    cast(minutes_driven as integer)    as minutes_driven,
    country                            as destination_country
from source
