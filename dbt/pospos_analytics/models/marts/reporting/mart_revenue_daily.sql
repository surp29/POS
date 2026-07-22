-- Data mart cho bao cao "doanh thu theo khoang thoi gian" — 1 dong / ngay co phat sinh
-- doanh thu (chi tinh hoa don da thanh toan).

select
    s.date_key,
    d.year,
    d.month,
    d.month_name,
    d.day_of_week,
    d.is_weekend,
    count(distinct s.invoice_id)   as invoice_count,
    sum(s.line_total)              as revenue,
    sum(s.quantity)                as units_sold
from {{ ref('fact_sales') }} s
join {{ ref('dim_date') }} d
    on s.date_key = d.date_key
where s.payment_status = 'Đã thanh toán'
group by 1, 2, 3, 4, 5, 6
order by 1
