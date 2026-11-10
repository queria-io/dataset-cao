"""県民経済計算の統計表 (Excel) を取り出し、縦持ちにする。

最新の公表の「総括表」と「主要系列表」を取る。県民経済計算は公表のたびに過去の年度まで
遡って改定されるので、毎回最新の公表だけで作り直す。

出力: data/pref_accounts/observations.csv

データソース: 内閣府 経済社会総合研究所 県民経済計算
https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/files_kenmin.html
"""

import io
import logging
import re
from pathlib import Path

import openpyxl
from shared.fetch import fetch

from pipelines.tables import clean, header_paths, number, write_rows

logger = logging.getLogger("pipelines")

SITE = "https://www.esri.cao.go.jp"
BASE = f"{SITE}/jp/sna/data/data_list/kenmin/files"
INDEX = f"{BASE}/files_kenmin.html"
USER_AGENT = "dataset-cao (+https://github.com/queria-io/dataset-cao)"
OUTPUT = Path("data/pref_accounts/observations.csv")

RELEASE = re.compile(r'href="contents/main_(\d{4})\.html"')
TABLE = re.compile(r'href="(tables/\d{4}/(soukatu|syuyo)(\d+)\.xlsx)"')
TITLE_NUMBER = re.compile(r"^\d+[.．]")
UNIT = re.compile(r"単位[:：](.+?)[)）]")
SHEET_YEAR = re.compile(r"^(\d{4})")

# 政令指定都市の全国地方公共団体コード
DESIGNATED_CITIES = {
    "札幌市": "011002",
    "仙台市": "041009",
    "さいたま市": "111007",
    "千葉市": "121002",
    "横浜市": "141003",
    "川崎市": "141305",
    "相模原市": "141500",
    "新潟市": "151009",
    "静岡市": "221007",
    "浜松市": "221309",
    "名古屋市": "231002",
    "京都市": "261009",
    "大阪市": "271004",
    "堺市": "271403",
    "神戸市": "281000",
    "岡山市": "331007",
    "広島市": "341002",
    "北九州市": "401005",
    "福岡市": "401307",
    "熊本市": "431001",
}
SECTIONS = {"地域ブロック": "block", "政令指定都市": "designated_city"}
FIELDS = [
    "release",
    "table_kind",
    "table_number",
    "table_title",
    "item",
    "item_level",
    "area_type",
    "area_name",
    "prefecture_code",
    "city_code",
    "fiscal_year",
    "value",
    "unit",
]


def areas(rows: list[tuple]) -> dict[int, dict]:
    """行番号 → 地域。都道府県・全県計・地域ブロック・政令指定都市の行を拾う。"""

    def walk():
        section = None
        for index, row in enumerate(rows):
            code, name = clean(row[0]), clean(row[1]) if len(row) > 1 else None
            if code in SECTIONS:
                section = SECTIONS[code]
            elif code and re.fullmatch(r"\d{2}", code) and name:
                yield index, {"area_type": "prefecture", "area_name": name, "prefecture_code": code}
            elif name == "全県計":
                yield index, {"area_type": "national", "area_name": name}
            elif name and section == "block":
                yield index, {"area_type": "block", "area_name": name}
            elif name and section == "designated_city":
                yield index, {
                    "area_type": "designated_city",
                    "area_name": name,
                    "city_code": DESIGNATED_CITIES[name],
                }

    return dict(walk())


def title_and_unit(rows: list[tuple]) -> tuple[str, str | None]:
    cells = [clean(cell) for row in rows[:4] for cell in row if clean(cell)]
    title = next(c for c in cells if TITLE_NUMBER.match(c))
    unit = next((m.group(1) for c in cells if (m := UNIT.search(c))), None)
    return TITLE_NUMBER.sub("", title), unit


def summary(book: openpyxl.Workbook, number_: int) -> list[dict]:
    """総括表: 1 つの指標を、都道府県などの行 × 年度の列で持つ。"""
    rows = list(book["実数"].iter_rows(values_only=True))
    title, unit = title_and_unit(rows)
    header = next(row for row in rows if sum(isinstance(c, int) and 1900 < c < 2100 for c in row) > 3)
    years = {column: c for column, c in enumerate(header) if isinstance(c, int) and 1900 < c < 2100}
    return [
        {
            "table_kind": "summary",
            "table_number": number_,
            "table_title": title,
            "item": None,
            "item_level": 0,
            **area,
            "fiscal_year": year,
            "value": value,
            "unit": unit,
        }
        for index, area in areas(rows).items()
        for column, year in years.items()
        if (value := number(rows[index][column])) is not None
    ]


def main_series(book: openpyxl.Workbook, number_: int) -> list[dict]:
    """主要系列表: シートが年度、行が都道府県など、列が項目。"""

    def sheet(name: str) -> list[dict]:
        rows = list(book[name].iter_rows(values_only=True))
        title, unit = title_and_unit(rows)
        found = areas(rows)
        first = min(found)
        # 見出しは【年度】の行の次から、最初の都道府県の行の前まで
        start = next(i for i, row in enumerate(rows) if any("【" in (clean(c) or "") for c in row)) + 1
        width = max(len(row) for row in rows)
        # 印刷のページごとに、都道府県コードと名前の列が横に繰り返し並ぶ。その列は項目にしない
        labels = {clean(rows[first][0]), clean(rows[first][1])}
        values = [c for c in range(3, width) if c >= len(rows[first]) or clean(rows[first][c]) not in labels]
        paths = header_paths(rows[start:first], values)
        year = int(SHEET_YEAR.match(name).group(1))
        return [
            {
                "table_kind": "main_series",
                "table_number": number_,
                "table_title": title,
                "item": " > ".join(path),
                "item_level": len(path),
                **area,
                "fiscal_year": year,
                "value": value,
                "unit": unit,
            }
            for index, area in found.items()
            for column, path in paths.items()
            if column < len(rows[index]) and (value := number(rows[index][column])) is not None
        ]

    return [row for name in book.sheetnames if SHEET_YEAR.match(name) for row in sheet(name)]


def download_pref_accounts() -> None:
    index = fetch(INDEX, user_agent=USER_AGENT).decode("utf-8")
    years = sorted(int(y) for y in RELEASE.findall(index))
    if not years:
        raise SystemExit("県民経済計算の公表ページが見つからない")
    latest = years[-1]
    page = fetch(f"{BASE}/contents/main_{latest}.html", user_agent=USER_AGENT).decode("utf-8")
    tables = TABLE.findall(page)
    if not tables:
        raise SystemExit(f"県民経済計算 {latest} 年度の統計表が見つからない")
    release = {"release": f"{latest}年度"}
    logger.info("  %s 年度 (%d 表)", latest, len(tables))

    def table(path: str, kind: str, number_: str) -> list[dict]:
        body = fetch(f"{BASE}/contents/{path}", user_agent=USER_AGENT)
        book = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
        parse = summary if kind == "soukatu" else main_series
        return [{**release, **row} for row in parse(book, int(number_))]

    rows = [row for path, kind, number_ in tables for row in table(path, kind, number_)]
    logger.info("  %d 行", write_rows(OUTPUT, FIELDS, rows))
