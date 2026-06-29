with source as (
    select * from {{ ref('raw_cars') }}
)
select
    car_id,
    make,
    model,
    powertrain,
    cast(battery_kwh_gross as double) as battery_kwh_gross,
    cast(wltp_consumption as double)   as wltp_consumption,
    consumption_unit,
    cast(purchase_price_eur as double) as purchase_price_eur,
    cast(has_heat_pump as boolean)     as has_heat_pump,
    (powertrain = 'BEV')               as is_bev
from source
