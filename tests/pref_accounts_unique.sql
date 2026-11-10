-- 1 表の 1 項目・1 地域・1 年度は 1 行
select table_kind, table_number, item, area_name, fiscal_year, count(*) as n
from {{ ref('observations') }}
group by all
having n > 1
