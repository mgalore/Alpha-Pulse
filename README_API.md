# Alpha-Pulse API & Dashboard

## Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Start the API Server
```bash
python backend/app/main.py
```
API will run on: http://localhost:8000

### 3. Start the Streamlit Dashboard (in a new terminal)
```bash
streamlit run streamlit_app.py
```
Dashboard will open in your browser automatically.

---

## API Endpoints

### Market Data
- `GET /api/yield-curve?date=2026-01-30` - Yield curve points
- `GET /api/market-summary?date=2026-01-30` - Daily market summary
- `GET /api/security-metrics?date=2026-01-30&security_type=CORPORATE` - Security metrics
- `GET /api/treasury-bills?date=2026-01-30` - T-Bill data

### Analytics
- `GET /api/corporate-spreads?date=2026-01-30` - Corporate spreads vs GOG
- `GET /api/top-securities?metric=ytm&limit=10` - Top securities by metric
- `GET /api/market-alerts?days=7` - Recent market alerts

### Health Check
- `GET /health` - API status

---

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Dashboard Features

1. **Yield Curve Visualization** - Interactive Ghana sovereign curve
2. **Corporate Spreads** - Bar chart of spreads vs government bonds
3. **Market Alerts** - Real-time volume spikes and spread widening
4. **Top Securities** - Sortable rankings by YTM, volume, spreads

---

## Example Usage

### Python
```python
import requests

# Get yield curve
response = requests.get("http://localhost:8000/api/yield-curve")
data = response.json()
print(data)

# Get corporate spreads
response = requests.get("http://localhost:8000/api/corporate-spreads")
spreads = response.json()
```

### cURL
```bash
# Market summary
curl http://localhost:8000/api/market-summary

# Top securities by YTM
curl "http://localhost:8000/api/top-securities?metric=ytm&limit=5"
```
