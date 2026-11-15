{# data/economy_watchers/di.csv を、pipelines が書いた列と値のまま読む #}

select *
from read_csv('data/economy_watchers/di.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
