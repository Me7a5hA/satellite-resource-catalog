"""Minimal, read-only satellite resource catalog."""

import streamlit as st

from catalog import (
    CatalogError,
    display_catalog,
    filter_options,
    load_catalog,
    query_catalog,
)


def reset_filters() -> None:
    st.session_state["search"] = ""
    st.session_state["operators"] = []
    st.session_state["sensor_types"] = []


def main() -> None:
    st.set_page_config(page_title="Satellite Resource Catalog v0.2", layout="wide")
    st.title("Satellite Resource Catalog v0.2")
    st.caption("基于本地 CSV 的静态 SAR 资源目录；每条记录可能代表任务、星座或资源系列。")
    try:
        data = load_catalog()
    except CatalogError as exc:
        st.error(str(exc))
        st.stop()

    search = st.text_input("搜索四个字段", key="search", placeholder="例如 Sentinel 或 disaster")
    left, right = st.columns(2)
    operators = left.multiselect("operator", filter_options(data, "operator"), key="operators")
    sensor_types = right.multiselect("sensor_type", filter_options(data, "sensor_type"), key="sensor_types")
    st.button("重置", on_click=reset_filters)

    results = query_catalog(data, search, operators, sensor_types)
    st.write(f"匹配 {len(results)} / 共 {len(data)} 条资源记录")
    if results.empty:
        st.info("没有匹配的资源记录，请调整查询条件或点击重置。")
    st.dataframe(display_catalog(results), hide_index=True, width="stretch")
    st.caption("空字段显示为“未提供”；内容按 CSV 原样展示，未接入实时状态或外部 API。")


if __name__ == "__main__":
    main()
