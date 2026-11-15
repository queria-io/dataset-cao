{# 景気ウォッチャー調査の DI を型付けする #}

select
    adjustment,
    judgment,
    make_date(cast(year as integer), cast(month as integer), 1) as survey_month,
    region,
    field,
    nullif(sector, '') as sector,
    cast(di as double) as di,
    source_sha256,
    source_sheet,
    cast(source_row as integer) as source_row
from {{ ref('raw_di') }}
