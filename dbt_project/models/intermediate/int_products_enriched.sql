with products as (
    select * from {{ ref('stg_olist_products') }}
),

translations as (
    select * from {{ ref('stg_olist_category_translation') }}
),

enriched as (
    select
        p.product_id,
        p.product_category_name,
        coalesce(
            t.product_category_name_english,
            case
                when p.product_category_name = 'pc_gamer' then 'pc_gamer'
                when p.product_category_name in (
                    'portateis_cozinha_e_preparadores_de_alimentos',
                    'portateis_cozinha_e_preparadores_de_alimentos_e_bebidas'
                ) then 'kitchen_portable_appliances'
            end,
            'unknown'
        ) as product_category_name_english,
        p.product_name_length,
        p.product_description_length,
        p.product_photos_qty,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm
    from products p
    left join translations t
        on p.product_category_name = t.product_category_name
)

select * from enriched
