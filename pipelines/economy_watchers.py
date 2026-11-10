"""景気ウォッチャー調査の DI (Excel) と景気判断理由集 (CSV) を取り出し、縦持ちにする。

- DI: 統計表 (Excel 表形式) の季節調整値 (分野別・地域別) と原数値 (全国の分野・業種別、地域別)。
  季節調整値は年に一度遡って改定されるので、毎回作り直す
- 景気判断理由集: 月次の公表資料にある (参考) 景気判断理由集 (CSV)。統計表一覧と過去の資料に載っている月のうち、
  CSV のある月のぶんを取る。
  公表後に変わらないので、取得済みの月は取り直さない

出力: data/economy_watchers/di.csv、data/economy_watchers/comments.csv

データソース: 内閣府 景気ウォッチャー調査
https://www5.cao.go.jp/keizai3/watcher/watcher_menu.html
"""

import csv
import io
import logging
import re
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.utils.datetime import from_excel
from shared.fetch import fetch, write_atomic

from pipelines.tables import clean, header_paths, number, write_rows

logger = logging.getLogger("pipelines")

SITE = "https://www5.cao.go.jp/keizai3"
USER_AGENT = "dataset-cao (+https://github.com/queria-io/dataset-cao)"
OUTPUT = Path("data/economy_watchers")
RAW = OUTPUT / "comments_raw"

DI_FIELDS = ["adjustment", "judgment", "year", "month", "region", "field", "sector", "di"]
COMMENT_FIELDS = [
    "survey_year",
    "survey_month",
    "release_date",
    "judgment",
    "region",
    "field",
    "mark",
    "assessment",
    "industry",
    "reason",
    "comment",
    "line_number",
]
# 景気判断の記号 → 5 段階の判断
MARKS = {
    "◎": "良くなっている",
    "○": "やや良くなっている",
    "□": "変わらない",
    "▲": "やや悪くなっている",
    "×": "悪くなっている",
}
NO_ANSWER = {"－", "＊", "-", "*"}
INDEXES = ["watcher_index.html", "kako_watcher.html"]
RELEASE = re.compile(r'href="((\d{4})/(\d{2})(\d{2})watcher/menu\.html)"')
REGION = re.compile(r"^\d+[.．](.+?)[(（]")
# 1 列目は「家計動向関連(北海道)」の形。月によって「関連」が抜ける
FIELD = re.compile(r"^(家計動向|企業動向|雇用)")


def judgment(text: str) -> str:
    """見出しやシート名から判断の種類を返す。"""
    if "先行き" in text:
        return "outlook"
    if "水準" in text:
        return "current_level"
    return "current"


def year_month(value, year: int | None, month) -> tuple[int, int] | None:
    """年 (2002年 や空) と月 (1 や １月) を (年, 月) にする。年が空なら前の行の年。"""
    found = re.match(r"(\d{4})年", clean(value) or "")
    m = re.fullmatch(r"(\d{1,2})月?", clean(month) or "")
    if not m:
        return None
    return (int(found.group(1)) if found else year), int(m.group(1))


def serial_month(value) -> tuple[int, int] | None:
    """Excel の日付 (日付型か通し番号) を (年, 月) にする。"""
    if isinstance(value, datetime):
        return value.year, value.month
    if isinstance(value, (int, float)) and 30000 < value < 80000:
        day = from_excel(value)
        return day.year, day.month
    return None


def blocks(rows: list[tuple], period_of) -> list[tuple[list[tuple], list[tuple[tuple[int, int], tuple]]]]:
    """シートを (見出しの行, [(年月, データの行)]) の塊に分ける。データの行が続く間を 1 つの塊にする。"""

    def walk():
        header, data, year = [], [], None
        for row in rows:
            if not any(clean(cell) for cell in row):
                continue
            found = period_of(row, year)
            if found:
                year = found[0]
                data.append((found, row))
                continue
            if data:
                yield header, data
                header, data = [], []
            header.append(row)
        if data:
            yield header, data

    return list(walk())


def melt(header: list[tuple], data, first_column: int, base: dict, place) -> list[dict]:
    width = max(len(row) for row in header + [row for _, row in data])
    paths = header_paths(header, range(first_column, width))
    title = " ".join(clean(c) or "" for row in header for c in row[:first_column])
    return [
        {**base, "judgment": base.get("judgment") or judgment(title), "year": y, "month": m, **place(path), "di": value}
        for (y, m), row in data
        for column, path in paths.items()
        if column < len(row) and (value := number(row[column])) is not None
    ]


def by_field(path: list[str]) -> dict:
    return {"region": "全国", "field": path[0], "sector": path[-1] if len(path) > 1 else None}


def by_region(field: str):
    return lambda path: {"region": path[-1], "field": field, "sector": None}


def regional(row: dict) -> bool:
    # 地域別の表の「全国」は分野別の表と同じ値なので、地域別からは取らない
    return row["region"] != "全国"


