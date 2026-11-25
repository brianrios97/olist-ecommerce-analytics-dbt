with source as (
    select * from {{ source('olist', 'olist_order_reviews') }}
),

renamed as (
    select
        nullif(trim(review_id), '') as review_id,
        nullif(trim(order_id), '') as order_id,
        cast(nullif(trim(review_score), '') as integer) as review_score,
        nullif(trim(review_comment_title), '') as review_comment_title,
        nullif(trim(review_comment_message), '') as review_comment_message,
        cast(nullif(trim(review_creation_date), '') as timestamp) as review_creation_date,
        cast(nullif(trim(review_answer_timestamp), '') as timestamp) as review_answer_timestamp
    from source
)

select * from renamed
