# 内閣府

内閣府が公開する経済統計を SQL で検索できるテーブルにしたデータセットです。四半期別 GDP 速報、県民経済計算、景気ウォッチャー調査を収録しています。

## 四半期別 GDP 速報（sna）

[四半期別GDP速報](https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/files_sokuhou.html)の「国内総生産（支出側）及び各需要項目」です。最新の速報の名目・実質の実額とデフレーターを、1994 年からの四半期・年度・暦年で収録します。季節調整系列は速報のたびに 1994 年まで遡って改定されるので、毎回最新の速報だけで作り直します。

## 県民経済計算（pref_accounts）

[県民経済計算](https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/files_kenmin.html)の総括表と主要系列表です。都道府県・地域ブロック・政令指定都市の県内総生産（生産側・支出側）、経済活動別県内総生産、県民所得、1 人当たり県民所得、総人口、就業者数などを年度で収録します。公表のたびに過去の年度まで遡って改定されるので、毎回最新の公表だけで作り直します。

## 景気ウォッチャー調査（economy_watchers）

[景気ウォッチャー調査](https://www5.cao.go.jp/keizai3/watcher/watcher_menu.html)の DI と景気判断理由集です。DI は現状判断・先行き判断の季節調整値と原数値を、全国の分野・業種別と地域別に月次で収録します。景気判断理由集は、景気ウォッチャーが判断に添えたコメントを 1 回答 1 行で収録します。

## 出典と利用条件

内閣府の次の統計表を取得して加工しています。

- [四半期別GDP速報 統計表](https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/files_sokuhou.html)（内閣府 経済社会総合研究所）
- [県民経済計算 統計表](https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/files_kenmin.html)（内閣府 経済社会総合研究所）
- [景気ウォッチャー調査 統計表](https://www5.cao.go.jp/keizai3/watcher/watcher_menu.html)と月次の公表資料の景気判断理由集（内閣府）

内閣府ウェブサイトのコンテンツには[公共データ利用規約（第1.0版）](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)が適用されます（[内閣府ホームページ利用規約](https://www.cao.go.jp/notice/rule.html)）。使うときは「内閣府 四半期別GDP速報（内閣府）を加工して作成」のように、出典と加工したことを明記してください。

## テーブル

| テーブル | 内容 |
| --- | --- |
| `sna.gdp_expenditure` | 1 行が 1 項目の 1 期。名目・実質・デフレーター、原系列・季節調整系列、四半期・年度・暦年 |
| `pref_accounts.observations` | 1 行が 1 表の 1 項目・1 地域・1 年度。総括表 11 表と主要系列表 5 表 |
| `economy_watchers.di` | 1 行が 1 系列の 1 か月。現状判断・先行き判断・現状の水準の DI |
| `economy_watchers.comments` | 1 行が景気判断理由集の 1 回答 |

- 項目（item）は「民間最終消費支出 > 家計最終消費支出」のように、統計表の見出しの階層を「 > 」でつないだものです。合計と内訳の行が並んでいるので、足し合わせると重複します
- 実質は連鎖方式です。実質の内訳を足しても合計に一致しません
- 四半期の季節調整系列の実額は年率で表示しています

## 使い方

実質 GDP（季節調整系列）の前期比:

```sql
SELECT period_start, value,
       round(100 * (value / lag(value) OVER (ORDER BY period_start) - 1), 1) AS qoq_pct
FROM cao.sna.gdp_expenditure
WHERE measure = 'real' AND adjustment = 'seasonally_adjusted'
  AND item = '国内総生産(支出側)'
ORDER BY period_start DESC
LIMIT 8;
```

1 人当たり県民所得の高い都道府県:

```sql
SELECT area_name, value AS income_thousand_yen
FROM cao.pref_accounts.observations
WHERE table_kind = 'summary' AND table_title = '1人当たり県民所得'
  AND area_type = 'prefecture'
  AND fiscal_year = (SELECT max(fiscal_year) FROM cao.pref_accounts.observations)
ORDER BY value DESC
LIMIT 10;
```

地域別の景気の現状判断 DI（季節調整値）:

```sql
SELECT survey_month, region, di
FROM cao.economy_watchers.di
WHERE adjustment = 'seasonally_adjusted' AND judgment = 'current' AND field = '合計'
  AND survey_month >= DATE '2026-01-01'
ORDER BY survey_month, region;
```

景気判断理由集から、飲食店のコメントを探す:

```sql
SELECT survey_month, region, assessment, industry, comment
FROM cao.economy_watchers.comments
WHERE judgment = 'current' AND industry LIKE '%飲食%'
ORDER BY survey_month DESC
LIMIT 20;
```

## 計画・通知等（plans）

[行政事業レビュー見える化サイト](https://rssystem.go.jp)のレビューシート（政策・施策、法令等、2024 年度から）が「関係する計画・通知等」に挙げる URL のうち、内閣府のサイト（www.cao.go.jp・www5.cao.go.jp・www8.cao.go.jp）の PDF を取得し、ページごとの本文にしています。

| テーブル | 内容 |
| --- | --- |
| `plans.documents` | 1 行が 1 つの計画・通知等の PDF の URL。名前・sha256・ページ数・取得日時 |
| `plans.pages` | 1 行が 1 ページ。PDF から取り出して NFKC で正規化した本文 |

- 文字コードの対応表が無いフォントの文字は、Adobe-Japan1 の CID とみなして文字に戻しています（`cid_repaired_chars`）
- ほかのサイトの文書と HTML のページは入っていません。シートの URL のうち、取得できなかったもの（リンク切れなど）と開けない PDF も入っていません
- 全文検索の索引は持っていません。`plans.pages` の `text` を検索してください
- 取得と Parquet 化は dataset-shared の `review_plans.py` で行います。PDF は 1 秒に 1 回の頻度で取得します

## ビルド

```bash
uv sync
uv run python main.py           # 取得して手元で dbt build（profiles.yml の環境変数が要る）
scripts/build.sh                # 取得・ビルドして Queria に公開する
```
