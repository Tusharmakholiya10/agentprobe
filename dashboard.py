import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AgentProbe Dashboard", layout="wide")
st.title("🕵️ AgentProbe Red-Teaming Results")

# Load the data we exported in Phase 6
try:
    df = pd.read_csv("campaign_report.csv")
    
    # High-level metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Runs", len(df))
    col2.metric("Total Cost", f"${df['total_cost'].sum():.4f}")
    col3.metric("Total Tokens", df['total_tokens'].sum())

    # Example Chart: Cost per run
    st.subheader("Cost per Task Execution")
    fig = px.bar(df, x="task_id", y="total_cost", color="task_id", title="Campaign Costs")
    st.plotly_chart(fig, use_container_width=True)

    # Display raw trace data
    st.subheader("Raw Trace Logs")
    st.dataframe(df)

except FileNotFoundError:
    st.error("No campaign_report.csv found. Run your campaign first!")