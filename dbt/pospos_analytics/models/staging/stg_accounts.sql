-- Chuan hoa ten khach hang de co the join voi invoices.nguoi_mua (chi la text tu do,
-- khong co FK sang accounts trong schema OLTP goc). customer_name_key la khoa ghep noi
-- dung o dim_customer / fact_sales — xem giai thich chi tiet trong models/marts/core/dim_customer.sql
with source as (
    select * from {{ source('pospos', 'accounts') }}
)

select
    id                                                          as customer_id,
    ma_khach_hang                                               as customer_code,
    ten_tk                                                      as customer_name,
    lower(trim(regexp_replace(ten_tk, '\s+', ' ', 'g')))        as customer_name_key,
    email,
    so_dt          as phone,
    dia_chi        as address,
    ngay_sinh      as birth_date,
    trang_thai     as is_active
from source
