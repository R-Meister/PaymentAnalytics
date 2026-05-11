import streamlit as st

st.set_page_config(
    page_title="Payment Analytics",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("Payment Analytics")
st.sidebar.markdown("Enterprise payment intelligence platform")
st.sidebar.divider()

pages = {
    "Executive": "pages/1_executive.py",
    "Merchants": "pages/2_merchant.py",
    "Fraud": "pages/3_fraud.py",
    "Customers": "pages/4_customer.py",
}

selected = st.sidebar.radio("Navigate", list(pages.keys()))

st.sidebar.divider()
st.sidebar.markdown("Built with FastAPI + PostgreSQL + Streamlit")
