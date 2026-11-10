-- 1 項目の 1 期は 1 行
select measure, adjustment, frequency, period_start, item, count(*) as n
from {{ ref('gdp_expenditure') }}
group by all
having n > 1
