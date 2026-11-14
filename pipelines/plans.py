"""行政事業レビューのシートが「関係する計画・通知等」に挙げる、内閣府のサイトの PDF をページごとの本文にする。

取得と Parquet 化は shared/review_plans.py。

出典: 行政事業レビュー見える化サイト https://rssystem.go.jp 、内閣府ウェブサイトの各資料
"""

from pathlib import Path

from shared import review_plans

USER_AGENT = "queria-dataset-cao (+https://queria.io/)"
HOSTS = {"www.cao.go.jp", "www5.cao.go.jp", "www8.cao.go.jp"}
PDF_DIR = Path("data/plans")
PARQUET_DIR = Path("data/parquet")


def download_plans() -> None:
    review_plans.download_plans(HOSTS, user_agent=USER_AGENT, pdf_dir=PDF_DIR)


def build_plans_parquet() -> None:
    review_plans.build_plans_parquet(
        user_agent=USER_AGENT, pdf_dir=PDF_DIR, parquet_dir=PARQUET_DIR
    )
