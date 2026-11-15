{{ config(alias='source_file') }}

select * from {{ ref('stg_pref_accounts_source_file') }}
order by url
