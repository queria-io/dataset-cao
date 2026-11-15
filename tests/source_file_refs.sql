-- 統計表から作ったテーブルの source_sha256 が、どれも同じスキーマの source_file の sha256 を指す
select distinct 'sna.gdp_expenditure' as table_name, source_sha256 from {{ ref('gdp_expenditure') }}
where source_sha256 not in (select sha256 from {{ ref('sna_source_file') }})
union all
select distinct 'pref_accounts.observations', source_sha256 from {{ ref('observations') }}
where source_sha256 not in (select sha256 from {{ ref('pref_accounts_source_file') }})
union all
select distinct 'economy_watchers.di', source_sha256 from {{ ref('di') }}
where source_sha256 not in (select sha256 from {{ ref('economy_watchers_source_file') }})
union all
select distinct 'economy_watchers.comments', source_sha256 from {{ ref('comments') }}
where source_sha256 not in (select sha256 from {{ ref('economy_watchers_source_file') }})
