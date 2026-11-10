{# 県民経済計算の総括表と主要系列表 (data/pref_accounts/observations.csv) を型付けする #}

select
    release,
    table_kind,
    cast(table_number as integer) as table_number,
    table_title,
    nullif(item, '') as item,
    cast(item_level as integer) as item_level,
    area_type,
    area_name,
    nullif(prefecture_code, '') as prefecture_code,
    nullif(city_code, '') as city_code,
    cast(fiscal_year as integer) as fiscal_year,
    cast(value as double) as value,
    nullif(unit, '') as unit
from read_csv('data/pref_accounts/observations.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
