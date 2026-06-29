-- THE decision table: for each EV, replacing your Corolla, per year ->
-- energy saved, CO2 avoided, capital premium, payback, and EUR per tonne of CO2.
--
-- Honest matchup (overridable with --vars):
--   EVs use real-world community consumption (spritmonitor)
--   Corolla uses YOUR actual measured driving (actual)
-- Annualized using the real time-span of your data, so it stays correct whether
-- you load 6 months or 6 years of trips.
{% set ev_source = var('ev_source', 'spritmonitor') %}
{% set base_source = var('baseline_source', 'actual') %}
{% set horizon = var('horizon_years', 8) %}

with fct as (
    select * from {{ ref('fct_trip_car_scenarios') }}
),
prices as (
    select car_id, purchase_price_eur from {{ ref('dim_car') }}
),
span as (
    select (max(ym) - min(ym) + 1) / 12.0 as years_span
    from (select distinct trip_year * 12 + trip_month as ym from fct)
),
ev_tot as (
    select car_id, make, model,
           sum(distance_km)   as tot_km,
           sum(energy_cost_eur) as tot_cost,
           sum(co2_kg)        as tot_co2
    from fct
    where is_bev and source = '{{ ev_source }}'
    group by 1, 2, 3
),
base_tot as (
    select sum(energy_cost_eur) as tot_cost,
           sum(co2_kg)          as tot_co2
    from fct
    where car_id = 'corolla' and source = '{{ base_source }}'
)
select
    ev.car_id,
    ev.make,
    ev.model,
    round(ev.tot_km / s.years_span, 0)                                     as annual_km,
    round(b.tot_cost / s.years_span, 0)                                    as corolla_annual_cost_eur,
    round(ev.tot_cost / s.years_span, 0)                                   as ev_annual_cost_eur,
    round((b.tot_cost - ev.tot_cost) / s.years_span, 0)                    as annual_energy_saving_eur,
    round((b.tot_co2 - ev.tot_co2) / s.years_span, 0)                      as annual_co2_avoided_kg,
    p_ev.purchase_price_eur                                               as ev_price_eur,
    p_co.purchase_price_eur                                               as corolla_price_eur,
    (p_ev.purchase_price_eur - p_co.purchase_price_eur)                   as capital_premium_eur,
    round(
        (p_ev.purchase_price_eur - p_co.purchase_price_eur)
        / nullif((b.tot_cost - ev.tot_cost) / s.years_span, 0), 1)        as payback_years,
    {{ horizon }}                                                         as horizon_years,
    -- green premium: net extra cost over the horizon per tonne of CO2 avoided.
    -- positive = you pay this much per tonne; negative = it pays for itself.
    round(
        ( (p_ev.purchase_price_eur - p_co.purchase_price_eur)
          - ((b.tot_cost - ev.tot_cost) / s.years_span) * {{ horizon }} )
        / nullif(((b.tot_co2 - ev.tot_co2) / s.years_span / 1000.0) * {{ horizon }}, 0), 0)
                                                                          as green_premium_eur_per_tonne
from ev_tot ev
cross join base_tot b
cross join span s
join prices p_ev on p_ev.car_id = ev.car_id
join prices p_co on p_co.car_id = 'corolla'
order by green_premium_eur_per_tonne
