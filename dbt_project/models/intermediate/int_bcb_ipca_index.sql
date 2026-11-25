with monthly_ipca as (
    select
        reference_month,
        ipca_monthly_pct,
        exp(
            sum(ln(1.0 + ipca_monthly_pct / 100.0)) over (
                order by reference_month
                rows between unbounded preceding and current row
            )
        ) as raw_compound_index
    from {{ ref('stg_bcb_ipca') }}
),

base_index as (
    select
        raw_compound_index as base_2018_08_index
    from monthly_ipca
    where reference_month = date '2018-08-01'
),

rebased as (
    select
        m.reference_month,
        m.ipca_monthly_pct,
        (m.raw_compound_index / b.base_2018_08_index) * 100.0 as ipca_index_base_2018_08
    from monthly_ipca m
    cross join base_index b
)

select
    reference_month,
    ipca_monthly_pct,
    ipca_index_base_2018_08,
    100.0 / ipca_index_base_2018_08 as deflator_to_2018_08
from rebased
order by reference_month
