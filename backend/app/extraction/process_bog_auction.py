"""
BoG Auction Results PDF Parser
Extracts primary market auction data from Bank of Ghana PDFs
"""

import pdfplumber
import pandas as pd
import logging
import os
import re
from datetime import datetime
from typing import Optional, List, Dict
from supabase import create_client, Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.warning("Supabase credentials not found. Data will not be uploaded.")

def extract_auction_date_from_text(text: str) -> Optional[str]:
    """Extract auction date from PDF text"""
    # Look for patterns like "6th Feb. 2026" or "6TH FEBRUARY 2026"
    patterns = [
        r'(\d{1,2})[a-z]{2}\s+([A-Za-z]+)\.?\s+(\d{4})',
        r'(\d{1,2})[A-Z]{2}\s+([A-Z]+)\s+(\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            try:
                date_str = f"{day} {month} {year}"
                dt = datetime.strptime(date_str, "%d %B %Y")
                return dt.strftime("%Y-%m-%d")
            except:
                try:
                    dt = datetime.strptime(date_str, "%d %b %Y")
                    return dt.strftime("%Y-%m-%d")
                except:
                    pass
    
    return datetime.now().strftime("%Y-%m-%d")

def clean_amount(amount_str: str) -> Optional[float]:
    """Clean and convert amount string to float"""
    if not amount_str or amount_str == '':
        return None
    
    # Remove currency symbols, commas, and 'Million'
    cleaned = re.sub(r'[GH¢,Million\s]', '', str(amount_str))
    try:
        return float(cleaned)
    except:
        return None

def clean_rate(rate_str: str) -> Optional[float]:
    """Clean and convert rate string to float"""
    if not rate_str or rate_str == '':
        return None
    
    # Extract first number from range like "9.7000-11.0000"
    match = re.search(r'(\d+\.\d+)', str(rate_str))
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None

def parse_bog_auction_pdf(pdf_path: str) -> Dict:
    """Parse BoG auction PDF and extract structured data"""
    logger.info(f"Processing {pdf_path}...")
    
    results = {
        "auction_date": None,
        "instruments": [],
        "summary": {}
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 4:
                    continue
                
                # Row 3 contains the main data (index 3)
                if len(table) > 3:
                    data_row = table[3]
                    
                    # Extract ISINs (column 0)
                    isins_text = data_row[0] if data_row[0] else ""
                    isins = re.findall(r'GHGGOGI\d+', isins_text)
                    
                    # Extract tenors (column 1)
                    tenors_text = data_row[1] if data_row[1] else ""
                    tenors = [t.strip() for t in tenors_text.split('\n') if t.strip()]
                    
                    # Extract amounts tendered (column 2)
                    tendered_text = data_row[2] if data_row[2] else ""
                    tendered_amounts = [clean_amount(a) for a in tendered_text.split('\n') if a.strip()]
                    
                    # Extract amounts accepted (column 4)
                    accepted_text = data_row[4] if data_row[4] else ""
                    accepted_amounts = [clean_amount(a) for a in accepted_text.split('\n') if a.strip()]
                    
                    # Extract discount rates (column 10)
                    discount_text = data_row[10] if len(data_row) > 10 and data_row[10] else ""
                    discount_rates = [clean_rate(r) for r in discount_text.split('\n') if r.strip()]
                    
                    # Extract interest rates (column 11)
                    interest_text = data_row[11] if len(data_row) > 11 and data_row[11] else ""
                    interest_rates = [clean_rate(r) for r in interest_text.split('\n') if r.strip()]
                    
                    # Combine all data
                    for i, tenor in enumerate(tenors):
                        instrument = {
                            "instrument_type": "TBILL",
                            "tenor": tenor.replace(' ', '-'),  # "91 Day Bill" -> "91-Day-Bill"
                            "isin": isins[i] if i < len(isins) else None,
                            "amount_tendered": tendered_amounts[i] if i < len(tendered_amounts) else None,
                            "amount_accepted": accepted_amounts[i] if i < len(accepted_amounts) else None,
                            "discount_rate": discount_rates[i] if i < len(discount_rates) else None,
                            "interest_rate": interest_rates[i] if i < len(interest_rates) else None,
                        }
                        results["instruments"].append(instrument)
                
                # Extract summary (row 7)
                if len(table) > 7:
                    summary_row = table[7]
                    if summary_row and len(summary_row) > 4:
                        results["summary"]["total_tendered"] = clean_amount(summary_row[4])
                    if summary_row and len(summary_row) > 8:
                        results["summary"]["total_accepted"] = clean_amount(summary_row[8])
        
        # Extract auction date
        results["auction_date"] = extract_auction_date_from_text(full_text)
    
    logger.info(f"Auction Date: {results['auction_date']}")
    logger.info(f"Found {len(results['instruments'])} instruments")
    
    return results

def upload_to_supabase(results: Dict):
    """Upload parsed data to Supabase"""
    if not supabase:
        logger.warning("Supabase not configured. Skipping upload.")
        return
    
    auction_date = results["auction_date"]
    
    # Upload individual instruments
    for instrument in results["instruments"]:
        record = {
            "auction_date": auction_date,
            "instrument_type": instrument["instrument_type"],
            "tenor": instrument["tenor"],
            "isin": instrument.get("isin"),
            "amount_tendered": instrument.get("amount_tendered"),
            "amount_accepted": instrument.get("amount_accepted"),
            "discount_rate": instrument.get("discount_rate"),
            "interest_rate": instrument.get("interest_rate"),
            "weighted_average_rate": instrument.get("interest_rate"),  # Use interest rate as weighted avg
            "raw_data": instrument.get("raw_data")
        }
        
        # Calculate bid cover ratio if we have the data
        if record["amount_tendered"] and record["amount_accepted"]:
            # We need target amount - for now use accepted as proxy
            record["bid_cover_ratio"] = round(record["amount_tendered"] / record["amount_accepted"], 2)
        
        try:
            logger.info(f"Upserting {instrument['tenor']} to bog_auction_results...")
            supabase.table("bog_auction_results").upsert(
                record, 
                on_conflict="auction_date, instrument_type, tenor"
            ).execute()
            logger.info(f"Success: {instrument['tenor']}")
        except Exception as e:
            logger.error(f"Failed to upload {instrument['tenor']}: {e}")
    
    # Upload summary
    if results["summary"]:
        summary_record = {
            "auction_date": auction_date,
            "total_amount_tendered": results["summary"].get("total_tendered"),
            "total_amount_accepted": results["summary"].get("total_accepted"),
        }
        
        if summary_record["total_amount_tendered"] and summary_record["total_amount_accepted"]:
            summary_record["overall_bid_cover_ratio"] = round(
                summary_record["total_amount_tendered"] / summary_record["total_amount_accepted"], 2
            )
        
        try:
            logger.info("Upserting auction summary...")
            supabase.table("bog_auction_summary").upsert(
                summary_record,
                on_conflict="auction_date"
            ).execute()
            logger.info("Success: auction summary")
        except Exception as e:
            logger.error(f"Failed to upload summary: {e}")

def process_bog_auction(filepath: str, override_date: str = None):
    """Process BoG auction PDF and extract structured data"""
    results = parse_bog_auction_pdf(filepath)
    
    # Override date if provided
    if override_date:
        results["auction_date"] = override_date
    
    logger.info(f"\n=== PARSED DATA ===")
    logger.info(f"Auction Date: {results['auction_date']}")
    logger.info(f"Instruments: {len(results['instruments'])}")
    for inst in results['instruments']:
        logger.info(f"  {inst['tenor']}: Tendered={inst.get('amount_tendered')}M, Accepted={inst.get('amount_accepted')}M, Rate={inst.get('interest_rate')}%")
    logger.info(f"Summary: {results['summary']}")
    
    # Upload to database
    upload_to_supabase(results)
    
    logger.info("\n=== PROCESSING COMPLETE ===")

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Process BoG auction PDF')
    parser.add_argument('pdf_path', help='Path to BoG auction PDF file')
    parser.add_argument('--date', help='Override auction date (YYYY-MM-DD format)', default=None)
    
    args = parser.parse_args()
    
    process_bog_auction(args.pdf_path, args.date)
