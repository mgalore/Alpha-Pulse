import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Config
st.set_page_config(page_title="Alpha-Pulse GFIM", page_icon="📊", layout="wide")

API_BASE = "http://localhost:8000/api"

# Helper functions
def fetch_data(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Header
st.title("📊 Alpha-Pulse GFIM Dashboard")
st.markdown("**Ghana Fixed Income Market - Decision Support System**")

# Sidebar
st.sidebar.header("Filters")
date_input = st.sidebar.date_input("Select Date", datetime.now())
selected_date = date_input.strftime("%Y-%m-%d")

# Main Dashboard
col1, col2, col3 = st.columns(3)

# Market Summary
summary = fetch_data("market-summary", {"date": selected_date})
if summary:
    with col1:
        st.metric("Curve Shape", summary.get("curve_shape", "N/A"))
    with col2:
        st.metric("Curve Slope", f"{summary.get('curve_slope', 0):.2f}%")
    with col3:
        st.metric("91D-10Y Spread", f"{summary.get('spread_91d_10y', 0):.2f}%")

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Yield Curve", "💰 Corporate Spreads", "🔔 Alerts", "📊 Top Securities"])

with tab1:
    st.subheader("Ghana Sovereign Yield Curve")
    curve_data = fetch_data("yield-curve", {"date": selected_date})
    
    if curve_data and curve_data.get("curve_points"):
        df_curve = pd.DataFrame(curve_data["curve_points"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_curve["maturity_bucket"],
            y=df_curve["yield"],
            mode='lines+markers',
            name='Yield Curve',
            line=dict(color='#3ECF8E', width=3),
            marker=dict(size=10)
        ))
        
        fig.update_layout(
            xaxis_title="Maturity",
            yaxis_title="Yield (%)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_curve[["maturity_bucket", "yield", "maturity_days"]], use_container_width=True)
    else:
        st.info("No yield curve data available for this date")

with tab2:
    st.subheader("Corporate Bond Spreads vs Government")
    spreads = fetch_data("corporate-spreads", {"date": selected_date})
    
    if spreads and spreads.get("spreads"):
        df_spreads = pd.DataFrame(spreads["spreads"])
        
        # Get issuer info
        df_spreads["display_name"] = df_spreads["isin"]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_spreads["display_name"],
            y=df_spreads["spread_vs_govt"],
            marker_color='#FF6B6B',
            text=df_spreads["spread_vs_govt"].round(2),
            textposition='outside'
        ))
        
        fig.update_layout(
            xaxis_title="Security",
            yaxis_title="Spread vs GOG (%)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_spreads[["isin", "ytm", "benchmark_yield", "spread_vs_govt", "liquidity_score"]], use_container_width=True)
    else:
        st.info("No corporate spread data available")

with tab3:
    st.subheader("Market Alerts (Last 7 Days)")
    alerts = fetch_data("market-alerts", {"days": 7})
    
    if alerts and alerts.get("alerts"):
        df_alerts = pd.DataFrame(alerts["alerts"])
        
        # Color code by severity
        for _, alert in df_alerts.iterrows():
            severity = alert.get("severity", "INFO")
            icon = "🔴" if severity == "WARNING" else "🟡" if severity == "INFO" else "🟢"
            
            st.markdown(f"{icon} **{alert['alert_type']}** - {alert['alert_message']}")
            st.caption(f"Date: {alert['date']} | ISIN: {alert.get('isin', 'N/A')}")
            st.divider()
    else:
        st.info("No recent alerts")

with tab4:
    st.subheader("Top Securities")
    
    metric_choice = st.selectbox("Sort by", ["ytm", "volume", "spread_vs_govt", "real_yield"])
    
    top_securities = fetch_data("top-securities", {"metric": metric_choice, "limit": 10, "date": selected_date})
    
    if top_securities and top_securities.get("top_securities"):
        df_top = pd.DataFrame(top_securities["top_securities"])
        
        st.dataframe(
            df_top[["isin", "security_type", "ytm", "real_yield", "volume", "liquidity_score"]],
            use_container_width=True
        )
    else:
        st.info("No data available")

# Footer
st.sidebar.divider()
st.sidebar.info("**Alpha-Pulse GFIM** v1.0\n\nReal-time Ghana Fixed Income Analytics")
