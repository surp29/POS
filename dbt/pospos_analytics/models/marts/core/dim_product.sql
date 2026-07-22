with products as (
    select * from {{ ref('stg_products') }}
),

groups as (
    select * from {{ ref('stg_product_groups') }}
)

select
    p.product_id,
    p.product_code,
    p.product_name,
    -- products.nhom_id la FK "chinh thuc", nhung nhieu ban ghi cu chi co nhom_sp (text) —
    -- coalesce ve nhom_sp roi ve 1 gia tri mac dinh de khong mat san pham chua duoc gan nhom
    coalesce(g.product_group_name, p.product_group_name_raw, 'Chua phan nhom') as product_group_name,
    p.unit,
    p.status,
    p.sale_price,
    p.list_price,
    p.cost_price,
    p.stock_qty
from products p
left join groups g on p.product_group_id = g.product_group_id
