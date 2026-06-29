-- Grain: one row per trip x car x source.
-- Sources:
--   wltp         -> lab baseline, gets the temperature multiplier applied
--   spritmonitor -> community real-world average, already all-conditions (factor = 1)
--   actual       -> the Corolla ONLY: this car's own measured fuel per trip (factor = 1)
-- "Selecting a car" = filter car_id. "Official vs real-world vs mine" = filter source.
with trips as (
    select * from {{ ref('int_trips_classified') }}
),
trip_temp as (
    select * from {{ ref('int_trip_temperature') }}
),
cars as (
    select * from {{ ref('stg_cars') }}
),
cons as (
    select * from {{ ref('stg_car_consumption') }}
),
prices as (
    select
        max(case when energy_type = 'petrol_l'             then eur_per_unit    end) as petrol_eur_l,
        max(case when energy_type = 'electricity_home_kwh' then eur_per_unit    end) as elec_eur_kwh,
        max(case when energy_type = 'petrol_l'             then co2_kg_per_unit end) as petrol_co2_kg_l,
        max(case when energy_type = 'electricity_home_kwh' then co2_kg_per_unit end) as elec_co2_kg_kwh
    from {{ ref('stg_energy_prices') }}
),

-- 1) reference scenarios: every car under WLTP and community Spritmonitor figures
reference_scenarios as (
    select
        t.trip_id, t.trip_year, t.trip_month, t.distance_km, t.trip_type,
        t.is_cross_border, t.destination_country, t.region,
        c.car_id, c.make, c.model, c.powertrain, c.is_bev,
        cn.source,
        cn.consumption_avg,
        tt.avg_temp_c,
        case
            when cn.source = 'spritmonitor' then 1.0
            when c.is_bev and c.has_heat_pump then tt.factor_bev_heatpump
            when c.is_bev                     then tt.factor_bev_no_heatpump
            else tt.factor_ice
        end as season_factor
    from trips t
    join trip_temp tt on tt.trip_id = t.trip_id
    cross join cars c
    join cons cn on cn.car_id = c.car_id
),

-- 2) the Corolla's ACTUAL measured fuel, per trip (compare your real driving
--    against WLTP and the Spritmonitor community average)
actual_scenarios as (
    select
        t.trip_id, t.trip_year, t.trip_month, t.distance_km, t.trip_type,
        t.is_cross_border, t.destination_country, t.region,
        c.car_id, c.make, c.model, c.powertrain, c.is_bev,
        'actual'                  as source,
        t.observed_l_per_100km    as consumption_avg,
        tt.avg_temp_c,
        1.0                       as season_factor
    from trips t
    join trip_temp tt on tt.trip_id = t.trip_id
    join cars c on c.car_id = 'corolla'
),

unioned as (
    select * from reference_scenarios
    union all
    select * from actual_scenarios
),

energy as (
    select
        *,
        case when is_bev then distance_km / 100.0 * consumption_avg * season_factor end as kwh_used,
        case when not is_bev then distance_km / 100.0 * consumption_avg * season_factor end as litres_used
    from unioned
)
select
    trip_id || '-' || car_id || '-' || source as scenario_id,
    trip_id, trip_year, trip_month, distance_km, trip_type,
    is_cross_border, destination_country, region,
    car_id, make, model, powertrain, is_bev, source,
    round(avg_temp_c, 1)                                          as avg_temp_c,
    round(season_factor, 3)                                       as season_factor,
    round(coalesce(kwh_used, 0), 3)                               as kwh_used,
    round(coalesce(litres_used, 0), 3)                            as litres_used,
    round(case when is_bev then kwh_used * (select elec_eur_kwh from prices)
               else litres_used * (select petrol_eur_l from prices) end, 2)   as energy_cost_eur,
    round(case when is_bev then kwh_used * (select elec_co2_kg_kwh from prices)
               else litres_used * (select petrol_co2_kg_l from prices) end, 3) as co2_kg
from energy
