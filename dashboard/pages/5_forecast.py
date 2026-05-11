import streamlit as st
import pandas as pd
from utils import get

st.title("Forecasting")

data = get("/api/forecast")

left, right = st.columns(2)

with left:
    st.subheader("Transaction Volume Forecast (30 Days)")
    df_hist = pd.DataFrame(data["historical"])
    df_fc = pd.DataFrame(data["forecast_transactions"])

    if not df_hist.empty and not df_fc.empty:
        df_hist["date"] = pd.to_datetime(df_hist["date"])
        df_fc["forecast_date"] = pd.to_datetime(df_fc["forecast_date"])

        df_combined = pd.concat([
            df_hist[["date", "transactions"]].rename(columns={"date": "ds", "transactions": "y"}),
            df_fc[["forecast_date", "forecast_value"]].rename(columns={"forecast_date": "ds", "forecast_value": "y"}),
        ])
        df_combined = df_combined.set_index("ds")
        st.line_chart(df_combined, use_container_width=True)

with right:
    st.subheader("Revenue Forecast (30 Days)")
    df_fc_rev = pd.DataFrame(data["forecast_revenue"])

    if not df_hist.empty and not df_fc_rev.empty:
        df_fc_rev["forecast_date"] = pd.to_datetime(df_fc_rev["forecast_date"])

        df_combined_rev = pd.concat([
            df_hist[["date", "revenue"]].rename(columns={"date": "ds", "revenue": "y"}),
            df_fc_rev[["forecast_date", "forecast_value"]].rename(columns={"forecast_date": "ds", "forecast_value": "y"}),
        ])
        df_combined_rev = df_combined_rev.set_index("ds")
        st.line_chart(df_combined_rev, use_container_width=True)

st.divider()

st.subheader("Forecast Details")
cols = st.columns(2)

with cols[0]:
    st.markdown("**Transaction Forecasts**")
    if not df_fc.empty:
        df_fc["forecast_value"] = df_fc["forecast_value"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_fc[["forecast_date", "forecast_value"]], hide_index=True, use_container_width=True)

with cols[1]:
    st.markdown("**Revenue Forecasts**")
    if not df_fc_rev.empty:
        df_fc_rev["forecast_value"] = df_fc_rev["forecast_value"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_fc_rev[["forecast_date", "forecast_value"]], hide_index=True, use_container_width=True)
