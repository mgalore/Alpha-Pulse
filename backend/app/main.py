from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Alpha-Pulse API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Alpha-Pulse API"}

@app.get("/api/yield-curve")
def get_yield_curve(date: Optional[str] = None):
    """Get yield curve points for a specific date"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        response = supabase.table("yield_curve_points")\
            .select("*")\
            .eq("date", date)\
            .order("maturity_days")\
            .execute()
        
        return {"date": date, "curve_points": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-summary")
def get_market_summary(date: Optional[str] = None):
    """Get daily market summary"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        response = supabase.table("daily_market_summary")\
            .select("*")\
            .eq("date", date)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="No data for this date")
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/security-metrics")
def get_security_metrics(date: Optional[str] = None, security_type: Optional[str] = None):
    """Get security metrics with optional filters"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        query = supabase.table("security_metrics").select("*").eq("date", date)
        
        if security_type:
            query = query.eq("security_type", security_type)
        
        response = query.order("ytm", desc=True).execute()
        
        return {"date": date, "count": len(response.data), "metrics": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/corporate-spreads")
def get_corporate_spreads(date: Optional[str] = None):
    """Get corporate bond spreads vs government"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        response = supabase.table("security_metrics")\
            .select("isin, issuer, ytm, spread_vs_govt, benchmark_yield, liquidity_score")\
            .eq("date", date)\
            .eq("security_type", "CORPORATE")\
            .not_.is_("spread_vs_govt", "null")\
            .order("spread_vs_govt", desc=True)\
            .execute()
        
        return {"date": date, "spreads": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-alerts")
def get_market_alerts(days: int = 7):
    """Get recent market alerts"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        response = supabase.table("market_alerts")\
            .select("*")\
            .gte("date", cutoff_date)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"alerts": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/top-securities")
def get_top_securities(metric: str = "ytm", limit: int = 10, date: Optional[str] = None):
    """Get top securities by metric (ytm, volume, spread_vs_govt)"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        valid_metrics = ["ytm", "volume", "spread_vs_govt", "real_yield"]
        if metric not in valid_metrics:
            raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")
        
        response = supabase.table("security_metrics")\
            .select("isin, issuer, security_type, ytm, real_yield, volume, spread_vs_govt, liquidity_score")\
            .eq("date", date)\
            .not_.is_(metric, "null")\
            .order(metric, desc=True)\
            .limit(limit)\
            .execute()
        
        return {"metric": metric, "top_securities": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/treasury-bills")
def get_treasury_bills(date: Optional[str] = None):
    """Get T-Bill data"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        response = supabase.table("treasury_bills")\
            .select("*")\
            .eq("date", date)\
            .order("days_to_maturity")\
            .execute()
        
        return {"date": date, "tbills": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bog-auction-results")
def get_bog_auction_results(date: Optional[str] = None, days: int = 30):
    """Get BoG auction results"""
    try:
        if date:
            response = supabase.table("bog_auction_results")\
                .select("*")\
                .eq("auction_date", date)\
                .order("tenor")\
                .execute()
        else:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            response = supabase.table("bog_auction_results")\
                .select("*")\
                .gte("auction_date", cutoff_date)\
                .order("auction_date", desc=True)\
                .execute()
        
        return {"results": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bog-auction-summary")
def get_bog_auction_summary(days: int = 90):
    """Get BoG auction summary over time"""
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        response = supabase.table("bog_auction_summary")\
            .select("*")\
            .gte("auction_date", cutoff_date)\
            .order("auction_date", desc=True)\
            .execute()
        
        return {"summaries": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/primary-vs-secondary")
def compare_primary_vs_secondary(date: Optional[str] = None):
    """Compare primary market (auction) vs secondary market (GFIM) rates"""
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Get auction data
        auction_response = supabase.table("bog_auction_results")\
            .select("tenor, weighted_average_rate, amount_tendered, amount_accepted, bid_cover_ratio")\
            .eq("auction_date", date)\
            .execute()
        
        # Get secondary market data for T-Bills
        secondary_response = supabase.table("security_metrics")\
            .select("isin, ytm, volume")\
            .eq("date", date)\
            .eq("security_type", "TBILL")\
            .execute()
        
        return {
            "date": date,
            "primary_market": auction_response.data,
            "secondary_market": secondary_response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
