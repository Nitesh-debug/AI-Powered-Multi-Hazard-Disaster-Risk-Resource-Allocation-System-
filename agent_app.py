"""Streamlit entry point: chat assistant + live HQ dashboard."""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from agents.master_agent import MasterAgent
from ui.maps import render_folium_heatmap, render_risk_map

st.set_page_config(page_title="Agentic Disaster Manager", page_icon="🤖", layout="wide")


def init_session() -> None:
    if "agent" not in st.session_state:
        st.session_state.agent = MasterAgent()
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_allocation_table(data: list[dict[str, Any]]) -> None:
    table_rows = []
    for plan in data:
        shortages = ", ".join(
            f"{key}:{value['shortage']} needed"
            for key, value in plan["supply_allocation"].items()
            if value["shortage"] > 0
        ) or "All needs met"
        table_rows.append(
            {
                "District": plan["district"],
                "Risk": plan["risk_level"],
                "Teams": len(plan["allocated_teams"]),
                "Shortages": shortages,
            }
        )
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)


def render_hospital_cards(data: list[dict[str, Any]]) -> None:
    for item in data:
        st.error(f"🚨 **{item['district']}** (High Risk)")
        st.markdown(f"🏥 **Nearest:** {item['hospital']}")
        st.markdown(f"📍 [Get Directions on Google Maps]({item['link']})")
        st.divider()


def render_payload(dtype: str | None, data: Any) -> None:
    if not data:
        return
    if dtype == "allocation_plan":
        render_allocation_table(data)
    elif dtype == "map_data":
        render_risk_map(data)
        render_folium_heatmap(data)
    elif dtype == "stats":
        st.bar_chart(data)
    elif dtype == "hospital_directions":
        render_hospital_cards(data)


def render_chat() -> None:
    st.title("🤖 AI Assistant")
    st.markdown("Ask me to *'Run allocation'* or *'Show risk map'*")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            render_payload(msg.get("type"), msg.get("data"))

    if prompt := st.chat_input("How can I help you?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Agent working..."):
                response = st.session_state.agent.process_request(prompt)
            st.markdown(response["response_text"])
            if response.get("metrics"):
                st.caption(f"Latency: {response['metrics']}")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response["response_text"],
                    "data": response.get("data"),
                    "type": response.get("type"),
                }
            )
            render_payload(response.get("type"), response.get("data"))


def render_dashboard() -> None:
    st.title("🚨 Live Disaster Dashboard")
    if st.button("Refresh Data"):
        st.rerun()

    summary = st.session_state.agent.analytics_agent.get_dashboard_summary()
    if not summary:
        st.warning("No data available. Please run resource allocation in Chat Mode first.")
        return

    st.caption(
        f"Weather: OpenWeatherMap / Open-Meteo / dummy fallback | Last update: **{summary.get('last_updated', 'Unknown')}**"
    )
    stats = summary["stats"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Districts", stats["total_districts"])
    col2.metric("High Risk (Alerts)", stats["high_risk"], delta_color="inverse")
    col3.metric("Medium Risk", stats["medium_risk"])
    col4.metric(
        "Safe",
        int(stats["total_districts"]) - int(stats["high_risk"]) - int(stats["medium_risk"]) - int(stats["low_risk"]),
    )
    st.divider()

    c_map, c_alerts = st.columns([2, 1])
    with c_map:
        st.subheader("🗺️ 3D Risk Terrain")
        render_risk_map(summary["map_data"])
        st.subheader("🔥 Risk Heatmap")
        render_folium_heatmap(summary["map_data"])
    with c_alerts:
        st.subheader("⚠️ Active Alerts")
        if not summary["alerts"] and not summary["warnings"]:
            st.success("No active high/medium risk alerts.")
        for item in summary["alerts"]:
            st.error(f"🚨 **{item['district']}** (High Risk)")
            st.caption(f"Prob: {item.get('risk_probability', 0)}")
        for item in summary["warnings"]:
            st.warning(f"⚠️ **{item['district']}** (Medium Risk)")

    st.divider()
    st.subheader("📦 Resource Allocation Needs")
    if summary["allocations"]:
        table_data = []
        for plan in summary["allocations"]:
            supplies = plan["supply_allocation"]
            supp_str = ", ".join(f"{k}: {v['allocated']}/{v['needed']}" for k, v in supplies.items())
            table_data.append(
                {
                    "District": plan["district"],
                    "Risk": plan["risk_level"],
                    "Priority": plan["priority_score"],
                    "Teams Allocated": len(plan["allocated_teams"]),
                    "Supplies Status": supp_str,
                }
            )
        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            column_config={
                "Risk": st.column_config.ProgressColumn("Risk Level", format="%d", min_value=0, max_value=4),
                "Priority": st.column_config.NumberColumn("Priority Score", format="%.2f"),
            },
        )
    else:
        st.info("No allocation plan generated yet.")

    st.divider()
    st.subheader("📊 Detailed Prediction Data")
    if summary["map_data"]:
        pred_df = pd.DataFrame(summary["map_data"])
        cols = [c for c in ("district", "risk_level", "risk_probability") if c in pred_df.columns]
        st.dataframe(pred_df[cols], use_container_width=True)


def main() -> None:
    init_session()
    st.sidebar.title("🎮 Controls")
    mode = st.sidebar.radio("Mode", ["Chat Assistant", "Live Dashboard"])
    if mode == "Chat Assistant":
        st.sidebar.markdown(
            """
            **Chat Mode**
            - 'Run resource allocation'
            - 'Show risk map'
            - 'Show heatmap'
            """
        )
        if st.sidebar.button("Clear Chat"):
            st.session_state.messages = []
        if st.sidebar.button("♻️ Reload System"):
            st.session_state.clear()
            st.rerun()
        render_chat()
    else:
        render_dashboard()


main()
