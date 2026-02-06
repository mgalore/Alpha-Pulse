# Alpha-Pulse

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E.svg)](https://supabase.com/)

**A Decision Support System for the Ghana Fixed Income Market (GFIM)**

Alpha-Pulse transforms raw GFIM trading data into actionable investment intelligence by calculating yields, spreads, and liquidity metrics that help traders identify relative value opportunities.

---

## 🎯 Key Features

### Data Ingestion (Bronze Layer)
- **Automated Excel parsing** from GFIM daily trading reports
- **5 asset classes**: GOG Bonds (New & Old), Treasury Bills, Corporate Bonds, Sell-Buy-Back
- **Forward-fill logic** for merged Excel cells (Issuer handling)

### Quantitative Analytics (Silver Layer)
- **Yield to Maturity (YTM)** for bonds and T-Bills
- **Real Yield** adjusted for Ghana inflation (currently 23.2%)
- **Bond Equivalent Yield (BEY)** for T-Bill comparison
- **Modified Duration** for interest rate risk

### Relative Value Analysis (Alpha Logic)
- **Sovereign Yield Curve** with 8 maturity buckets (91D → 20Y)
- **Corporate Spreads** vs. Government benchmark
- **Liquidity Alerts** for volume spikes (>300% of 30-day average)
- **Market Alerts** database for SPREAD_WIDENING and VOLUME_SPIKE events

---

## 📊 Database Schema

### Bronze Layer (Raw Data)
| Table | Description |
|-------|-------------|
| `new_gog_notes_and_bonds` | New GOG securities |
| `old_gog_notes_and_bonds` | Old GOG securities |
| `treasury_bills` | T-Bills (91D, 182D, 364D) |
| `corporate` | Corporate bonds |
| `sell_buy_back_trades` | Repo trades |
| `issuer_securities` | Issuer-to-ISIN mapping |

### Silver Layer (Calculated Metrics)
| Table | Description |
|-------|-------------|
| `security_metrics` | Per-ISIN daily analytics (YTM, Duration, Spread) |
| `yield_curve_points` | Sovereign curve coordinates |
| `daily_market_summary` | Market-wide aggregates |
| `market_alerts` | Flash alerts (volume spikes, spread widening) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Supabase account (free tier works)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/alpha-pulse.git
cd alpha-pulse

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials
```

### Environment Variables

Create a `.env` file:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

---

## 🔧 Usage

### 1. Ingest Trading Data (Worker A)
```bash
python backend/app/extraction/process_excel.py downloads/TRADING-REPORT-FOR-GFIM-30012026.xlsx
```

**Output:**
```
INFO: Processing downloads/TRADING-REPORT-FOR-GFIM-30012026.xlsx...
INFO: Upserting 29 records to new_gog_notes_and_bonds...
INFO: Upserting 21 records to old_gog_notes_and_bonds...
INFO: Upserting 24 records to corporate...
INFO: Upserting 90 records to treasury_bills...
```

### 2. Run Quant Engine (Worker B)
```bash
python backend/app/quant/worker_b.py 2026-01-30
```

**Output:**
```
INFO: === QUANT ENGINE: Processing 2026-01-30 ===
INFO: Total securities processed: 164
INFO: Yield curve points: 8
INFO: Calculating corporate spreads...
INFO: Generated 4 market alerts
INFO: === QUANT ENGINE COMPLETE ===
```

---

## 📈 Sample Output

### Yield Curve (2026-01-30)
| Tenor | Yield |
|-------|-------|
| 91D   | 12.83% |
| 182D  | 11.24% |
| 1Y    | 14.01% |
| 2Y    | 18.95% |
| 10Y   | 18.16% |
| 20Y   | 16.61% |

**Curve Shape:** NORMAL (slope: +3.77%)

### Top Corporate Spreads
| Issuer | YTM | Spread vs GOG |
|--------|-----|---------------|
| QUANTUM | 71.69% | +55.98% |
| LETSHEGO | 47.66% | +33.65% |
| BAYPORT | 21.90% | +10.66% |

> ⚠️ High spreads may indicate **illiquidity risk** rather than true alpha.

---

## 📁 Project Structure

```
alpha-pulse/
├── backend/
│   ├── app/
│   │   ├── extraction/
│   │   │   └── process_excel.py    # Excel → Supabase ingestion
│   │   ├── quant/
│   │   │   └── worker_b.py         # Quantitative analytics engine
│   │   ├── api/                    # FastAPI endpoints (coming soon)
│   │   ├── models/                 # SQLAlchemy models (coming soon)
│   │   └── main.py                 # FastAPI app entry
│   └── requirements.txt
├── downloads/                      # GFIM Excel reports (git-ignored)
├── .env                            # Environment config (git-ignored)
└── README.md
```

---

## 🛣️ Roadmap

- [x] Bronze Layer (Data Ingestion)
- [x] Silver Layer (Quant Analytics)
- [x] Alpha Logic (Spreads & Alerts)
- [ ] REST API (FastAPI)
- [ ] Frontend Dashboard (React/Next.js)
- [ ] Worker C (AI Sentiment Analysis)
- [ ] Automated Daily Scraper

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📧 Contact

**Alpha-Pulse Team**
- GitHub: [@yourusername](https://github.com/yourusername)
