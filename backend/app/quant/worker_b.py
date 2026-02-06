"""
Worker B: Quant Engine
Calculates financial metrics from Bronze Layer data and populates Silver Layer tables.

Run: python backend/app/quant/worker_b.py [date]
Example: python backend/app/quant/worker_b.py 2026-01-30
"""

import os
import sys
import math
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.error("Supabase credentials not found")
    sys.exit(1)

# --- Constants ---
GHANA_INFLATION_RATE = 23.2  # Latest Ghana CPI (%)
GHANA_POLICY_RATE = 29.0     # BoG policy rate (%)

# Maturity buckets for yield curve
MATURITY_BUCKETS = [
    (0, 91, "91D"),
    (92, 182, "182D"),
    (183, 365, "1Y"),
    (366, 730, "2Y"),
    (731, 1095, "3Y"),
    (1096, 1825, "5Y"),
    (1826, 3650, "10Y"),
    (3651, 7300, "20Y"),
]

# All possible keys for security_metrics - ensures consistent schema
METRIC_KEYS = [
    "date", "isin", "security_type",
    "ytm", "discount_yield", "bond_equivalent_yield", "real_yield", "coupon_rate",
    "volume", "turnover_ratio", "hl_spread", "liquidity_score",
    "modified_duration", "convexity", "z_spread", "corporate_spread",
    "benchmark_yield", "spread_vs_govt", "volume_avg_30d", "volume_spike_flag", "liquidity_flag"
]

# Volume spike threshold (300% of average)
VOLUME_SPIKE_THRESHOLD = 3.0

def normalize_metric_record(record: Dict) -> Dict:
    """Ensure all records have the same keys (required by Supabase upsert)"""
    return {k: record.get(k) for k in METRIC_KEYS}

def get_maturity_bucket(days: int) -> str:
    """Map days to maturity bucket"""
    for low, high, bucket in MATURITY_BUCKETS:
        if low <= days <= high:
            return bucket
    return "20Y+"

# --- YTM Calculations ---

def calculate_tbill_yields(price: float, days_to_maturity: int) -> Dict[str, float]:
    """
    Calculate T-Bill yields.
    T-Bills are sold at discount, no coupon.
    
    Discount Yield = (100 - Price) / 100 * (360 / Days)
    Bond Equivalent Yield = (100 - Price) / Price * (365 / Days)
    """
    if not price or not days_to_maturity or days_to_maturity <= 0:
        return {}
    
    face_value = 100
    discount = face_value - price
    
    # Discount Yield (Bank Discount Basis)
    discount_yield = (discount / face_value) * (360 / days_to_maturity) * 100
    
    # Bond Equivalent Yield (for comparison with bonds)
    bey = (discount / price) * (365 / days_to_maturity) * 100
    
    return {
        "discount_yield": round(discount_yield, 4),
        "bond_equivalent_yield": round(bey, 4),
        "ytm": round(bey, 4)  # Use BEY as YTM for T-Bills
    }

def calculate_bond_ytm(price: float, coupon_rate: float, days_to_maturity: int) -> float:
    """
    Approximate YTM using simplified formula.
    Full YTM requires iterative solving; this uses Current Yield + Capital Gain approximation.
    
    YTM ≈ (Coupon + (Face - Price) / Years) / ((Face + Price) / 2)
    """
    if not price or price <= 0 or not days_to_maturity or days_to_maturity <= 0:
        return None
    
    face_value = 100
    years = days_to_maturity / 365
    
    if years <= 0:
        return None
    
    coupon = coupon_rate if coupon_rate else 0
    annual_coupon = coupon  # Already in %
    
    # Approximate YTM
    capital_gain_per_year = (face_value - price) / years
    avg_price = (face_value + price) / 2
    ytm = ((annual_coupon + capital_gain_per_year) / avg_price) * 100
    
    return round(ytm, 4)

def extract_coupon_from_description(desc: str) -> Optional[float]:
    """
    Extract coupon rate from security description.
    Examples: "GOG-BD-17/08/27-A6139-1838-10.00" -> 10.00
              "LGH-BD-13/03/28-C0896-30.25" -> 30.25
    """
    if not desc:
        return None
    try:
        # Look for pattern like "-XX.XX" at the end
        parts = desc.split("-")
        for part in reversed(parts):
            try:
                val = float(part)
                if 0 < val < 100:  # Reasonable coupon range
                    return val
            except ValueError:
                continue
        return None
    except Exception:
        return None

