-- 同じ月・同じ判断の CSV の 1 行は 1 回答
select survey_month, judgment, line_number, count(*) as n
from {{ ref('comments') }}
group by all
having n > 1
