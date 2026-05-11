import streamlit as st
import pandas as pd
from utils import get

st.title("Fraud Detection")

tab1, tab2, tab3 = st.tabs(["Summary", "ML Predictions", "Alerts"])

with tab1:
    summary = get("/api/fraud/summary")
    ml_comp = get("/api/fraud/ml-comparison")

    st.subheader("Fraud Overview")
    cols = st.columns(4)
    cols[0].metric("Fraud Txns", f"{summary['fraud_transactions']:,}")
    cols[1].metric("Fraud Rate", f"{summary['fraud_rate']:.2f}%")
    cols[2].metric("Fraud Amount", f"₹{summary['fraud_amount']:,.2f}")
    cols[3].metric("Amount %", f"{summary['fraud_amount_pct']:.2f}%")

    st.subheader("Risk Distribution")
    risk = summary["risk_distribution"]
    df_risk = pd.DataFrame(
        {"level": ["High", "Medium", "Low"], "count": [risk["high"], risk["medium"], risk["low"]]}
    )
    df_risk = df_risk.set_index("level")
    st.bar_chart(df_risk, use_container_width=True)

    st.subheader("Fraud by Hour")
    df_hour = pd.DataFrame(summary["fraud_by_hour"])
    if not df_hour.empty:
        df_hour = df_hour.set_index("transaction_hour")[["fraud_count"]]
        st.bar_chart(df_hour, use_container_width=True)

    st.subheader("Heuristic vs ML Model")
    cols2 = st.columns(4)
    cols2[0].metric("Both Flagged", ml_comp["both_flagged"])
    cols2[1].metric("Heuristic Only", ml_comp["heuristic_only"])
    cols2[2].metric("ML Only", ml_comp["ml_only"])
    cols2[3].metric("Neither", ml_comp["neither"])

with tab2:
    st.subheader("ML Anomaly Predictions (Isolation Forest)")
    preds = get("/api/fraud/ml-predictions", params={"limit": 50})
    df_preds = pd.DataFrame(preds.get("results", []))
    if not df_preds.empty:
        df_preds["amount"] = df_preds["amount"].apply(lambda x: f"₹{x:,.2f}")
        df_preds["model_score"] = df_preds["model_score"].apply(lambda x: f"{x:.4f}")
        st.dataframe(
            df_preds[["transaction_id", "amount", "risk_level", "model_score", "customer_name", "merchant_name", "timestamp"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No ML predictions available.")

with tab3:
    st.subheader("Fraud Alerts")
    alerts = get("/api/fraud/alerts", params={"limit": 50})
    df_alerts = pd.DataFrame(alerts.get("results", []))
    if not df_alerts.empty:
        df_alerts["amount"] = df_alerts["amount"].apply(lambda x: f"₹{x:,.2f}")
        df_alerts["fraud_score"] = df_alerts["fraud_score"].apply(lambda x: f"{x:.4f}")
        st.dataframe(
            df_alerts[["transaction_id", "amount", "fraud_score", "risk_level", "customer_name", "merchant_name", "timestamp"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No fraud alerts.")
