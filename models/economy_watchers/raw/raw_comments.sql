{# data/economy_watchers/comments.csv を、pipelines が書いた列と値のまま読む #}

select *
from read_csv('data/economy_watchers/comments.csv', header = true, delim = ',', quote = '"', escape = '"', all_varchar = true)
