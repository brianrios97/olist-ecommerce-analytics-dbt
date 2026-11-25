with items as (
    select * from {{ ref('stg_olist_order_items') }}
),

aggregated as (
    select
        order_id,
        count(*) as items_count,
        count(distinct product_id) as distinct_products_count,
        count(distinct seller_id) as distinct_sellers_count,
        cast(sum(price) as numeric(12,2)) as gross_items_value_brl,
        cast(sum(freight_value) as numeric(12,2)) as freight_value_brl,
        cast(sum(price + freight_value) as numeric(12,2)) as gross_order_value_brl
    from items
    group by order_id
)

select * from aggregated
