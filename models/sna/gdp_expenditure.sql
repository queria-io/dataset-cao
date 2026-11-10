{# 四半期別 GDP 速報の国内総生産（支出側）と各需要項目 (data/sna/gdp_expenditure.csv) を型付けする #}

select
    release,
    cast(release_date as date) as release_date,
    measure,
    adjustment,
    frequency,
    cast(year as integer) as year,
    cast(quarter as integer) as quarter,
    case frequency
        when 'quarter' then make_date(cast(year as integer), cast(quarter as integer) * 3 - 2, 1)
        when 'fiscal_year' then make_date(cast(year as integer), 4, 1)
        when 'calendar_year' then make_date(cast(year as integer), 1, 1)
    end as period_start,
    item,
    cast(item_level as integer) as item_level,
    cast(value as double) as value,
    unit
from read_csv('data/sna/gdp_expenditure.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
