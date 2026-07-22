with source as (
    select * from {{ source('pospos', 'products') }}
)

select
    id                as product_id,
    ma_sp             as product_code,
    ten_sp            as product_name,
    nhom_id           as product_group_id,
    nhom_sp           as product_group_name_raw,   -- ten nhom luu truc tiep tren product, co the lech voi product_groups
    so_luong          as stock_qty,
    gia_ban           as sale_price,
    gia_chung         as list_price,
    gia_von           as cost_price,
    don_vi            as unit,
    trang_thai        as status,
    image_url
from source
