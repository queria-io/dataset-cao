{# data/pref_accounts/observations.csv を、pipelines が書いた列と値のまま読む #}

select *
from read_csv('data/pref_accounts/observations.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
