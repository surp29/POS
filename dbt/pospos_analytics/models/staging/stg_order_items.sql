with source as (
    select * from {{ source('pospos', 'order_items') }}
)

select
    id            as order_item_id,
    order_id,
    product_id,
    so_luong      as quantity,
    don_gia       as unit_price,
    total_price   as line_total
from source
