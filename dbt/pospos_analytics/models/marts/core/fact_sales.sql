-- Grain: 1 dong = 1 invoice_item (1 dong san pham trong 1 hoa don da phat sinh).
-- Day la fact table doanh thu "that" — dung invoices/invoice_items (da thanh toan tai POS),
-- KHONG dung orders (chi la yeu cau, chua chac chuyen thanh doanh thu). Xem fact_orders.sql
-- cho pipeline don hang.

with items as (
    select * from {{ ref('stg_invoice_items') }}
),

invoices as (
    select * from {{ ref('stg_invoices') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
)

select
    i.invoice_item_id                              as sale_id,
    inv.invoice_id,
    inv.invoice_code,
    inv.invoice_date                               as date_key,
    i.product_id,
    -- Uu tien FK that (buyer_customer_id, tu invoices.customer_id) khi hoa don da co —
    -- chi fallback ve khop ten cho hoa don cu tao truoc khi co cot nay.
    coalesce(inv.buyer_customer_id, c.customer_id, -1) as customer_id,
    inv.buyer_name_raw                             as customer_name_at_sale,
    inv.payment_status,
    inv.payment_method,
    i.quantity,
    i.unit_price,
    i.line_total
from items i
join invoices inv
    on i.invoice_id = inv.invoice_id
left join customers c
    on inv.buyer_customer_id is null
    and inv.buyer_name_key = c.customer_name_key
