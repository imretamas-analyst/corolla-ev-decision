-- Collapse the home-address cluster into one "Home" node (correctness + privacy),
-- classify trip type, and tag a climate region for the temperature join.
-- The home street to match is read from the HOME_STREET environment variable so the
-- real address never enters version control (defaults to the demo value 'Sample Street').
with trips as (
    select * from {{ ref('stg_trips') }}
),
labelled as (
    select
        *,
        case when departure   ilike '{{ env_var('HOME_STREET', 'Sample Street') }}%' then 'Home' else departure   end as departure_label,
        case when destination ilike '{{ env_var('HOME_STREET', 'Sample Street') }}%' then 'Home' else destination end as destination_label
    from trips
)
select
    trip_id,
    departure_label,
    destination_label,
    dep_lat, dep_lng, des_lat, des_lng,
    distance_km,
    observed_l_per_100km,
    trip_year,
    trip_month,
    minutes_driven,
    destination_country,
    (destination_country <> 'Germany')                  as is_cross_border,
    case
        when distance_km < 30  then 'local'
        when distance_km < 150 then 'regional'
        else 'long_haul'
    end                                                  as trip_type,
    -- climate region proxy (destination country). The real per-trip script keys on
    -- departure coordinates instead; see scripts/fetch_temperature.py.
    case destination_country
        when 'Germany'        then 'DE'
        when 'Czech Republic' then 'CZ'
        when 'Slovakia'       then 'SK'
        when 'Hungary'        then 'HU'
        else 'DE'
    end                                                  as region
from labelled
