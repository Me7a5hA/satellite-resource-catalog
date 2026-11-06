from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import catalog

APP = Path(__file__).resolve().parents[1] / "app.py"


def start_app():
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    return app


def names(app):
    assert not app.exception
    return app.dataframe[0].value["satellite"].tolist()


def test_default_page():
    app = start_app()
    assert len(names(app)) == 4
    assert "匹配 4 / 共 4" in app.markdown[0].value
    assert app.multiselect(key="sensor_types").options == ["SAR"]


def test_case_search_combination_empty_and_reset():
    app = start_app()
    operators = list(app.multiselect(key="operators").options)
    app.text_input(key="search").set_value("DISASTER").run()
    assert names(app) == ["RADARSAT Constellation Mission", "ICEYE constellation"]
    app.multiselect(key="operators").set_value(["ICEYE", "Canadian Space Agency"])
    app.multiselect(key="sensor_types").set_value(["SAR"]).run()
    assert names(app) == ["RADARSAT Constellation Mission", "ICEYE constellation"]
    assert app.multiselect(key="operators").options == operators
    app.multiselect(key="operators").set_value(["Capella Space"]).run()
    assert names(app) == []
    assert "没有匹配" in app.info[0].value
    app.button[0].click().run()
    assert len(names(app)) == 4
    assert app.text_input(key="search").value == ""
    assert app.multiselect(key="operators").value == []
    assert app.multiselect(key="sensor_types").value == []


def test_special_character_search():
    app = start_app()
    app.text_input(key="search").set_value("[").run()
    assert names(app) == []


def test_dynamic_options_and_missing_value_display(monkeypatch):
    data = catalog.parse_catalog(
        "satellite,operator,sensor_type,primary_application\n"
        "A,New operator,Optical,\nB,,SAR,Other\nC,New operator,Thermal,x\n"
    )
    monkeypatch.setattr(catalog, "load_catalog", lambda: data.copy())
    app = start_app()
    assert app.multiselect(key="operators").options == ["New operator"]
    assert app.multiselect(key="sensor_types").options == ["Optical", "SAR", "Thermal"]
    assert app.dataframe[0].value.iloc[0]["primary_application"] == "未提供"
    assert app.dataframe[0].value.iloc[1]["operator"] == "未提供"
    app.multiselect(key="sensor_types").set_value(["Thermal", "Optical"]).run()
    assert names(app) == ["A", "C"]
    app.text_input(key="search").set_value("未提供").run()
    assert names(app) == []


@pytest.mark.parametrize(("filename", "content", "message"), [
    ("missing.csv", None, "找不到"),
    ("empty.csv", "", "为空"),
    ("columns.csv", "satellite,operator\nA,B\n", "缺少必需列"),
    ("parse.csv", "satellite,operator,sensor_type,primary_application\n\"bad", "解析失败"),
])
def test_file_errors_are_shown_without_traceback(monkeypatch, tmp_path, filename, content, message):
    path = tmp_path / filename
    if content is not None:
        path.write_text(content)
    real_load = catalog.load_catalog
    monkeypatch.setattr(catalog, "load_catalog", lambda: real_load(path))
    app = start_app()
    assert message in app.error[0].value
    assert not app.dataframe
