-- Fuel use by road type, as two clean, well-defined buckets plus the overall figure.
--   city    = trips that stay essentially off the motorway (<5% highway)
--   highway = trips that are mostly motorway (>=60% highway)
--   overall = all driving combined (the honest headline)
-- The old "mixed" bucket was dropped: a 95%-motorway trip with a short city tail
-- landed there and averaged to a figure that described no real kind of driving.
-- Mixed trips still count fully toward 'overall'.
{% if var('use_routed_highway', false) %}
with trip as (
    select
        c.distance_km,
        c.distance_km / 100.0 * c.observed_l_per_100km as fuel_liters,
        h.highway_km / nullif(c.distance_km, 0)        as highway_share
    from {{ ref('int_trips_classified') }} c
    join {{ ref('int_trip_highway') }} h on h.trip_id = c.trip_id
    where c.distance_km > 0
)
select 'city'    as road_type, count(*) as trips, round(sum(distance_km),0) as total_km,
       round(sum(fuel_liters)/nullif(sum(distance_km),0)*100,2) as fuel_l_per_100km
from trip where highway_share < 0.05
union all
select 'highway', count(*), round(sum(distance_km),0),
       round(sum(fuel_liters)/nullif(sum(distance_km),0)*100,2)
from trip where highway_share >= 0.60
union all
select 'overall', count(*), round(sum(distance_km),0),
       round(sum(fuel_liters)/nullif(sum(distance_km),0)*100,2)
from trip
{% else %}
with t as (select * from {{ ref('stg_telematics') }})
select 'city'    as road_type, count(*) as trips, round(sum(total_km),0) as total_km,
       round(sum(fuel_liters)/nullif(sum(total_km),0)*100,2) as fuel_l_per_100km
from t where highway_share < 0.05
union all
select 'highway', count(*), round(sum(total_km),0),
       round(sum(fuel_liters)/nullif(sum(total_km),0)*100,2)
from t where highway_share >= 0.60
union all
select 'overall', count(*), round(sum(total_km),0),
       round(sum(fuel_liters)/nullif(sum(total_km),0)*100,2)
from t
{% endif %}
