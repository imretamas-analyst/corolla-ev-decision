with source as (
    select * from {{ ref('temperature_factor_curve') }}
)
select
    cast(temp_min as double)                as temp_min,
    cast(temp_max as double)                as temp_max,
    cast(factor_ice as double)              as factor_ice,
    cast(factor_bev_heatpump as double)     as factor_bev_heatpump,
    cast(factor_bev_no_heatpump as double)  as factor_bev_no_heatpump
from source
