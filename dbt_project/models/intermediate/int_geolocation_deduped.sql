with geo as (
    select
        geolocation_zip_code_prefix as zip_code_prefix,
        geolocation_lat,
        geolocation_lng,
        lower(geolocation_city) as city,
        upper(geolocation_state) as state
    from {{ ref('stg_olist_geolocation') }}
    where geolocation_zip_code_prefix is not null
),

deduped as (
    select
        zip_code_prefix,
        cast(avg(geolocation_lat) as numeric(10,6)) as geolocation_lat,
        cast(avg(geolocation_lng) as numeric(10,6)) as geolocation_lng,
        mode() within group (order by city) as city,
        mode() within group (order by state) as state
    from geo
    group by zip_code_prefix
)

select * from deduped
