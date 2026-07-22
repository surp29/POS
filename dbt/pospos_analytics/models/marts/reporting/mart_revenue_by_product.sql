-- Data mart cho bao cao "doanh thu theo san pham" — dung cho dashboard xep hang san pham
-- ban chay, chi tinh hoa don da thanh toan.

select
    p.product_id,
    p.product_code,
    p.product_name,
    p.product_group_name,
    sum(s.quantity)                as units_sold,
    sum(s.line_total)              as revenue,
    count(distinct s.invoice_id)   as invoice_count
from {{ ref('fact_sales') }} s
join {{ ref('dim_product') }} p
    on s.product_id = p.product_id
where s.payment_status = 'Đã thanh toán'
group by 1, 2, 3, 4
order by revenue desc
