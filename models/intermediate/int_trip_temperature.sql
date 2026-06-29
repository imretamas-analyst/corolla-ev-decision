-- One row per trip: the temperature it was driven in (REAL measured temperature
-- when available, monthly climatology as fallback), plus the consumption
-- multiplier that temperature implies for each powertrain type.
with trips as (
    select * from {{ ref('int_trips_classified') }}
),
measured as (
    select * from {{ ref('stg_trip_temperature') }}
),
climate as (
    select * from {{ ref('stg_monthly_temperature') }}
),
curve as (
    select * from {{ ref('stg_temperature_factor') }}
),
resolved as (
    select
        t.trip_id,
        coalesce(m.avg_temp_c, cl.avg_temp_c)                       as avg_temp_c,
        case when m.avg_temp_c is not null then 'measured'
             else 'climatology' end                                  as temp_source
    from trips t
    left join measured m on m.trip_id = t.trip_id
    left join climate  cl on cl.region = t.region
                         and cl.year   = t.trip_year
                         and cl.month  = t.trip_month
)
select
    r.trip_id,
    r.avg_temp_c,
    r.temp_source,
    c.factor_ice,
    c.factor_bev_heatpump,
    c.factor_bev_no_heatpump
from resolved r
left join curve c
    on r.avg_temp_c >= c.temp_min
   and r.avg_temp_c <  c.temp_max
