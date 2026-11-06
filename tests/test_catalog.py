import hashlib

import pandas as pd
import pytest

from catalog import (
    DEFAULT_DATA_PATH,
    REQUIRED_COLUMNS,
    CatalogError,
    CatalogFileNotFoundError,
    CatalogParseError,
    EmptyCatalogError,
    MissingColumnsError,
    display_catalog,
    filter_options,
    load_catalog,
    parse_catalog,
    query_catalog,
)

HEADER = ",".join(REQUIRED_COLUMNS) + "\n"
NAMES = [
    "Sentinel-1", "RADARSAT Constellation Mission",
    "ICEYE constellation", "Capella constellation",
]


@pytest.fixture
def data():
    return load_catalog()


def test_original_data_and_whitespace_tail(data):
    assert list(data.columns) == list(REQUIRED_COLUMNS)
    assert data["satellite"].tolist() == NAMES
    assert data["operator"].tolist() == [
        "ESA/Copernicus", "Canadian Space Agency", "ICEYE", "Capella Space",
    ]
    assert data["sensor_type"].tolist() == ["SAR"] * 4
    assert data["primary_application"].tolist() == [
        "Flood monitoring", "Maritime and disaster monitoring",
        "Disaster monitoring", "High-resolution monitoring",
    ]
    assert len(parse_catalog(DEFAULT_DATA_PATH.read_text() + "\n  \n\t\n")) == 4


@pytest.mark.parametrize(("search", "expected"), [
    ("sentinel", [NAMES[0]]),
    ("DISASTER", NAMES[1:3]),
    ("copERNICUS", [NAMES[0]]),
    ("sar", NAMES),
    ("", NAMES),
    ("no such satellite", []),
    ("[", []), (".*", []), ("\\", []), ("^", []),
])
def test_search_all_fields_case_and_literal(data, search, expected):
    assert query_catalog(data, search)["satellite"].tolist() == expected


def test_special_characters_match_literally():
    data = parse_catalog(HEADER + 'A[1],Operator.*,SAR,Path\\name\nB,Other,SAR,Other\n')
    for search in ["[", ".*", "\\"]:
        assert query_catalog(data, search)["satellite"].tolist() == ["A[1]"]


def test_combined_filters_or_and_order(data):
    result = query_catalog(data, "disaster", ["ICEYE", "Canadian Space Agency"], ["SAR"])
    assert result["satellite"].tolist() == NAMES[1:3]
    assert result.index.tolist() == [1, 2]
    assert query_catalog(data, "disaster", ["Capella Space"], ["SAR"]).empty
    assert query_catalog(data, sensor_types=["Optical"]).empty


def test_sensor_multiselect_or_and_cross_field():
    data = parse_catalog(HEADER + "A,One,SAR,x\nB,One,Optical,x\nC,Two,Thermal,x\n")
    assert query_catalog(data, sensor_types=["Optical", "SAR"])["satellite"].tolist() == ["A", "B"]
    assert query_catalog(data, operators=["One"], sensor_types=["Thermal"]).empty


def test_dynamic_options_from_complete_data(data):
    assert filter_options(data, "operator") == data["operator"].tolist()
    assert filter_options(data, "sensor_type") == ["SAR"]
    custom = parse_catalog(HEADER + "A,New operator,L-band,x\nB,New operator,,x\nC, ,C-band,x\n")
    assert filter_options(custom, "operator") == ["New operator"]
    assert filter_options(custom, "sensor_type") == ["L-band", "C-band"]


def test_missing_values_display_and_search():
    data = parse_catalog(HEADER + "A,,SAR,   \nB,NA,,null\nC,Other\n")
    assert data.iloc[0].tolist() == ["A", "", "SAR", ""]
    assert data.iloc[1].tolist() == ["B", "NA", "", "null"]
    assert data.iloc[2].tolist() == ["C", "Other", "", ""]
    assert query_catalog(data, "未提供").empty
    shown = display_catalog(data)
    assert shown.iloc[0].tolist() == ["A", "未提供", "SAR", "未提供"]
    assert shown.iloc[1].tolist() == ["B", "NA", "未提供", "null"]
    assert data.iloc[0]["operator"] == ""


def test_functions_do_not_mutate_input(data):
    original = data.copy(deep=True)
    result = query_catalog(data, "sar")
    result.iloc[0, 0] = "Changed"
    display_catalog(data)
    filter_options(data, "operator")
    pd.testing.assert_frame_equal(data, original)


def test_nulls_from_dataframe_are_empty_for_search_and_display():
    data = pd.DataFrame([["A", None, "SAR", pd.NA]], columns=REQUIRED_COLUMNS)
    assert query_catalog(data, "none").empty
    assert query_catalog(data, "未提供").empty
    assert display_catalog(data).iloc[0].tolist() == ["A", "未提供", "SAR", "未提供"]


@pytest.mark.parametrize("text", ["", " \n\t\n", HEADER])
def test_empty_files(tmp_path, text):
    path = tmp_path / "empty.csv"
    path.write_text(text)
    with pytest.raises(EmptyCatalogError, match="为空|没有资源记录"):
        load_catalog(path)


@pytest.mark.parametrize("missing", REQUIRED_COLUMNS)
def test_each_missing_required_column(tmp_path, missing):
    path = tmp_path / "missing-column.csv"
    path.write_text(",".join(c for c in REQUIRED_COLUMNS if c != missing) + "\n")
    with pytest.raises(MissingColumnsError, match=missing):
        load_catalog(path)


@pytest.mark.parametrize("text", [
    HEADER + '"Unclosed,Operator,SAR,Application\n',
    HEADER + "A,Operator,SAR,Application,extra\n",
    HEADER.rstrip("\n") + ",operator\nA,B,SAR,C,D\n",
])
def test_csv_parse_errors(tmp_path, text):
    path = tmp_path / "bad.csv"
    path.write_text(text)
    with pytest.raises(CatalogParseError, match="CSV 解析失败"):
        load_catalog(path)


def test_missing_file(tmp_path):
    with pytest.raises(CatalogFileNotFoundError, match="找不到"):
        load_catalog(tmp_path / "not-there.csv")


def test_invalid_encoding(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_bytes(b"\xff\xfe\xff")
    with pytest.raises(CatalogParseError, match="UTF-8"):
        load_catalog(path)


def test_unreadable_path(tmp_path):
    with pytest.raises(CatalogError, match="无法读取"):
        load_catalog(tmp_path)


def test_utf8_bom(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_text(HEADER + "A,B,SAR,C\n", encoding="utf-8-sig")
    assert load_catalog(path)["satellite"].tolist() == ["A"]


def test_original_csv_bytes_unchanged():
    before = DEFAULT_DATA_PATH.read_bytes()
    data = load_catalog()
    display_catalog(query_catalog(data, "DISASTER"))
    assert DEFAULT_DATA_PATH.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == "f337c0aa8d8d67d9342cc5a3135f5aae2ba5cea31c836d94e00a29d5df5984f5"
