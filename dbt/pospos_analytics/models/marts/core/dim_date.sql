with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2023-01-01' as date)",
        end_date=dbt.dateadd("year", 1, "current_date")
    ) }}
)

select
    cast(date_day as date)                                      as date_key,
    cast(date_day as date)                                      as full_date,
    extract(year from date_day)::int                             as year,
    extract(quarter from date_day)::int                          as quarter,
    extract(month from date_day)::int                            as month,
    trim(to_char(date_day, 'Month'))                             as month_name,
    extract(day from date_day)::int                              as day_of_month,
    extract(isodow from date_day)::int                           as day_of_week,     -- 1=Mon .. 7=Sun
    trim(to_char(date_day, 'Day'))                                as day_name,
    extract(isodow from date_day)::int in (6, 7)                  as is_weekend
from spine
