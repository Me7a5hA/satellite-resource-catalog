"""CSV catalog operations, independent of Streamlit and without writes."""

import csv
from io import StringIO
from pathlib import Path
from collections.abc import Sequence

import pandas as pd

REQUIRED_COLUMNS = ("satellite", "operator", "sensor_type", "primary_application")
DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "sar_satellites.csv"


class CatalogError(ValueError):
    """A catalog problem safe to show to the user."""


class CatalogFileNotFoundError(CatalogError):
    pass


class EmptyCatalogError(CatalogError):
    pass


class MissingColumnsError(CatalogError):
    pass


class CatalogParseError(CatalogError):
    pass


def validate_columns(columns: Sequence[str]) -> None:
    """Require the four catalog fields; do not infer missing attributes."""
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise MissingColumnsError(f"CSV 缺少必需列：{', '.join(missing)}")


def parse_catalog(text: str) -> pd.DataFrame:
    """Parse UTF-8 CSV text. Blank lines are ignored, short rows retain blanks."""
    try:
        rows = [
            row for row in csv.reader(StringIO(text), strict=True)
            if any(value.strip() for value in row)
        ]
    except csv.Error as exc:
        raise CatalogParseError(f"CSV 解析失败：{exc}") from exc
    if not rows:
        raise EmptyCatalogError("CSV 文件为空或仅包含空白行。")
    header, *records = rows
    validate_columns(header)
    if len(header) != len(set(header)):
        raise CatalogParseError("CSV 解析失败：存在重复列名。")
    if not records:
        raise EmptyCatalogError("CSV 只有表头，没有资源记录。")
    if any(len(row) > len(header) for row in records):
        raise CatalogParseError("CSV 解析失败：数据行的字段数超过表头列数。")
    # Preserve nonempty source strings, including literal 'NA' and 'null'.
    padded = [row + [""] * (len(header) - len(row)) for row in records]
    data = pd.DataFrame(padded, columns=header).loc[:, list(REQUIRED_COLUMNS)]
    return data.replace(r"^\s*$", "", regex=True)


def load_catalog(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """The only I/O boundary: read the source without modifying it."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise CatalogFileNotFoundError("找不到 CSV 数据文件，请检查 data/sar_satellites.csv。") from exc
    except UnicodeError as exc:
        raise CatalogParseError("CSV 解析失败：文件必须使用 UTF-8 编码。") from exc
    except OSError as exc:
        raise CatalogError("无法读取 CSV 数据文件，请检查路径和读取权限。") from exc
    return parse_catalog(text)


def filter_options(data: pd.DataFrame, column: str) -> list[str]:
    """Derive nonempty options from the complete catalog in source order."""
    values = data[column].fillna("")
    return values[values.str.strip().ne("")].drop_duplicates().tolist()


def query_catalog(
    data: pd.DataFrame,
    search: str = "",
    operators: Sequence[str] = (),
    sensor_types: Sequence[str] = (),
) -> pd.DataFrame:
    """OR within fields, AND across conditions; preserve rows and input data."""
    values = data.loc[:, list(REQUIRED_COLUMNS)].fillna("")
    mask = pd.Series(True, index=data.index)
    if search:
        matches = values.apply(
            lambda column: column.str.casefold().str.contains(
                search.casefold(), regex=False, na=False
            )
        )
        mask &= matches.any(axis=1)
    if operators:
        mask &= values["operator"].isin(operators)
    if sensor_types:
        mask &= values["sensor_type"].isin(sensor_types)
    return data.loc[mask].copy()


def display_catalog(data: pd.DataFrame) -> pd.DataFrame:
    """Use a presentation-only placeholder, never as searchable data."""
    return data.fillna("").replace(r"^\s*$", "未提供", regex=True)
