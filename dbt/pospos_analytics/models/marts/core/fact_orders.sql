-- Grain: 1 dong = 1 order_item. Fact "pipeline" — theo doi yeu cau cua khach truoc khi
-- (neu co) chuyen thanh hoa don. Tach rieng khoi fact_sales vi orders khong dam bao da
-- thu duoc tien; gop chung 2 fact se lam sai lech so lieu doanh thu.

with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
)

select
    i.order_item_id                                as order_line_id,
    o.order_id,
    o.order_code,
    o.order_date                                   as date_key,
    i.product_id,
    coalesce(o.buyer_customer_id, c.customer_id, -1) as customer_id,
    o.buyer_name_raw                               as customer_name_at_order,
    o.order_status,
    i.quantity,
    i.unit_price,
    i.line_total
from items i
join orders o
    on i.order_id = o.order_id
left join customers c
    on o.buyer_customer_id is null
    and o.buyer_name_key = c.customer_name_key
