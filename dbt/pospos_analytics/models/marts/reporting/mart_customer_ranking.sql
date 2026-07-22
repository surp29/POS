-- Data mart cho bao cao "xep hang khach hang theo doanh thu". Khach hang chua dinh danh
-- (customer_id = -1, xem dim_customer.sql) van xuat hien nhu 1 dong gop chung — huu ich de
-- thay ty le doanh thu den tu khach vang lai so voi khach da co ho so.

select
    c.customer_id,
    c.customer_code,
    c.customer_name,
    count(distinct s.invoice_id)                                       as invoice_count,
    sum(s.line_total)                                                  as total_revenue,
    sum(s.line_total) / nullif(count(distinct s.invoice_id), 0)        as avg_invoice_value,
    max(s.date_key)                                                    as last_purchase_date
from {{ ref('fact_sales') }} s
join {{ ref('dim_customer') }} c
    on s.customer_id = c.customer_id
where s.payment_status = 'Đã thanh toán'
group by 1, 2, 3
order by total_revenue desc
