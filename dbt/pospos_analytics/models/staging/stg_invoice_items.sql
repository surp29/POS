with source as (
    select * from {{ source('pospos', 'invoice_items') }}
)

select
    id                       as invoice_item_id,
    invoice_id,
    product_id,
    product_code             as product_code_snapshot,  -- ma/ten SP tai thoi diem ban, co the khac dim_product hien tai
    product_name             as product_name_snapshot,
    so_luong                 as quantity,
    don_gia                  as unit_price,
    total_price              as line_total
from source
