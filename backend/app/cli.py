#!/usr/bin/env python3
"""
Alpha-Pulse CLI Tool
Unified command-line interface for data extraction and processing
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_gfim_excel(filepath: str, date: str = None):
    """Process GFIM Excel trading report"""
    from extraction.process_excel import process_excel, parse_date_from_filename
    
    if date:
        # Override date parsing
        import extraction.process_excel as excel_module
        excel_module.parse_date_from_filename = lambda x: date
    
    process_excel(filepath)

def process_bog_auction(filepath: str, date: str = None):
    """Process BoG auction PDF"""
    from extraction.process_bog_auction import process_bog_auction as process_func
    process_func(filepath, date)

def run_quant_engine(date: str = None, start_date: str = None, end_date: str = None):
    """Run quantitative analytics engine"""
    from quant.worker_b import run_quant_engine as run_engine
    
    if start_date and end_date:
        # Batch processing
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing date: {date_str}")
            logger.info(f"{'='*60}")
            try:
                run_engine(date_str)
            except Exception as e:
                logger.error(f"Failed to process {date_str}: {e}")
            current += timedelta(days=1)
    else:
        date_arg = date if date else datetime.now().strftime("%Y-%m-%d")
        run_engine(date_arg)

def main():
    parser = argparse.ArgumentParser(
        description='Alpha-Pulse Data Extraction & Processing CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process GFIM Excel report
  python cli.py gfim downloads/TRADING-REPORT-30012026.xlsx
  
  # Process GFIM with specific date
  python cli.py gfim downloads/report.xlsx --date 2026-01-30
  
  # Process BoG auction PDF
  python cli.py auction downloads/bog_auction_1993.pdf
  
  # Run quant engine for specific date
  python cli.py quant --date 2026-01-30
  
  # Run quant engine for date range
  python cli.py quant --start-date 2026-01-01 --end-date 2026-01-31
  
  # Full pipeline: extract GFIM data and run analytics
  python cli.py gfim downloads/report.xlsx --date 2026-01-30
  python cli.py quant --date 2026-01-30
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # GFIM Excel processing
    gfim_parser = subparsers.add_parser('gfim', help='Process GFIM Excel trading report')
    gfim_parser.add_argument('filepath', help='Path to Excel file')
    gfim_parser.add_argument('--date', help='Override trade date (YYYY-MM-DD)', default=None)
    
    # BoG Auction processing
    auction_parser = subparsers.add_parser('auction', help='Process BoG auction PDF')
    auction_parser.add_argument('filepath', help='Path to PDF file')
    auction_parser.add_argument('--date', help='Override auction date (YYYY-MM-DD)', default=None)
    
    # Quant engine
    quant_parser = subparsers.add_parser('quant', help='Run quantitative analytics engine')
    quant_parser.add_argument('--date', help='Date to process (YYYY-MM-DD)', default=None)
    quant_parser.add_argument('--start-date', help='Start date for batch (YYYY-MM-DD)', default=None)
    quant_parser.add_argument('--end-date', help='End date for batch (YYYY-MM-DD)', default=None)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'gfim':
            logger.info(f"Processing GFIM Excel: {args.filepath}")
            process_gfim_excel(args.filepath, args.date)
            logger.info("✓ GFIM processing complete")
            
        elif args.command == 'auction':
            logger.info(f"Processing BoG Auction PDF: {args.filepath}")
            process_bog_auction(args.filepath, args.date)
            logger.info("✓ Auction processing complete")
            
        elif args.command == 'quant':
            logger.info("Running quantitative analytics engine")
            run_quant_engine(args.date, args.start_date, args.end_date)
            logger.info("✓ Quant engine complete")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
