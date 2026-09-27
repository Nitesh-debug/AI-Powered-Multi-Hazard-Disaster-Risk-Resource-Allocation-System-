"""Map rendering helpers used by the Streamlit UI and Analytics Agent."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st
from folium.plugins import HeatMap
import folium
from streamlit_folium import st_folium

from scripts import district_info


RISK_COLORS = {
    0: [0, 255, 0, 160],
    1: [255, 255, 0, 160],
    2: [255, 165, 0, 160],
    3: [255, 0, 0, 160],
    4: [128, 0, 128, 160],
}


def _map_rows(data_list: list[dict[str, Any]]) -> pd.DataFrame:
    map_data: list[dict[str, Any]] = []
    for item in data_list:
        dname = item.get("district") or item.get("District")
        info = district_info.district_data.get(dname, {})
        coords = info.get("coordinates")
        if not coords:
            continue
        risk = int(item.get("risk_level", 0) or 0)
        map_data.append(
            {
                "district": dname,
                "lat": coords[0],
                "lon": coords[1],
                "risk": risk,
                "height": (risk + 1) * 20000,
                "color": RISK_COLORS.get(risk, RISK_COLORS[0]),
                "weight": max(risk, 0) + 0.1,
            }
        )
    return pd.DataFrame(map_data)


def render_risk_map(data_list: list[dict[str, Any]]) -> None:
    """3D column map of district risk levels."""
    df_map = _map_rows(data_list)
    if df_map.empty:
        st.warning("No data for map.")
        return

    layer = pdk.Layer(
        "ColumnLayer",
        data=df_map,
        get_position="[lon, lat]",
        get_elevation="height",
        elevation_scale=1,
        radius=5000,
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=33.77, longitude=76.57, zoom=7, pitch=45)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{district}\nRisk: {risk}"},
    )
    st.pydeck_chart(deck)


def render_folium_heatmap(data_list: list[dict[str, Any]]) -> None:
    """2D Folium heatmap for high-risk concentrations."""
    df_map = _map_rows(data_list)
    if df_map.empty:
        st.warning("No data for heatmap.")
        return
    fmap = folium.Map(location=[33.77, 76.57], zoom_start=7)
    heat_points = df_map[["lat", "lon", "weight"]].values.tolist()
    HeatMap(heat_points, radius=25, blur=18).add_to(fmap)
    for _, row in df_map.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color="#222",
            fill=True,
            fill_color="#ff4b4b" if row["risk"] >= 3 else "#4b8bff",
            popup=f"{row['district']} (risk {row['risk']})",
        ).add_to(fmap)
    st_folium(fmap, width=None, height=420)
