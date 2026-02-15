# Alpha-Pulse CLI Guide

Command-line interface for extracting and processing Ghana Fixed Income Market data.

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Navigate to app directory
cd backend/app
```

## Commands

### 1. Process GFIM Excel Reports

Extract secondary market trading data from Ghana Stock Exchange Excel reports.

```bash
# Basic usage
python cli.py gfim <excel_file>

# With specific date
python cli.py gfim downloads/TRADING-REPORT-30012026.xlsx --date 2026-01-30

# Example
python cli.py gfim ../../downloads/TRADING-REPORT-FOR-GFIM-30012026.xlsx
```

**What it does:**
- Extracts data from 5 asset classes (GOG Bonds, T-Bills, Corporate Bonds, etc.)
- Uploads to Bronze Layer tables in Supabase
- Handles merged cells and forward-fills issuer data

### 2. Process BoG Auction PDFs

Extract primary market auction data from Bank of Ghana PDFs.

```bash
# Basic usage
python cli.py auction <pdf_file>

# With specific date
python cli.py auction downloads/bog_auction_1993.pdf --date 2026-02-06

# Example
python cli.py auction ../../downloads/bog_auction_1993.pdf
```

**What it does:**
- Extracts T-Bill auction results (91D, 182D, 364D)
- Calculates bid-cover ratios
- Uploads to `bog_auction_results` and `bog_auction_summary` tables

### 3. Run Quantitative Analytics

Calculate yields, spreads, and generate market alerts.

```bash
# Process single date
python cli.py quant --date 2026-01-30

# Process date range (batch)
python cli.py quant --start-date 2026-01-01 --end-date 2026-01-31

# Process today's data
python cli.py quant
```

**What it does:**
- Calculates YTM, real yield, modified duration
- Builds yield curve
- Calculates corporate spreads vs government
- Detects volume spikes and spread widening
- Generates market alerts

## Complete Workflow

### Daily Data Pipeline

```bash
# 1. Extract GFIM trading data
python cli.py gfim downloads/TRADING-REPORT-30012026.xlsx --date 2026-01-30

# 2. Extract BoG auction data (if available)
python cli.py auction downloads/bog_auction_1993.pdf --date 2026-02-06

# 3. Run analytics
python cli.py quant --date 2026-01-30
```

### Backfill Historical Data

```bash
# Process multiple dates
for date in 2026-01-{01..31}; do
    python cli.py quant --date $date
done

# Or use batch processing
python cli.py quant --start-date 2026-01-01 --end-date 2026-01-31
```

## Direct Script Usage

You can also run scripts directly:

### GFIM Excel Processing
```bash
python extraction/process_excel.py <filepath> --date 2026-01-30
```

### BoG Auction Processing
```bash
python extraction/process_bog_auction.py <pdf_path> --date 2026-02-06
```

### Quant Engine
```bash
python quant/worker_b.py --date 2026-01-30
python quant/worker_b.py --start-date 2026-01-01 --end-date 2026-01-31
```

## Data Flow

```
┌─────────────────┐
│  GFIM Excel     │──┐
│  (Secondary)    │  │
└─────────────────┘  │
                     ├──> Bronze Layer ──> Quant Engine ──> Silver Layer
┌─────────────────┐  │                                         │
│  BoG Auction    │──┘                                         │
│  (Primary)      │                                            │
└─────────────────┘                                            ▼
                                                        ┌──────────────┐
                                                        │  Dashboard   │
                                                        │  & API       │
                                                        └──────────────┘
```

## Tips

1. **Date Format**: Always use `YYYY-MM-DD` format
2. **File Paths**: Use relative or absolute paths
3. **Batch Processing**: Use date ranges for historical data
4. **Error Handling**: Check logs if processing fails
5. **Database**: Ensure Supabase credentials are in `.env`

## Troubleshooting

### "Supabase credentials not found"
```bash
# Check .env file exists
cat ../../.env

# Should contain:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-key
```

### "No data for this date"
```bash
# Verify data was extracted first
python cli.py gfim <excel_file> --date 2026-01-30

# Then run analytics
python cli.py quant --date 2026-01-30
```

### "Module not found"
```bash
# Ensure you're in the app directory
cd backend/app

# And virtual environment is activated
source ../../.venv/bin/activate
```

## Examples

### Example 1: Process New Trading Report
```bash
# Download report from GSE
# Save to downloads/TRADING-REPORT-06022026.xlsx

# Extract data
python cli.py gfim ../../downloads/TRADING-REPORT-06022026.xlsx --date 2026-02-06

# Run analytics
python cli.py quant --date 2026-02-06

# View in dashboard at http://localhost:8501
```

### Example 2: Backfill Week of Data
```bash
# Process Jan 27-31, 2026
python cli.py quant --start-date 2026-01-27 --end-date 2026-01-31
```

### Example 3: Full Pipeline
```bash
#!/bin/bash
# daily_pipeline.sh

DATE=$(date +%Y-%m-%d)

echo "Processing $DATE..."

# Extract GFIM data
python cli.py gfim downloads/report_$DATE.xlsx --date $DATE

# Extract auction data (if available)
if [ -f "downloads/auction_$DATE.pdf" ]; then
    python cli.py auction downloads/auction_$DATE.pdf --date $DATE
fi

# Run analytics
python cli.py quant --date $DATE

echo "Pipeline complete!"
```

## Next Steps

- Set up automated scraping from GSE website
- Schedule daily pipeline with cron
- Add email alerts for market events
- Build automated reporting
