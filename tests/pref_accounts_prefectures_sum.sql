-- 総括表の県内総生産（名目）は、47 都道府県の和が全県計に一致する
with by_type as (
    select fiscal_year, area_type, sum(value) as value
    from {{ ref('observations') }}
    where table_kind = 'summary' and table_number = 1 and area_type in ('prefecture', 'national')
    group by all
)
select p.fiscal_year, p.value, n.value
from by_type as p
join by_type as n on n.fiscal_year = p.fiscal_year and n.area_type = 'national'
where p.area_type = 'prefecture' and abs(p.value - n.value) > 1
