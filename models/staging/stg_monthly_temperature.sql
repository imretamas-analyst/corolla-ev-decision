with source as (
    select * from {{ ref('monthly_temperature') }}
)
select
    region,
    cast(year as integer)       as year,
    cast(month as integer)      as month,
    cast(avg_temp_c as double)  as avg_temp_c
from source
