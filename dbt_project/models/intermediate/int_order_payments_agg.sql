with payments as (
    select * from {{ ref('stg_olist_order_payments') }}
),

payment_type_totals as (
    select
        order_id,
        payment_type,
        sum(payment_value) as type_payment_value,
        min(payment_sequential) as first_payment_sequential
    from payments
    group by order_id, payment_type
),

primary_payment as (
    select
        order_id,
        payment_type as primary_payment_type,
        row_number() over (
            partition by order_id
            order by
                type_payment_value desc,
                first_payment_sequential asc
        ) as row_num
    from payment_type_totals
),

order_totals as (
    select
        order_id,
        cast(sum(payment_value) as numeric(12,2)) as total_payment_value_brl,
        count(*) as payment_rows_count,
        max(payment_installments) as max_installments
    from payments
    group by order_id
)

select
    t.order_id,
    t.total_payment_value_brl,
    t.payment_rows_count,
    t.max_installments,
    p.primary_payment_type
from order_totals t
inner join primary_payment p
    on t.order_id = p.order_id
    and p.row_num = 1
