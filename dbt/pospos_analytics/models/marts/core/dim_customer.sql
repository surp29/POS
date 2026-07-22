-- LUU Y VE CHAT LUONG DU LIEU (data-quality note):
-- Schema OLTP goc KHONG co foreign key giua invoices/orders va accounts — nguoi_mua /
-- thong_tin_kh chi la 1 cot text nhan vien go tay luc ban hang. Nghia la mot khach hang
-- da co ho so trong `accounts` van co the bi ghi hoa don duoi 1 cai ten hoi khac (thieu dau,
-- viet tat, sai chinh ta...) va se KHONG match duoc.
--
-- Cach xu ly o day: chuan hoa ca 2 phia ve 1 "match key" (lower + trim + gop khoang trang,
-- xem stg_accounts.sql / stg_invoices.sql), roi join fact_sales voi key nay thay vi ten goc.
-- Nhung ten khong khop voi bat ky account nao (khach vang lai, ten viet khac...) se roi vao
-- 1 dong "khach le / chua dinh danh" duy nhat (customer_id = -1) thay vi bi loai khoi fact —
-- day la lua chon co chu dich: khong danh mat doanh thu, nhung van tach rieng phan chua
-- chuan hoa duoc de dashboard/nguoi doc bao cao thay ro ty le nay.

with accounts as (
    select * from {{ ref('stg_accounts') }}
),

known_customers as (
    select
        customer_id,
        customer_code,
        customer_name,
        customer_name_key,
        email,
        phone,
        is_active,
        'accounts' as customer_source
    from accounts
),

unknown_customer as (
    select
        -1                              as customer_id,
        'UNKNOWN'                       as customer_code,
        'Khach le / chua dinh danh'     as customer_name,
        '__unknown__'                   as customer_name_key,
        cast(null as varchar)           as email,
        cast(null as varchar)           as phone,
        true                            as is_active,
        'synthetic'                     as customer_source
)

select * from known_customers
union all
select * from unknown_customer
