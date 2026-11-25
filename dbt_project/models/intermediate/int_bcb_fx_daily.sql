with date_spine as (
    select
        generate_series(
            date '2016-08-01',
            date '2018-12-31',
            interval '1 day'
        )::date as fx_date
),

joined as (
    select
        d.fx_date,
        f.usd_brl_rate as raw_usd_brl_rate,
        (f.usd_brl_rate is not null) as is_bcb_business_day,
        count(f.usd_brl_rate) over (
            order by d.fx_date
            rows between unbounded preceding and current row
        ) as rate_group
    from date_spine d
    left join {{ ref('stg_bcb_fx_usd_brl') }} f
        on d.fx_date = f.fx_date
),

forward_filled as (
    select
        fx_date,
        first_value(raw_usd_brl_rate) over (
            partition by rate_group
            order by fx_date
        ) as usd_brl_rate,
        is_bcb_business_day
    from joined
)

select
    fx_date,
    cast(usd_brl_rate as numeric(10,4)) as usd_brl_rate,
    is_bcb_business_day
from forward_filled
order by fx_date