# --- Duration Calculations ---

def calculate_modified_duration(ytm: float, years_to_maturity: float, coupon_rate: float) -> float:
    """
    Simplified Modified Duration.
    For zero-coupon: Duration = Years to Maturity
    For coupon bonds: Duration ≈ (1 + YTM/100) / (YTM/100) * (1 - 1/(1+YTM/100)^Years)
    
    Using Macaulay Duration approximation for simplicity.
    """
    if not ytm or ytm <= 0 or not years_to_maturity or years_to_maturity <= 0:
        return None
    
    # For T-Bills (zero coupon), duration = maturity
    if not coupon_rate or coupon_rate == 0:
        return round(years_to_maturity, 2)
    
    # Simplified approximation for coupon bonds
    y = ytm / 100
    n = years_to_maturity
    
    # Modified Duration ≈ Macaulay Duration / (1 + y)
    # Using rough approximation
    mac_duration = (1 + y) / y - (1 + y + n * (coupon_rate/100 - y)) / (coupon_rate/100 * ((1 + y)**n - 1) + y)
    
    # Fallback: simpler approximation
    try:
        if mac_duration < 0 or mac_duration > n:
            mac_duration = n * 0.8  # Rough estimate
        mod_duration = mac_duration / (1 + y)
        return round(mod_duration, 2)
    except:
        return round(n * 0.7, 2)  # Very rough fallback

# --- Liquidity Metrics ---

def calculate_liquidity_score(volume: float, hl_spread: float) -> str:
    """
    Simple liquidity classification.
    """
    if volume is None:
        return "LOW"
    
    if volume > 10_000_000:
        return "HIGH"
    elif volume > 1_000_000:
        return "MEDIUM"
    else:
        return "LOW"

# --- Main Processing Functions ---

def process_gog_bonds(trade_date: str, table_name: str, security_type: str) -> List[Dict]:
    """Process GOG bonds and return metrics"""
    logger.info(f"Processing {table_name}...")
    
    response = supabase.table(table_name).select("*").eq("date", trade_date).execute()
    records = response.data
    
    metrics = []
    for r in records:
        try:
            price = r.get("closing_price")
            days = r.get("days_to_maturity")
            desc = r.get("security_description")
            
            coupon = extract_coupon_from_description(desc)
            ytm = calculate_bond_ytm(price, coupon, days) if price and days else r.get("closing_yield")
            
            # If no YTM calculated, use closing_yield from source
            if not ytm:
                ytm = r.get("closing_yield")
            
            real_yield = round(ytm - GHANA_INFLATION_RATE, 2) if ytm else None
            
            hl_spread = None
            high_y = r.get("day_high_yield")
            low_y = r.get("day_low_yield")
            if high_y and low_y:
                hl_spread = round(abs(high_y - low_y), 4)
            
            volume = r.get("volume")
            
            years = days / 365 if days else None
            mod_duration = calculate_modified_duration(ytm, years, coupon) if ytm and years else None
            
            metrics.append({
                "date": trade_date,
                "isin": r["isin"],
                "security_type": security_type,
                "ytm": ytm,
                "real_yield": real_yield,
                "coupon_rate": coupon,
                "volume": volume,
                "hl_spread": hl_spread,
                "liquidity_score": calculate_liquidity_score(volume, hl_spread),
                "modified_duration": mod_duration
            })
        except Exception as e:
            logger.warning(f"Error processing {r.get('isin')}: {e}")
    
    return metrics

