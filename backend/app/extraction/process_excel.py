import pandas as pd
import logging
import os
import re
from typing import Optional, Any
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Env
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("Supabase credentials not found. Data will not be uploaded.")

def parse_date_from_filename(filepath: str) -> Optional[str]:
    """Extract date from filename (e.g., ...30012026.xlsx -> 2026-01-30)"""
    try:
        filename = os.path.basename(filepath)
        match = re.search(r"(\d{8})", filename)
        if match:
            date_str = match.group(1)
            dt = datetime.strptime(date_str, "%d%m%Y")
            return dt.strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error parsing date from filename: {e}")
        return datetime.now().strftime("%Y-%m-%d")

def parse_date(date_val: Any) -> Optional[str]:
    """Helper to parse Excel dates"""
    try:
        if pd.isna(date_val): return None
        if isinstance(date_val, datetime): return date_val.strftime('%Y-%m-%d')
        return str(date_val).split(' ')[0]
    except Exception:
        return None

def clean_data(val: Any) -> Any:
    """Prepare data for DB"""
    if pd.isna(val): return None
    if isinstance(val, (int, float)): return val
    return str(val).strip()

def process_sheet_data(df: pd.DataFrame, table_name: str, mapping_func, trade_date: str):
    records = []
    # Data starts at row 5 (Index 4)
    data_slice = df.iloc[4:].copy()
    
    for idx, row in data_slice.iterrows():
        try:
            record = mapping_func(row)
            if record:
                record['date'] = trade_date
                # Store full raw row
                raw_dict = {str(k): clean_data(v) for k, v in row.to_dict().items()}
                record['raw_data'] = raw_dict
                records.append(record)
        except Exception:
            pass

    if not records:
        logger.info(f"No records found for {table_name}")
        return

    if supabase:
        try:
            logger.info(f"Upserting {len(records)} records to {table_name}...")
            supabase.table(table_name).upsert(records, on_conflict='date, isin').execute()
            logger.info(f"Success: {table_name}")
        except Exception as e:
            logger.error(f"Failed to upload to {table_name}: {e}")
    else:
        logger.info(f"Dry Run: {len(records)} -> {table_name}")

# --- STRICT 1:1 MAPPERS ---

def map_gog_bond(row):
    # Sheets: NEW GOG NOTES AND BONDS / OLD GOG NOTES AND BONDS
    # 0: NO, 1: TENOR, 2: DESC, 3: ISIN, 4: OPEN YIELD, 5: CLOSE YIELD, 6: CLOSE PRICE, 
    # 7: VOLUME, 8: NUM TRADED, 9: LOW YIELD, 10: HIGH YIELD, 11: DAYS, 12: MATURITY
    
    if len(row) < 4: return None
    isin = clean_data(row.iloc[3])
    if not isin or str(isin).lower() == 'nan': return None
    
    return {
        'isin': isin,
        'tenor': clean_data(row.iloc[1]) if len(row) > 1 else None,
        'security_description': clean_data(row.iloc[2]) if len(row) > 2 else None,
        'opening_yield': clean_data(row.iloc[4]) if len(row) > 4 else None,
        'closing_yield': clean_data(row.iloc[5]) if len(row) > 5 else None,
        'closing_price': clean_data(row.iloc[6]) if len(row) > 6 else None,
        'volume': clean_data(row.iloc[7]) if len(row) > 7 else None,
        'number_traded': clean_data(row.iloc[8]) if len(row) > 8 else None,
        'day_low_yield': clean_data(row.iloc[9]) if len(row) > 9 else None,
        'day_high_yield': clean_data(row.iloc[10]) if len(row) > 10 else None,
        'days_to_maturity': clean_data(row.iloc[11]) if len(row) > 11 else None,
        'maturity_date': parse_date(row.iloc[12]) if len(row) > 12 else None
    }

def map_treasury_bill(row):
    # Sheet: TREASURY BILLS
    # 0: NO, 1: TENOR, 2: TENOR(dup), 3: DESC, 4: ISIN? Wait.
    # Previous analysis for T-Bills was:
    # 0: nan, 1: nan, 2: 91-DAY BILL (Tenor?), 3: 1 (No), 4: Description, 5: ISIN
    # Let's re-verify T-Bill indices from Step 294.
    # Row 5 Data (Indices):
    # 0: nan, 1: nan, 2: 91-DAY BILL (Tenor), 3: 1 (No), 4: Desc, 5: ISIN
    # 6: Open Price, 7: Close Price, 8: Vol, 9: Num Traded, 10: Low Yield, 11: High Yield, 12: Days, 13: Mat Date
    
    if len(row) < 6: return None
    isin = clean_data(row.iloc[5]) # Index 5 is ISIN
    if not isin or str(isin).lower() == 'nan': return None

    return {
        'isin': isin,
        'tenor': clean_data(row.iloc[2]) if len(row) > 2 else None,
        'security_description': clean_data(row.iloc[4]) if len(row) > 4 else None,
        'opening_price': clean_data(row.iloc[6]) if len(row) > 6 else None,
        'closing_price': clean_data(row.iloc[7]) if len(row) > 7 else None,
        'volume_traded': clean_data(row.iloc[8]) if len(row) > 8 else None,
        'number_traded': clean_data(row.iloc[9]) if len(row) > 9 else None,
        'day_low_yield': clean_data(row.iloc[10]) if len(row) > 10 else None,
        'day_high_yield': clean_data(row.iloc[11]) if len(row) > 11 else None,
        'days_to_maturity': clean_data(row.iloc[12]) if len(row) > 12 else None,
        'maturity_date': parse_date(row.iloc[13]) if len(row) > 13 else None
    }

