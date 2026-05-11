import streamlit as st
import pandas as pd
from utils import get

st.title("Executive Dashboard")

# Load data
summary = get("/api/executive/summary")

# KPIs
st.subheader("Key Performance Indicators")
cols = st.columns(4)
for i, kpi in enumerate(summary["kpis"][:4]):
    val = kpi["value"]
    prefix = kpi.get("prefix", "")
    suffix = kpi.get("suffix", "")
    if isinstance(val, float):
        val = f"{val:,.2f}"
    else:
        val = f"{val:,}"
    cols[i].metric(kpi["label"], f"{prefix}{val}{suffix}")

cols = st.columns(4)
for i, kpi in enumerate(summary["kpis"][4:]):
    val = kpi["value"]
    prefix = kpi.get("prefix", "")
    suffix = kpi.get("suffix", "")
    if isinstance(val, float):
        val = f"{val:,.2f}"
    else:
        val = f"{val:,}"
    cols[i].metric(kpi["label"], f"{prefix}{val}{suffix}")

st.divider()

# Charts
left, right = st.columns(2)

with left:
    st.subheader("Revenue Trend (Last 30 Days)")
    df_trend = pd.DataFrame(summary["daily_trend"])
    if not df_trend.empty:
        df_trend["date"] = pd.to_datetime(df_trend["date"])
        df_trend = df_trend.set_index("date")
        st.line_chart(df_trend[["revenue"]], use_container_width=True)

with right:
    st.subheader("Payment Method Distribution")
    df_pay = pd.DataFrame(summary["payment_distribution"])
    if not df_pay.empty:
        df_pay = df_pay.set_index("payment_method")[["total_amount"]]
        st.bar_chart(df_pay, use_container_width=True)

st.divider()

left2, right2 = st.columns(2)

with left2:
    st.subheader("Revenue by Category")
    df_cat = pd.DataFrame(summary["category_distribution"])
    if not df_cat.empty:
        df_cat = df_cat.sort_values("revenue", ascending=True)
        df_cat = df_cat.set_index("category")[["revenue"]]
        st.bar_chart(df_cat, use_container_width=True)

with right2:
    st.subheader("Daily Transactions")
    if not df_trend.empty:
        st.area_chart(df_trend[["transactions", "success", "failed"]], use_container_width=True)

st.divider()

st.subheader("Fraud Overview")
fraud_cols = st.columns(3)
fraud_cols[0].metric("Fraud Count", f"{summary['fraud_count']:,}")
fraud_cols[1].metric("Fraud Rate", f"{summary['fraud_rate']:.2f}%")
fraud_cols[2].metric("Fraud Amount", f"₹{summary['fraud_amount']:,.2f}")