def workbook(name: str) -> openpyxl.Workbook:
    body = fetch(f"{SITE}/watcher/{name}", user_agent=USER_AGENT)
    return openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)


def di_rows() -> list[dict]:
    seasonal = workbook("watcher5.xlsx")
    sectors = workbook("watcher3.xlsx")
    regions = workbook("watcher1.xlsx")

    def seasonal_sheet(name: str) -> list[dict]:
        rows = list(seasonal[name].iter_rows(values_only=True))
        place = by_region("合計") if "地域別" in name else by_field
        base = {"adjustment": "seasonally_adjusted", "judgment": judgment(name)}
        return [
            row
            for header, data in blocks(rows, lambda r, y: year_month(r[1], y, r[2]))
            for row in melt(header, data, 3, base, place)
            if "地域別" not in name or regional(row)
        ]

    def sector_sheet(name: str) -> list[dict]:
        rows = list(sectors[name].iter_rows(values_only=True))
        base = {"adjustment": "original", "judgment": judgment(name)}
        return [
            row
            for header, data in blocks(rows, lambda r, y: year_month(r[2], y, r[3]))
            for row in melt(header, data, 4, base, by_field)
        ]

    def region_sheet(name: str) -> list[dict]:
        rows = list(regions[name].iter_rows(values_only=True))
        field = "合計" if name == "合計" else f"{name}関連"
        base = {"adjustment": "original", "judgment": None}
        return [
            row
            for header, data in blocks(rows, lambda r, _: serial_month(r[0]))
            for row in melt(header, data, 1, base, by_region(field))
            if regional(row)
        ]

    return (
        [row for name in seasonal.sheetnames for row in seasonal_sheet(name)]
        + [row for name in sectors.sheetnames for row in sector_sheet(name)]
        + [row for name in regions.sheetnames for row in region_sheet(name)]
    )


def decode(body: bytes) -> str:
    # 年によって UTF-8 と Shift_JIS が混ざる
    try:
        return body.decode("utf-8-sig")
    except UnicodeDecodeError:
        return body.decode("cp932")


def comments(text: str, base: dict) -> list[dict]:
    """景気判断理由集の CSV を、1 行 1 回答にする。地域は節の見出し、分野は 1 列目から取る。"""
    current = base["judgment"] == "current"

    def walk():
        region = field = None
        for number_, row in enumerate(csv.reader(io.StringIO(text)), start=1):
            row = [*row, *[""] * (6 - len(row))]
            head = clean(row[0]) or ""
            if m := REGION.match(head):
                region, field = m.group(1), None
                continue
            if m := FIELD.match(head):
                field = f"{m.group(1)}関連"
            mark, industry = clean(row[2]), (row[3] or "").strip()
            reason, comment = (row[4], row[5]) if current else (None, row[4])
            comment = (comment or "").strip()
            if mark not in MARKS or not region or industry in NO_ANSWER or comment in NO_ANSWER or not comment:
                continue
            yield {
                **base,
                "region": region,
                "field": field,
                "mark": mark,
                "assessment": MARKS[mark],
                "industry": industry,
                "reason": (reason or "").strip() or None,
                "comment": comment,
                "line_number": number_,
            }

    return list(walk())


def comment_rows() -> list[dict]:
    # 新しい年は統計表一覧に、古い年は過去の資料に載る
    pages = [fetch(f"{SITE}/{page}", user_agent=USER_AGENT).decode("utf-8") for page in INDEXES]
    releases = sorted({match for page in pages for match in RELEASE.findall(page)})
    RAW.mkdir(parents=True, exist_ok=True)

    def release(path: str, year: str, month: str, day: str) -> list[dict]:
        published = date(int(year), int(month), int(day))
        # 公表は調査月の翌月
        survey = date(published.year - (published.month == 1), (published.month - 2) % 12 + 1, 1)
        base = {
            "survey_year": survey.year,
            "survey_month": survey.month,
            "release_date": published.isoformat(),
        }

        def one(file: str, kind: str) -> list[dict]:
            local = RAW / f"{survey:%Y%m}_{kind}.csv"
            if not local.exists():
                url = f"{SITE}/{path.rsplit('/', 1)[0]}/{file}"
                body = fetch(url, user_agent=USER_AGENT, not_found_ok=True)
                if body is None:
                    logger.info("  判断理由集の CSV が無い: %s", url)
                    return []
                write_atomic(local, decode(body).encode("utf-8"))
            return comments(local.read_text(encoding="utf-8"), {**base, "judgment": kind})

        return one("watcher4.csv", "current") + one("watcher5.csv", "outlook")

    return [row for match in releases for row in release(*match)]


def download_economy_watchers() -> None:
    logger.info("  DI: %d 行", write_rows(OUTPUT / "di.csv", DI_FIELDS, di_rows()))
    logger.info("  判断理由集: %d 行", write_rows(OUTPUT / "comments.csv", COMMENT_FIELDS, comment_rows()))
