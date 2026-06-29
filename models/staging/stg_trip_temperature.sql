-- Real per-trip mean temperature produced by scripts/fetch_temperature.py.
with source as (
    select * from {{ ref('trip_temperature') }}
)
select
    trip_id,
    cast(date as varchar)       as trip_date,
    cast(avg_temp_c as double)  as avg_temp_c
from source
