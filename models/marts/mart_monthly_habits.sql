-- Driving habits by calendar month (aggregated across all years of data).
-- Surfaces seasonality, holiday-season multi-country months, and a HIGHWAY PROXY.
-- NOTE: highway share is ESTIMATED from average trip speed (>= 80 km/h => highway-
-- dominant) because the measured highwayDistanceInKm field is not in the loaded
-- data. Import the raw telematics tab to replace this estimate with measured values.
with base as (
    select *,
        distance_km / nullif(minutes_driven / 60.0, 0) as avg_speed_kmh
    from {{ ref('int_trips_classified') }}
    where minutes_driven > 0 and distance_km > 0
)
select
    trip_month                                                              as month,
    count(*)                                                                as trips,
    round(sum(distance_km), 0)                                             as total_km,
    round(sum(distance_km) / nullif(sum(minutes_driven) / 60.0, 0), 1)     as avg_speed_kmh,
    count(distinct destination_country)                                    as distinct_countries,
    sum(case when is_cross_border then 1 else 0 end)                       as cross_border_trips,
    round(100.0 * sum(case when avg_speed_kmh >= 80 then distance_km else 0 end)
          / nullif(sum(distance_km), 0), 0)                                as est_highway_share_pct
from base
group by 1
order by 1
