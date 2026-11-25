with source as (
    select * from {{ source('olist', 'olist_sellers') }}
),

renamed as (
    select
        nullif(trim(seller_id), '') as seller_id,
        cast(nullif(trim(seller_zip_code_prefix), '') as text) as seller_zip_code_prefix,
        nullif(trim(seller_city), '') as seller_city,
        nullif(trim(seller_state), '') as seller_state
    from source
)

select * from renamed
