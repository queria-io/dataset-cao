{# 景気ウォッチャー調査の景気判断理由集 (data/economy_watchers/comments.csv) を型付けする。1 行が 1 回答 #}

select
    make_date(cast(survey_year as integer), cast(survey_month as integer), 1) as survey_month,
    cast(release_date as date) as release_date,
    judgment,
    region,
    field,
    mark,
    assessment,
    industry,
    nullif(reason, '') as reason,
    comment,
    cast(line_number as integer) as line_number
from read_csv('data/economy_watchers/comments.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
