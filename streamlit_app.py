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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Yield Curve", "💰 Corporate Spreads", "🔔 Alerts", "📊 Top Securities", "🏦 BoG Auctions"])

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
        
        # Use ISIN for chart display
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_spreads["isin"],
            y=df_spreads["spread_vs_govt"],
            marker_color='#FF6B6B',
            text=df_spreads["spread_vs_govt"].round(2),
            textposition='outside',
            hovertemplate='<b>%{customdata[0]}</b><br>ISIN: %{x}<br>Spread: %{y:.2f}%<br>YTM: %{customdata[1]:.2f}%<extra></extra>',
            customdata=df_spreads[["issuer", "ytm"]].values
        ))
        
        fig.update_layout(
            xaxis_title="ISIN",
            yaxis_title="Spread vs GOG (%)",
            height=400,
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show table with issuer names
        display_df = df_spreads[["issuer", "isin", "ytm", "benchmark_yield", "spread_vs_govt", "liquidity_score"]].copy()
        display_df.columns = ["Issuer", "ISIN", "YTM (%)", "Benchmark (%)", "Spread (%)", "Liquidity"]
        st.dataframe(display_df, use_container_width=True)
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
        
        # Rename columns for better display
        display_df = df_top[["issuer", "isin", "security_type", "ytm", "real_yield", "volume", "liquidity_score"]].copy()
        display_df.columns = ["Issuer", "ISIN", "Type", "YTM (%)", "Real Yield (%)", "Volume", "Liquidity"]
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No data available")

# Footer
st.sidebar.divider()
st.sidebar.info("**Alpha-Pulse GFIM** v1.0\n\nReal-time Ghana Fixed Income Analytics")


with tab5:
    st.subheader("Bank of Ghana Auction Results (Primary Market)")
    
    auction_data = fetch_data("bog-auction-results", {"date": selected_date})
    
    if auction_data and auction_data.get("results"):
        df_auction = pd.DataFrame(auction_data["results"])
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        total_tendered = df_auction["amount_tendered"].sum()
        total_accepted = df_auction["amount_accepted"].sum()
        avg_bid_cover = df_auction["bid_cover_ratio"].mean()
        
        with col1:
            st.metric("Total Tendered", f"GH₵ {total_tendered:,.0f}M")
        with col2:
            st.metric("Total Accepted", f"GH₵ {total_accepted:,.0f}M")
        with col3:
            st.metric("Avg Bid-Cover Ratio", f"{avg_bid_cover:.2f}x")
        
        # Bid-Cover Ratio Chart
        st.markdown("#### Bid-Cover Ratio by Tenor")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_auction["tenor"],
            y=df_auction["bid_cover_ratio"],
            marker_color='#3ECF8E',
            text=df_auction["bid_cover_ratio"].round(2),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Bid-Cover: %{y:.2f}x<br>Rate: %{customdata:.2f}%<extra></extra>',
            customdata=df_auction["weighted_average_rate"]
        ))
        
        fig.update_layout(
            xaxis_title="Tenor",
            yaxis_title="Bid-Cover Ratio",
            height=350
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Rates Comparison
        st.markdown("#### Auction Rates")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_auction["tenor"],
            y=df_auction["discount_rate"],
            mode='lines+markers',
            name='Discount Rate',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=10)
        ))
        fig2.add_trace(go.Scatter(
            x=df_auction["tenor"],
            y=df_auction["interest_rate"],
            mode='lines+markers',
            name='Interest Rate',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=10)
        ))
        
        fig2.update_layout(
            xaxis_title="Tenor",
            yaxis_title="Rate (%)",
            height=350,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Data Table
        st.markdown("#### Detailed Results")
        display_df = df_auction[["tenor", "isin", "amount_tendered", "amount_accepted", "bid_cover_ratio", "discount_rate", "interest_rate"]].copy()
        display_df.columns = ["Tenor", "ISIN", "Tendered (M)", "Accepted (M)", "Bid-Cover", "Discount Rate (%)", "Interest Rate (%)"]
        st.dataframe(display_df, use_container_width=True)
        
        # Market Insights
        st.markdown("#### 💡 Market Insights")
        if avg_bid_cover > 2.5:
            st.success(f"🔥 Strong demand! Bid-cover ratio of {avg_bid_cover:.2f}x indicates high investor appetite for government securities.")
        elif avg_bid_cover > 1.5:
            st.info(f"✅ Healthy demand with {avg_bid_cover:.2f}x bid-cover ratio.")
        else:
            st.warning(f"⚠️ Weak demand. Bid-cover ratio of {avg_bid_cover:.2f}x suggests limited investor interest.")
    else:
        st.info(f"No auction data available for {selected_date}")
