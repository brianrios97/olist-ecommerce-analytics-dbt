with source as (
    select * from {{ source('olist', 'olist_customers') }}
),

renamed as (
    select
        nullif(trim(customer_id), '') as customer_id,
        nullif(trim(customer_unique_id), '') as customer_unique_id,
        cast(nullif(trim(customer_zip_code_prefix), '') as text) as customer_zip_code_prefix,
        nullif(trim(customer_city), '') as customer_city,
        nullif(trim(customer_state), '') as customer_state
    from source
)

select * from renamed
