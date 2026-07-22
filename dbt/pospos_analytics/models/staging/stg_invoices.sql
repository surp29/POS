with source as (
    select * from {{ source('pospos', 'invoices') }}
)

select
    id                                                          as invoice_id,
    so_hd                                                       as invoice_code,
    ngay_hd                                                     as invoice_date,
    nguoi_mua                                                   as buyer_name_raw,
    lower(trim(regexp_replace(nguoi_mua, '\s+', ' ', 'g')))     as buyer_name_key,
    customer_id                                                 as buyer_customer_id,  -- FK that, them sau — null tren hoa don cu
    tong_tien                                                   as invoice_total,
    trang_thai                                                  as payment_status,
    hinh_thuc_tt                                                as payment_method
from source
