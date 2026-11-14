"""内閣府のデータパイプライン。

1. sna: 四半期別 GDP 速報 (CSV) を取り出す
2. pref_accounts: 県民経済計算 (Excel) を取り出す
3. economy_watchers: 景気ウォッチャー調査の DI (Excel) と景気判断理由集 (CSV) を取り出す
4. dbt: dbt ビルド
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines import plans
from pipelines.economy_watchers import download_economy_watchers
from pipelines.pref_accounts import download_pref_accounts
from pipelines.sna import download_sna

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")


def download():
    logger.info("1/5: sna (四半期別GDP速報)")
    download_sna()
    logger.info("2/5: pref_accounts (県民経済計算)")
    download_pref_accounts()
    logger.info("3/5: economy_watchers (景気ウォッチャー調査)")
    download_economy_watchers()


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        if not dbt.invoke(command).success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def main():
    download()
    logger.info("4/5: plans (行政事業レビューが挙げる計画・通知等)")
    plans.download_plans()
    plans.build_plans_parquet()
    logger.info("5/5: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
