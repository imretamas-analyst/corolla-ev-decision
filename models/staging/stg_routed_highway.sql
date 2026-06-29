{{ config(enabled = var('use_routed_highway', false)) }}
select
    trip_id,
    cast(routed_total_km as double)   as routed_total_km,
    cast(routed_highway_km as double) as routed_highway_km
from {{ ref('trip_routed_highway') }}
