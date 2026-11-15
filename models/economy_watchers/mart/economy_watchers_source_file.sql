{{ config(alias='source_file') }}

select * from {{ ref('stg_economy_watchers_source_file') }}
order by url