def process_tbills(trade_date: str) -> List[Dict]:
    """Process Treasury Bills"""
    logger.info("Processing treasury_bills...")
    
    response = supabase.table("treasury_bills").select("*").eq("date", trade_date).execute()
    records = response.data
    
    metrics = []
    for r in records:
        try:
            price = r.get("closing_price")
            days = r.get("days_to_maturity")
            
            yields = calculate_tbill_yields(price, days) if price and days else {}
            
            real_yield = round(yields.get("ytm", 0) - GHANA_INFLATION_RATE, 2) if yields.get("ytm") else None
            
            volume = r.get("volume_traded")
            
            hl_spread = None
            high_y = r.get("day_high_yield")
            low_y = r.get("day_low_yield")
            if high_y and low_y:
                hl_spread = round(abs(high_y - low_y), 4)
            
            years = days / 365 if days else None
            
            metrics.append({
                "date": trade_date,
                "isin": r["isin"],
                "security_type": "TBILL",
                "ytm": yields.get("ytm"),
                "discount_yield": yields.get("discount_yield"),
                "bond_equivalent_yield": yields.get("bond_equivalent_yield"),
                "real_yield": real_yield,
                "volume": volume,
                "hl_spread": hl_spread,
                "liquidity_score": calculate_liquidity_score(volume, hl_spread),
                "modified_duration": round(years, 2) if years else None  # Duration = Maturity for T-Bills
            })
        except Exception as e:
            logger.warning(f"Error processing T-Bill {r.get('isin')}: {e}")
    
    return metrics

def process_corporate(trade_date: str) -> List[Dict]:
    """Process Corporate Bonds"""
    logger.info("Processing corporate...")
    
    response = supabase.table("corporate").select("*").eq("date", trade_date).execute()
    records = response.data
    
    metrics = []
    for r in records:
        try:
            price = r.get("closing_price")
            days = r.get("days_to_maturity")
            desc = r.get("security_description")
            
            coupon = extract_coupon_from_description(desc)
            ytm = calculate_bond_ytm(price, coupon, days) if price and days else None
            
            # Fallback to day_high_yield if no price
            if not ytm:
                ytm = r.get("day_high_yield")
            
            real_yield = round(ytm - GHANA_INFLATION_RATE, 2) if ytm else None
            
            volume = r.get("volume_traded")
            
            years = days / 365 if days else None
            mod_duration = calculate_modified_duration(ytm, years, coupon) if ytm and years else None
            
            metrics.append({
                "date": trade_date,
                "isin": r["isin"],
                "security_type": "CORPORATE",
                "ytm": ytm,
                "real_yield": real_yield,
                "coupon_rate": coupon,
                "volume": volume,
                "liquidity_score": calculate_liquidity_score(volume, None),
                "modified_duration": mod_duration
            })
        except Exception as e:
            logger.warning(f"Error processing Corporate {r.get('isin')}: {e}")
    
    return metrics

def build_yield_curve(trade_date: str, all_metrics: List[Dict]) -> List[Dict]:
    """Build yield curve points from GOG bonds and T-Bills"""
    logger.info("Building yield curve...")
    
    # Get all GOG/TBILL securities with days_to_maturity
    gog_data = []
    
    # Query original tables for days_to_maturity
    for table in ["new_gog_notes_and_bonds", "old_gog_notes_and_bonds", "treasury_bills"]:
        response = supabase.table(table).select("isin, days_to_maturity").eq("date", trade_date).execute()
        for r in response.data:
            gog_data.append(r)
    
    # Map ISIN to days
    isin_to_days = {r["isin"]: r.get("days_to_maturity") for r in gog_data}
    
    # Bucket yields
    bucket_yields = {}
    for m in all_metrics:
        if m["security_type"] in ["GOG_BOND", "TBILL"] and m.get("ytm"):
            days = isin_to_days.get(m["isin"])
            if days:
                bucket = get_maturity_bucket(days)
                if bucket not in bucket_yields:
                    bucket_yields[bucket] = []
                bucket_yields[bucket].append((days, m["ytm"]))
    
    # Average per bucket
    curve_points = []
    for bucket, items in bucket_yields.items():
        avg_days = sum(d for d, y in items) / len(items)
        avg_yield = sum(y for d, y in items) / len(items)
        curve_points.append({
            "date": trade_date,
            "maturity_days": int(avg_days),
            "maturity_bucket": bucket,
            "yield": round(avg_yield, 4),
            "curve_type": "GOG"
        })
    
    return curve_points

