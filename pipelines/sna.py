"""四半期別 GDP 速報の統計表 (CSV) を取り出し、縦持ちにする。

最新の速報の「Ⅰ. 国内総生産（支出側）及び各需要項目」の実額 (名目・実質) とデフレーターを取る。
季節調整系列は速報のたびに 1994 年まで遡って改定されるので、毎回最新の速報だけで作り直す。

出力: data/sna/gdp_expenditure.csv

データソース: 内閣府 経済社会総合研究所 四半期別GDP速報
https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/files_sokuhou.html
"""

import csv
import io
import logging
import re
from datetime import date
from pathlib import Path

from shared.fetch import fetch

from pipelines.tables import clean, header_paths, number, write_rows

logger = logging.getLogger("pipelines")

SITE = "https://www.esri.cao.go.jp"
INDEX = f"{SITE}/jp/sna/data/data_list/sokuhou/files/files_sokuhou.html"
USER_AGENT = "dataset-cao (+https://github.com/queria-io/dataset-cao)"
OUTPUT = Path("data/sna/gdp_expenditure.csv")

YEAR_PAGE = re.compile(r'href="(/jp/sna/data/data_list/sokuhou/files/(\d{4})/toukei_\2\.html)"')
RELEASE = re.compile(r'href="(/jp/sna/data/data_list/sokuhou/files/\d{4}/(qe\d{3}(?:_2)?)/gdemenuja\.html)"')
TITLE = re.compile(r"統計表一覧（(\d{4}年\d+-\d+月期\s*\d次速報値)）")
PUBLISHED = re.compile(r"&lt;(\d{4})年(\d+)月(\d+)日公表&gt;")
UNIT = re.compile(r"\((?:単位:)?([^)]+)\)")
PERIOD = re.compile(r"^(?:(\d{4})/)?(\d+)-(\d+)\.$")

# ファイル名の頭 → (系列, 季節調整, 周期)。末尾の 4 桁 (速報の番号) は速報ごとに変わる
FILES = {
    "gaku-mg": ("nominal", "original", "quarter"),
    "gaku-mk": ("nominal", "seasonally_adjusted", "quarter"),
    "gaku-mfy": ("nominal", "original", "fiscal_year"),
    "gaku-mcy": ("nominal", "original", "calendar_year"),
    "gaku-jg": ("real", "original", "quarter"),
    "gaku-jk": ("real", "seasonally_adjusted", "quarter"),
    "gaku-jfy": ("real", "original", "fiscal_year"),
    "gaku-jcy": ("real", "original", "calendar_year"),
    "def-qg": ("deflator", "original", "quarter"),
    "def-qk": ("deflator", "seasonally_adjusted", "quarter"),
    "def-fy": ("deflator", "original", "fiscal_year"),
    "def-cy": ("deflator", "original", "calendar_year"),
}
FIELDS = [
    "release",
    "release_date",
    "measure",
    "adjustment",
    "frequency",
    "year",
    "quarter",
    "item",
    "item_level",
    "value",
    "unit",
]


def latest_release() -> tuple[str, str]:
    """最新の速報の統計表一覧ページの URL と番号 (例: qe262_2) を返す。"""
    index = fetch(INDEX, user_agent=USER_AGENT).decode("utf-8")
    years = sorted(set(YEAR_PAGE.findall(index)), key=lambda match: match[1])[-2:]
    releases = [
        release
        for path, _ in years
        for release in RELEASE.findall(fetch(SITE + path, user_agent=USER_AGENT).decode("utf-8"))
    ]
    if not releases:
        raise SystemExit("四半期別GDP速報の統計表一覧が見つからない")
    path, code = max(releases, key=lambda release: release[1])
    return SITE + path, code


def period(label: str, year: int | None) -> tuple[int, int | None] | None:
    """期の見出し (1994/ 1- 3. や 4- 6.、1994/4-3.) を (年, 四半期) にする。年が無ければ前の行の年。"""
    match = PERIOD.match(clean(label) or "")
    if not match:
        return None
    start = int(match.group(2))
    end = int(match.group(3))
    found = int(match.group(1)) if match.group(1) else year
    quarter = (start + 2) // 3 if end - start == 2 else None
    return found, quarter


def parse(text: str, measure: str, adjustment: str, frequency: str, release: dict) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    unit = next(
        (m.group(1) for cell in rows[0] if (m := UNIT.search(clean(cell) or ""))),
        None,
    )
    first = next(i for i, row in enumerate(rows) if row and period(row[0], 0))
    # 見出しは 3 行目から。日本語の行だけを使う (英語の行は ASCII だけ)
    japanese = [row for row in rows[2:first] if any(re.search(r"[^\x00-\x7f]", c) for c in row[1:])]
    width = max(len(row) for row in rows)
    paths = header_paths(japanese, range(1, width))

    def records():
        year = None
        for row in rows[first:]:
            found = period(row[0], year) if row else None
            if not found:
                continue
            year, quarter = found
            for column, path in paths.items():
                value = number(row[column]) if column < len(row) else None
                if value is not None:
                    yield {
                        **release,
                        "measure": measure,
                        "adjustment": adjustment,
                        "frequency": frequency,
                        "year": year,
                        "quarter": quarter,
                        "item": " > ".join(path),
                        "item_level": len(path),
                        "value": value,
                        "unit": unit,
                    }

    return list(records())


def download_sna() -> None:
    menu_url, code = latest_release()
    menu = fetch(menu_url, user_agent=USER_AGENT).decode("utf-8")
    title = TITLE.search(menu)
    published = PUBLISHED.search(menu)
    if not title or not published:
        raise SystemExit(f"速報の名前と公表日が読み取れない: {menu_url}")
    release = {
        "release": re.sub(r"\s+", "", title.group(1)),
        "release_date": date(*map(int, published.groups())).isoformat(),
    }
    logger.info("  %s (%s)", release["release"], code)

    links = re.findall(r'href="(tables/([a-z-]+?)(\d{4})\.csv)"', menu)
    files = {prefix: path for path, prefix, _ in links if prefix in FILES}
    missing = set(FILES) - set(files)
    if missing:
        raise SystemExit(f"統計表が見つからない: {sorted(missing)}")
    base = menu_url.rsplit("/", 1)[0]

    def table(prefix: str) -> list[dict]:
        text = fetch(f"{base}/{files[prefix]}", user_agent=USER_AGENT).decode("cp932")
        return parse(text, *FILES[prefix], release)

    rows = [row for prefix in FILES for row in table(prefix)]
    logger.info("  %d 行", write_rows(OUTPUT, FIELDS, rows))
