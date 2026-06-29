-- Does the hybrid premium pay back vs a comparable non-hybrid, on YOUR driving?
-- hybrid  = your actual measured driving (source 'actual')
-- conventional = the non-hybrid car's real-world figure (source 'spritmonitor')
-- Both costed over the exact same trips, then annualized.
{% set conv = var('conventional_car_id', 'corolla_ice') %}
with agg as (select * from {{ ref('agg_car_annual') }}),
prices as (select car_id, purchase_price_eur from {{ ref('dim_car') }}),
span as (
    select (max(ym) - min(ym) + 1) / 12.0 as years_span
    from (select distinct trip_year * 12 + trip_month as ym from {{ ref('fct_trip_car_scenarios') }})
),
hybrid as (select total_energy_cost_eur c, total_km km from agg where car_id='corolla' and source='actual'),
conv   as (select total_energy_cost_eur c from agg where car_id='{{ conv }}' and source='spritmonitor')
select
    round(hybrid.km / s.years_span, 0)                                       as annual_km,
    round(hybrid.c  / s.years_span, 0)                                       as hybrid_annual_fuel_eur,
    round(conv.c    / s.years_span, 0)                                       as conventional_annual_fuel_eur,
    round((conv.c - hybrid.c) / s.years_span, 0)                             as annual_saving_eur,
    (ph.purchase_price_eur - pc.purchase_price_eur)                          as hybrid_premium_eur,
    round((ph.purchase_price_eur - pc.purchase_price_eur)
          / nullif((conv.c - hybrid.c) / s.years_span, 0), 1)               as payback_years
from hybrid cross join conv cross join span s
join prices ph on ph.car_id='corolla'
join prices pc on pc.car_id='{{ conv }}'
