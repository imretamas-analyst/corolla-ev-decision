-- Your real driving vs the crowd vs the lab, for the Corolla.
-- 'actual' is your distance-weighted average l/100km from your own trips.
with trips as (
    select * from {{ ref('int_trips_classified') }}
),
reference as (
    select source, consumption_avg, sample_size
    from {{ ref('stg_car_consumption') }}
    where car_id = 'corolla'
),
actual as (
    select
        'actual'                                                          as source,
        round(sum(observed_l_per_100km * distance_km) / sum(distance_km), 2) as consumption_avg,
        count(*)                                                          as sample_size
    from trips
)
select source, consumption_avg as l_per_100km, sample_size from actual
union all
select source, consumption_avg as l_per_100km, sample_size from reference
order by l_per_100km
