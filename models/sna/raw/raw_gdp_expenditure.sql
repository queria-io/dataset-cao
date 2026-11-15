{# data/sna/gdp_expenditure.csv を、pipelines が書いた列と値のまま読む #}

select *
from read_csv('data/sna/gdp_expenditure.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