def map_corporate(row, current_issuer):
    # Sheet: CORPORATE (with merged ISSUER cells)
    # 0: Issuer (may be NaN due to merge), 1: No, 2: Desc, 3: ISIN, 4: Open, 5: Close, 6: Vol, 7: Num, 8: Low, 9: High, 10: Days, 11: Mat
    
    if len(row) < 4: return None, current_issuer
    
    # Forward-fill: If issuer is NaN, use the last known issuer
    issuer_val = clean_data(row.iloc[0])
    if issuer_val and str(issuer_val).lower() != 'nan':
        current_issuer = issuer_val
    
    isin = clean_data(row.iloc[3])
    if not isin or str(isin).lower() == 'nan': return None, current_issuer

    record = {
        'isin': isin,
        'issuer': current_issuer,
        'security_description': clean_data(row.iloc[2]),
        'opening_price': clean_data(row.iloc[4]),
        'closing_price': clean_data(row.iloc[5]),
        'volume_traded': clean_data(row.iloc[6]),
        'number_traded': clean_data(row.iloc[7]),
        'day_low_yield': clean_data(row.iloc[8]),
        'day_high_yield': clean_data(row.iloc[9]),
        'days_to_maturity': clean_data(row.iloc[10]),
        'maturity_date': parse_date(row.iloc[11])
    }
    return record, current_issuer

def process_corporate_sheet(df, trade_date):
    """Special processor for CORPORATE with forward-fill and issuer extraction"""
    records = []
    issuer_records = []
    current_issuer = None
    
    data_slice = df.iloc[4:].copy()
    
    for idx, row in data_slice.iterrows():
        try:
            record, current_issuer = map_corporate(row, current_issuer)
            if record:
                record['date'] = trade_date
                raw_dict = {str(k): clean_data(v) for k, v in row.to_dict().items()}
                record['raw_data'] = raw_dict
                records.append(record)
                
                # Also build issuer_securities reference
                issuer_records.append({
                    'issuer': current_issuer,
                    'security_description': record.get('security_description'),
                    'isin': record['isin']
                })
        except Exception:
            pass

    if records and supabase:
        try:
            logger.info(f"Upserting {len(records)} records to corporate...")
            supabase.table("corporate").upsert(records, on_conflict='date, isin').execute()
            logger.info("Success: corporate")
            
            # Also populate issuer_securities
            logger.info(f"Upserting {len(issuer_records)} to issuer_securities...")
            supabase.table("issuer_securities").upsert(issuer_records, on_conflict='isin').execute()
            logger.info("Success: issuer_securities")
        except Exception as e:
            logger.error(f"Failed: {e}")

def map_sell_buy_back(row):
    # Sheet: SELL BUY BACK TRADES-GOG BONDS
    # 0: 1, 1: Tenor, 2: Desc, 3: ISIN, 4: Yield, 5: Price, 6: Vol, 7: Num, 8: Days, 9: Mat
    
    if len(row) < 4: return None
    isin = clean_data(row.iloc[3])
    if not isin or str(isin).lower() == 'nan': return None

    return {
        'isin': isin,
        'tenor': clean_data(row.iloc[1]),
        'security_description': clean_data(row.iloc[2]),
        'yield': clean_data(row.iloc[4]),
        'price_avg': clean_data(row.iloc[5]),
        'volume': clean_data(row.iloc[6]),
        'number_traded': clean_data(row.iloc[7]),
        'days_to_maturity': clean_data(row.iloc[8]),
        'maturity_date': parse_date(row.iloc[9])
    }

def process_excel(filepath):
    logger.info(f"Processing {filepath}...")
    trade_date = parse_date_from_filename(filepath)
    logger.info(f"Trade Date: {trade_date}")
    
    if not trade_date:
        return

    xl = pd.ExcelFile(filepath)
    
    for sheet in xl.sheet_names:
        sheet_u = sheet.upper().strip()
        df = pd.read_excel(filepath, sheet_name=sheet, header=None)
        
        if "NEW GOG NOTES" in sheet_u:
            process_sheet_data(df, "new_gog_notes_and_bonds", map_gog_bond, trade_date)
        elif "OLD GOG NOTES" in sheet_u:
            process_sheet_data(df, "old_gog_notes_and_bonds", map_gog_bond, trade_date)
        elif "TREASURY" in sheet_u:
            process_sheet_data(df, "treasury_bills", map_treasury_bill, trade_date)
        elif "CORPORATE" in sheet_u:
            process_corporate_sheet(df, trade_date)
        elif "SELL" in sheet_u and "BUY" in sheet_u:
            process_sheet_data(df, "sell_buy_back_trades", map_sell_buy_back, trade_date)
        else:
            logger.info(f"Skipping sheet: {sheet}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        process_excel(sys.argv[1])
    else:
        print("Usage: python process_excel.py <filepath>")