def build_daily_summary(trade_date: str, all_metrics: List[Dict], curve_points: List[Dict]) -> Dict:
    """Build daily market summary"""
    logger.info("Building daily summary...")
    
    # Curve shape
    sorted_curve = sorted(curve_points, key=lambda x: x["maturity_days"])
    
    curve_shape = "NORMAL"
    curve_slope = 0
    spread_91d_10y = None
    
    if len(sorted_curve) >= 2:
        short_yield = sorted_curve[0]["yield"]
        long_yield = sorted_curve[-1]["yield"]
        curve_slope = round(long_yield - short_yield, 2)
        
        if curve_slope < -0.5:
            curve_shape = "INVERTED"
        elif curve_slope < 0.5:
            curve_shape = "FLAT"
        else:
            curve_shape = "NORMAL"
    
    # Find 91D and 10Y for spread
    yield_91d = next((p["yield"] for p in curve_points if p["maturity_bucket"] == "91D"), None)
    yield_10y = next((p["yield"] for p in curve_points if p["maturity_bucket"] == "10Y"), None)
    if yield_91d and yield_10y:
        spread_91d_10y = round(yield_10y - yield_91d, 2)
    
    # Volumes
    vol_gog = sum(m.get("volume") or 0 for m in all_metrics if m["security_type"] == "GOG_BOND")
    vol_tbill = sum(m.get("volume") or 0 for m in all_metrics if m["security_type"] == "TBILL")
    vol_corp = sum(m.get("volume") or 0 for m in all_metrics if m["security_type"] == "CORPORATE")
    
    # Most active
    most_active = max(all_metrics, key=lambda x: x.get("volume") or 0, default={})
    
    return {
        "date": trade_date,
        "curve_shape": curve_shape,
        "curve_slope": curve_slope,
        "spread_91d_10y": spread_91d_10y,
        "total_volume_gog": vol_gog,
        "total_volume_tbill": vol_tbill,
        "total_volume_corporate": vol_corp,
        "most_active_isin": most_active.get("isin"),
        "inflation_rate": GHANA_INFLATION_RATE,
        "policy_rate": GHANA_POLICY_RATE
    }

def calculate_corporate_spreads(all_metrics: List[Dict], curve_points: List[Dict]) -> List[Dict]:
    """
    Calculate Corporate Spread vs Government Benchmark.
    For each corporate bond, find the nearest maturity GOG yield and compute spread.
    """
    logger.info("Calculating corporate spreads...")
    
    # Build maturity -> yield lookup from curve
    bucket_to_yield = {p["maturity_bucket"]: p["yield"] for p in curve_points}
    
    # Get days_to_maturity for corporates from the database
    response = supabase.table("corporate").select("isin, days_to_maturity").execute()
    isin_to_days = {r["isin"]: r.get("days_to_maturity") for r in response.data}
    
    alerts = []
    
    for m in all_metrics:
        if m["security_type"] == "CORPORATE" and m.get("ytm"):
            days = isin_to_days.get(m["isin"])
            if days:
                bucket = get_maturity_bucket(days)
                benchmark = bucket_to_yield.get(bucket)
                
                if benchmark:
                    m["benchmark_yield"] = round(benchmark, 4)
                    spread = round(m["ytm"] - benchmark, 4)
                    m["spread_vs_govt"] = spread
                    
                    # Check for wide spread (potential opportunity alert)
                    if spread > 5.0:  # 5% spread is significant
                        alerts.append({
                            "date": m["date"],
                            "isin": m["isin"],
                            "alert_type": "SPREAD_WIDENING",
                            "alert_message": f"Corporate spread at {spread:.2f}% vs benchmark {benchmark:.2f}%",
                            "severity": "INFO"
                        })
    
    return alerts

