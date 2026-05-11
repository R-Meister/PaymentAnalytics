import streamlit as st
import pandas as pd
from utils import get

st.title("Customer Insights")

tab1, tab2, tab3 = st.tabs(["Segments", "ML Segments", "Customers"])

with tab1:
    st.subheader("Customer Segments (Heuristic)")
    segments = get("/api/customers/segments")
    df_seg = pd.DataFrame(segments)
    if not df_seg.empty:
        df_seg["avg_spend"] = df_seg["avg_spend"].apply(lambda x: f"₹{x:,.2f}")
        df_seg["total_revenue"] = df_seg["total_revenue"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(
            df_seg[["segment", "customer_count", "avg_spend", "avg_transactions", "total_revenue"]],
            use_container_width=True,
            hide_index=True,
        )

        # Pie chart
        df_chart = pd.DataFrame(segments)
        df_chart = df_chart.set_index("segment")[["customer_count"]]
        st.bar_chart(df_chart, use_container_width=True)

with tab2:
    st.subheader("Customer Segments (KMeans ML)")
    ml_segments = get("/api/customers/segments/ml")
    df_ml = pd.DataFrame(ml_segments)
    if not df_ml.empty:
        df_ml["avg_spend"] = df_ml["avg_spend"].apply(lambda x: f"₹{x:,.2f}")
        df_ml["avg_recency_days"] = df_ml["avg_recency_days"].apply(lambda x: f"{x:.1f}")
        st.dataframe(
            df_ml[["segment_name", "customer_count", "avg_spend", "avg_transactions", "avg_merchants", "avg_recency_days"]],
            use_container_width=True,
            hide_index=True,
        )

        df_chart2 = pd.DataFrame(ml_segments)
        df_chart2 = df_chart2.set_index("segment_name")[["customer_count"]]
        st.bar_chart(df_chart2, use_container_width=True)

with tab3:
    st.subheader("Customer Directory")
    city = st.selectbox("City", ["All", "Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune"])
    params = {"limit": 50}
    if city != "All":
        params["city"] = city

    customers = get("/api/customers", params=params)
    df_cust = pd.DataFrame(customers.get("results", []))
    if not df_cust.empty:
        df_cust["total_spend"] = df_cust["total_spend"].apply(lambda x: f"₹{x:,.2f}")
        df_cust["avg_txn_value"] = df_cust["avg_txn_value"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(
            df_cust[["customer_id", "customer_name", "city", "total_spend", "total_txns", "unique_merchants", "fraud_txn_count", "device_preference"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No customers found.")
