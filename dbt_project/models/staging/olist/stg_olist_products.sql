with source as (
    select * from {{ source('olist', 'olist_products') }}
),

renamed as (
    select
        nullif(trim(product_id), '') as product_id,
        nullif(trim(product_category_name), '') as product_category_name,
        cast(nullif(trim(product_name_lenght), '') as integer) as product_name_length,
        cast(nullif(trim(product_description_lenght), '') as integer) as product_description_length,
        cast(nullif(trim(product_photos_qty), '') as integer) as product_photos_qty,
        cast(nullif(trim(product_weight_g), '') as integer) as product_weight_g,
        cast(nullif(trim(product_length_cm), '') as integer) as product_length_cm,
        cast(nullif(trim(product_height_cm), '') as integer) as product_height_cm,
        cast(nullif(trim(product_width_cm), '') as integer) as product_width_cm
    from source
)

select * from renamed
