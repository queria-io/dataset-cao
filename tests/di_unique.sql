-- 1 系列の 1 か月は 1 行
select adjustment, judgment, survey_month, region, field, sector, count(*) as n
from {{ ref('di') }}
group by all
having n > 1
