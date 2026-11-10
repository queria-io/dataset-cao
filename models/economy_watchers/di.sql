{# 景気ウォッチャー調査の DI (data/economy_watchers/di.csv) を型付けする #}

select
    adjustment,
    judgment,
    make_date(cast(year as integer), cast(month as integer), 1) as survey_month,
    region,
    field,
    nullif(sector, '') as sector,
    cast(di as double) as di
from read_csv('data/economy_watchers/di.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
