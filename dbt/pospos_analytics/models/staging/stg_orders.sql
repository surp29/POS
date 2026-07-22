with source as (
    select * from {{ source('pospos', 'orders') }}
)

select
    id                                                          as order_id,
    ma_don_hang                                                 as order_code,
    ngay_tao                                                    as order_date,
    thong_tin_kh                                                as buyer_name_raw,
    lower(trim(regexp_replace(thong_tin_kh, '\s+', ' ', 'g')))  as buyer_name_key,
    customer_id                                                 as buyer_customer_id,  -- FK that, them sau — null tren don cu
    tong_tien                                                   as order_total,
    trang_thai                                                  as order_status
from source