def detect_volume_spikes(trade_date: str, all_metrics: List[Dict]) -> List[Dict]:
    """
    Detect volume spikes by comparing today's volume to historical average.
    Flags securities with >300% of 30-day average volume.
    """
    logger.info("Detecting volume spikes...")
    
    alerts = []
    
    # Get historical volume data (last 30 days)
    # Since we may not have 30 days of data yet, we use what's available
    for m in all_metrics:
        isin = m["isin"]
        today_volume = m.get("volume")
        
        if not today_volume or today_volume <= 0:
            m["liquidity_flag"] = "STALE"
            continue
        
        m["liquidity_flag"] = "ACTIVE"
        
        # Query historical volumes for this ISIN
        try:
            response = supabase.table("security_metrics")\
                .select("volume")\
                .eq("isin", isin)\
                .neq("date", trade_date)\
                .order("date", desc=True)\
                .limit(30)\
                .execute()
            
            historical_volumes = [r["volume"] for r in response.data if r.get("volume")]
            
            if historical_volumes:
                avg_volume = sum(historical_volumes) / len(historical_volumes)
                m["volume_avg_30d"] = round(avg_volume, 2)
                
                # Check for spike
                if avg_volume > 0 and today_volume >= (avg_volume * VOLUME_SPIKE_THRESHOLD):
                    m["volume_spike_flag"] = True
                    alerts.append({
                        "date": trade_date,
                        "isin": isin,
                        "alert_type": "VOLUME_SPIKE",
                        "alert_message": f"Volume spike: {today_volume:,.0f} vs avg {avg_volume:,.0f} ({today_volume/avg_volume:.1f}x)",
                        "severity": "WARNING"
                    })
                else:
                    m["volume_spike_flag"] = False
        except Exception as e:
            logger.warning(f"Could not calculate volume history for {isin}: {e}")
    
    return alerts

def run_quant_engine(trade_date: str):
    """Main entry point"""
    logger.info(f"=== QUANT ENGINE: Processing {trade_date} ===")
    
    # Collect all metrics
    all_metrics = []
    
    # Process each security type
    all_metrics.extend(process_gog_bonds(trade_date, "new_gog_notes_and_bonds", "GOG_BOND"))
    all_metrics.extend(process_gog_bonds(trade_date, "old_gog_notes_and_bonds", "GOG_BOND"))
    all_metrics.extend(process_tbills(trade_date))
    all_metrics.extend(process_corporate(trade_date))
    
    logger.info(f"Total securities processed: {len(all_metrics)}")
    
    # Build yield curve
    curve_points = build_yield_curve(trade_date, all_metrics)
    logger.info(f"Yield curve points: {len(curve_points)}")
    
    # --- ALPHA LOGIC ---
    
    # Calculate Corporate Spreads vs Government Benchmark
    spread_alerts = calculate_corporate_spreads(all_metrics, curve_points)
    
    # Detect Volume Spikes (compare to historical average)
    volume_alerts = detect_volume_spikes(trade_date, all_metrics)
    
    # Combine all alerts
    all_alerts = spread_alerts + volume_alerts
    logger.info(f"Generated {len(all_alerts)} market alerts")
    
    # Build daily summary
    summary = build_daily_summary(trade_date, all_metrics, curve_points)
    
    # --- UPSERT TO SILVER LAYER ---
    
    # 1. Security Metrics - normalize all records to have same keys
    if all_metrics:
        normalized_metrics = [normalize_metric_record(m) for m in all_metrics]
        logger.info(f"Upserting {len(normalized_metrics)} to security_metrics...")
        supabase.table("security_metrics").upsert(normalized_metrics, on_conflict="date, isin").execute()
        logger.info("Success: security_metrics")
    
    # 2. Yield Curve Points
    if curve_points:
        logger.info(f"Upserting {len(curve_points)} to yield_curve_points...")
        supabase.table("yield_curve_points").upsert(curve_points, on_conflict="date, maturity_bucket, curve_type").execute()
        logger.info("Success: yield_curve_points")
    
    # 3. Daily Summary
    logger.info("Upserting daily_market_summary...")
    supabase.table("daily_market_summary").upsert([summary], on_conflict="date").execute()
    logger.info("Success: daily_market_summary")
    
    # 4. Market Alerts
    if all_alerts:
        logger.info(f"Inserting {len(all_alerts)} market alerts...")
        supabase.table("market_alerts").insert(all_alerts).execute()
        logger.info("Success: market_alerts")
    
    logger.info("=== QUANT ENGINE COMPLETE ===")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
    else:
        date_arg = datetime.now().strftime("%Y-%m-%d")
    
    run_quant_engine(date_arg)
