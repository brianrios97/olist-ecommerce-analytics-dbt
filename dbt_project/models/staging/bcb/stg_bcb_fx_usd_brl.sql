with source as (
    select * from {{ source('bcb', 'bcb_fx_usd_brl') }}
),

renamed as (
    select
        to_date(nullif(trim(data), ''), 'DD/MM/YYYY') as fx_date,
        cast(nullif(trim(valor), '') as numeric(10,4)) as usd_brl_rate,
        cast(series_code as integer) as series_code
    from source
)

select * from renamed
