{# pipelines/economy_watchers.py が書いた data/economy_watchers/source_file.ndjson（取得の記録）をそのまま読む。 #}

select *
from read_json(
    'data/economy_watchers/source_file.ndjson',
    format = 'newline_delimited',
    columns = {
        url: 'varchar', page_url: 'varchar', sha256: 'varchar', bytes: 'bigint', media_type: 'varchar',
        retrieved_at: 'varchar', etag: 'varchar', last_modified: 'varchar'
    }
)
