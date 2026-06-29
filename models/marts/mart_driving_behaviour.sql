-- Overall driving-behaviour stats from measured telematics.
with t as (select * from {{ ref('stg_telematics') }})
select
    count(*)                                                       as trips,
    round(100.0 * sum(highway_km) / nullif(sum(total_km), 0), 0)   as highway_share_pct,
    round(100.0 * sum(overspeed_km) / nullif(sum(total_km), 0), 1) as overspeed_share_pct,
    round(sum(total_km) / nullif(sum(total_sec) / 3600.0, 0), 1)   as avg_speed_kmh,
    max(max_speed)                                                 as top_speed_kmh,
    round(100.0 * sum(idle_sec) / nullif(sum(total_sec), 0), 1)    as idle_time_pct,
    round(sum(hard_accel) / nullif(sum(total_km), 0) * 100, 2)     as hard_accel_per_100km,
    round(sum(hard_brake) / nullif(sum(total_km), 0) * 100, 2)     as hard_brake_per_100km,
    round(100.0 * sum(case when night_trip then 1 else 0 end) / count(*), 0) as night_trip_pct
from t
