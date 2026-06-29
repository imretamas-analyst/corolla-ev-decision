with source as (
    select * from {{ ref('car_consumption') }}
)
select
    car_id,
    source,
    consumption_unit,
    cast(consumption_avg as double)    as consumption_avg,
    cast(sample_size as integer)       as sample_size,
    cast(consumption_min as double)    as consumption_min,
    cast(consumption_max as double)    as consumption_max,
    cast(verified as boolean)          as verified
from source
