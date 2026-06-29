with source as (
    select * from {{ ref('energy_prices') }}
)
select
    energy_type,
    cast(eur_per_unit as double)       as eur_per_unit,
    cast(co2_kg_per_unit as double)    as co2_kg_per_unit
from source
