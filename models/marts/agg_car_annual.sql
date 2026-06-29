-- Roll-up per car x source: what a full year of THESE trips would cost & emit.
-- This is what the dashboard headline numbers read from.
with s as (
    select * from {{ ref('fct_trip_car_scenarios') }}
)
select
    car_id,
    make,
    model,
    powertrain,
    source,
    count(distinct trip_id)            as trips,
    round(sum(distance_km), 1)         as total_km,
    round(sum(kwh_used), 1)            as total_kwh,
    round(sum(litres_used), 1)         as total_litres,
    round(sum(energy_cost_eur), 2)     as total_energy_cost_eur,
    round(sum(co2_kg), 1)              as total_co2_kg
from s
group by 1, 2, 3, 4, 5
order by source, total_energy_cost_eur
