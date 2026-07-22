with source as (
    select * from {{ source('pospos', 'product_groups') }}
)

select
    id       as product_group_id,
    ten_nhom as product_group_name,
    mo_ta    as product_group_description
from source
