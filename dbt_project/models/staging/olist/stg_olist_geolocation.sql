with source as (
    select * from {{ source('olist', 'olist_geolocation') }}
),

renamed as (
    select
        cast(nullif(trim(geolocation_zip_code_prefix), '') as text) as geolocation_zip_code_prefix,
        cast(nullif(trim(geolocation_lat), '') as numeric(10,6)) as geolocation_lat,
        cast(nullif(trim(geolocation_lng), '') as numeric(10,6)) as geolocation_lng,
        nullif(trim(geolocation_city), '') as geolocation_city,
        nullif(trim(geolocation_state), '') as geolocation_state
    from source
)

select * from renamed
