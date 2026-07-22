with source as (
    select * from {{ source('pospos', 'warehouses') }}
)

select
    id              as warehouse_lot_id,
    ma_kho          as warehouse_code,
    ten_kho         as warehouse_name,
    product_id,
    ma_sp           as product_code_raw,   -- giu de tuong thich, uu tien join qua product_id
    gia_nhap        as import_price,
    so_luong        as lot_qty,
    trang_thai      as status
from source
