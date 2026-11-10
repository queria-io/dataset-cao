"""統計表 (CSV・Excel) を縦持ちの行にする共通部品。

内閣府の統計表は、見出しが複数の行に分かれた横持ちの表になっている。
見出しの行では、親の項目が左上のセルにだけ書かれ、子の項目がその下の行に並ぶ。
列ごとに、いちばん深い見出しと、その左にある上の行の見出しをたどって項目の経路にする。
"""

import csv
import re
import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path

SPACES = re.compile(r"\s+")


def clean(value) -> str | None:
    """セルの文字を NFKC にし、改行と空白を取る。空なら None。"""
    if value is None:
        return None
    text = SPACES.sub("", unicodedata.normalize("NFKC", str(value)))
    return text or None


def number(value) -> float | None:
    """セルの値を数にする。秘匿 (x)・該当なし (-, ***) などの記号は None。"""
    if isinstance(value, (int, float)):
        return float(value)
    text = (clean(value) or "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def header_paths(rows: Sequence[Sequence], columns: Iterable[int]) -> dict[int, list[str]]:
    """見出しの行から、列ごとの項目の経路 (上の行から順) を返す。見出しの無い列は含めない。"""
    targets = set(columns)
    grid = [[clean(cell) for cell in row] for row in rows]

    # 対象外の列 (地域名の列など) の見出しは親として拾わない
    def at(level: int, column: int) -> str | None:
        row = grid[level]
        return row[column] if column in targets and column < len(row) else None

    def path(column: int) -> list[str]:
        levels = [level for level in range(len(grid)) if at(level, column)]
        if not levels:
            return []
        deepest = levels[-1]

        # 上の行から順に、左にある見出しを親として拾う。親が見つかった列より左には戻らない
        def ancestors(level: int, left: int) -> list[str]:
            if level == deepest:
                return [at(deepest, column)]
            found = next((c for c in range(column, left - 1, -1) if at(level, c)), None)
            if found is None:
                return ancestors(level + 1, left)
            return [at(level, found), *ancestors(level + 1, found)]

        return ancestors(0, 0)

    return {column: p for column in sorted(targets) if (p := path(column))}


def write_rows(path: Path, fields: Sequence[str], rows: Iterable[dict]) -> int:
    """行を CSV に書き、書いた行数を返す。0 行なら前回の出力を残して止める。"""
    partial = path.with_name(path.name + ".part")
    partial.parent.mkdir(parents=True, exist_ok=True)
    with partial.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        count = sum(1 for row in rows if writer.writerow(row) is not None)
    if count == 0:
        partial.unlink()
        raise SystemExit(f"{path}: 行が 1 つも取れなかった")
    partial.replace(path)
    return count
