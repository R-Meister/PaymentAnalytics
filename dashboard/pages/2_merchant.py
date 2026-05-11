import streamlit as st
import pandas as pd
from utils import get

st.title("Merchant Intelligence")

tab1, tab2, tab3 = st.tabs(["Top Merchants", "All Merchants", "Sentiment"])

with tab1:
    st.subheader("Top Merchants by Revenue")
    top = get("/api/merchants/top/by-revenue", params={"limit": 20})
    df_top = pd.DataFrame(top)
    if not df_top.empty:
        df_top["revenue"] = df_top["revenue"].apply(lambda x: f"₹{x:,.2f}")
        df_top["fraud_pct"] = df_top["fraud_pct"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(
            df_top[["merchant_id", "merchant_name", "category", "city", "revenue", "total_txns", "unique_customers", "fraud_pct"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.subheader("Merchant Directory")
    search = st.text_input("Search merchants", "")
    category = st.selectbox(
        "Category",
        ["All", "Electronics", "Fashion", "Food & Dining", "Travel", "Entertainment",
         "Groceries", "Health & Wellness", "Education", "Utilities", "Home & Garden"],
    )

    params = {"limit": 50}
    if search:
        params["search"] = search
    if category != "All":
        params["category"] = category

    merchants = get("/api/merchants", params=params)
    df_merch = pd.DataFrame(merchants.get("results", []))
    if not df_merch.empty:
        df_merch["revenue"] = df_merch["revenue"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(
            df_merch[["merchant_id", "merchant_name", "category", "city", "revenue", "total_txns", "unique_customers", "status"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No merchants found.")

with tab3:
    st.subheader("Merchant Sentiment Analysis")
    sentiment = get("/api/merchants/sentiment", params={"limit": 50})
    df_sent = pd.DataFrame(sentiment.get("results", []))
    if not df_sent.empty:
        df_sent["avg_polarity"] = df_sent["avg_polarity"].apply(lambda x: f"{x:+.3f}")
        df_sent["avg_rating"] = df_sent["avg_rating"].apply(lambda x: f"{x:.1f}⭐")
        st.dataframe(
            df_sent[["merchant_name", "category", "city", "review_count", "avg_rating", "avg_polarity", "positive_count", "negative_count"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No sentiment data available.")
