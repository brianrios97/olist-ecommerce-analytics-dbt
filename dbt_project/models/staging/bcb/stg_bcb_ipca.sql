with source as (
    select * from {{ source('bcb', 'bcb_ipca') }}
),

renamed as (
    select
        to_date(nullif(trim(data), ''), 'DD/MM/YYYY') as reference_month,
        cast(nullif(trim(valor), '') as numeric(10,4)) as ipca_monthly_pct,
        cast(series_code as integer) as series_code
    from source
)

select * from renamed
