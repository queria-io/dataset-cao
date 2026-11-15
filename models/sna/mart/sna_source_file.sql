{{ config(alias='source_file') }}

select * from {{ ref('stg_sna_source_file') }}
order by url
