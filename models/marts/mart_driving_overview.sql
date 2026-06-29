-- Single-row headline stats over the whole dataset.
with base as (
    select *,
        trip_year * 12 + trip_month as ym,
        distance_km / nullif(minutes_driven / 60.0, 0) as avg_speed_kmh
    from {{ ref('int_trips_classified') }}
    where minutes_driven > 0 and distance_km > 0
)
select
    round(sum(distance_km), 0)                                             as total_km,
    count(*)                                                               as total_trips,
    round((max(ym) - min(ym) + 1) / 12.0, 2)                              as years_span,
    round(sum(distance_km) / nullif(sum(minutes_driven) / 60.0, 0), 1)     as avg_speed_kmh,
    count(distinct destination_country)                                    as countries_visited,
    round(100.0 * sum(case when is_cross_border then 1 else 0 end) / count(*), 0) as cross_border_pct,
    round(100.0 * sum(case when avg_speed_kmh >= 80 then distance_km else 0 end)
          / nullif(sum(distance_km), 0), 0)                                as est_highway_share_pct
from base
