with ranked_reviews as (
    select
        order_id,
        review_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp,
        count(*) over (partition by order_id) as reviews_count_for_order,
        row_number() over (
            partition by order_id
            order by
                review_answer_timestamp desc nulls last,
                review_creation_date desc nulls last,
                review_id asc
        ) as row_num
    from {{ ref('stg_olist_order_reviews') }}
)

select
    order_id,
    review_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp,
    reviews_count_for_order,
    (review_comment_title is not null or review_comment_message is not null) as has_comment,
    (review_score <= 2) as is_negative_review
from ranked_reviews
where row_num = 1
