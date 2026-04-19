# ⚡ GridWatch — Electricity Theft Detection System

A hackathon-ready real-time dashboard for detecting electricity theft in distribution networks.

---

## 🚀 Quick Start

```bash
# 1. Install the only dependency
pip install flask

# 2. Run
python app.py

# 3. Open dashboards
#    Smart Meters  → http://localhost:5000/meters
#    Transformers  → http://localhost:5000/transformers
#    Live Map      → http://localhost:5000/map
```

---

## 📊 Dashboards

### `/meters` — Smart Meters
- Live table of 18+ simulated households across 4 transformers
- Each row shows current kWh draw + sparkline trend (last 24h)
- Colour-coded load bars (green → red)
- Per-transformer aggregate totals + loss % badge
- **Inject Anomaly** button per transformer

### `/transformers` — Transformer Monitoring
- **Plotly gauge** showing transformer load % vs capacity
- Live metric cards: TF reading, household sum, diff %, household count
- **Grouped bar chart** comparing transformer draw vs household sum across all feeders
- Anomaly banners flash red when theft is simulated
- Inject Anomaly button per transformer

### `/map` — Live Tracking Map
- **Leaflet.js** dark-themed map centred on Delhi region
- Transformer nodes with colour-coded markers:
  - 🟢 Green  = normal loss < 5%
  - 🟡 Yellow = warning 5–15%
  - 🔴 Red    = critical / theft > 15% (pulsing, larger icon)
- Click any marker → popup with all readings + Inject Anomaly button
- Side panel lists all transformers with live diff% bars
- **Inject All Anomalies** button for instant demo impact

---

## ⚙️ Architecture

```
app.py                  Flask backend + SSE simulation engine
templates/
  base.html             Shared nav, CSS vars, SSE client JS
  meters.html           Chart.js sparklines + table
  transformers.html     Plotly gauges + Chart.js bar chart
  map.html              Leaflet.js map + side panel
  index.html            Landing page
```

### Real-time Transport
Uses **Server-Sent Events** (SSE) via `/api/stream` — no extra packages needed.
The backend pushes a JSON payload every 3 seconds to all connected clients.

### Simulation Logic
- Each household has a base load (1.5–8 kWh) with:
  - Diurnal sine-wave pattern (peak evening, trough night)
  - Gaussian noise ±0.3 kWh
- Normal line losses: 1–4% above household sum
- **Theft injection**: transformer reads 20–40% above household sum
- Anomaly thresholds: `<5%` normal · `5–15%` warning · `>15%` critical

### API Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /api/stream` | SSE stream (live data every 3s) |
| `GET /api/initial_data` | Snapshot of latest payload |
| `POST /api/inject_anomaly/<tf_id>` | Toggle theft simulation |
| `GET /api/anomaly_states` | Current anomaly flags |

---

## 🎯 Demo Flow (Hackathon Tip)

1. Open `/map` on the main screen
2. Point to the green nodes — "normal operation"
3. Click **Inject All Anomalies** → watch nodes turn red
4. Open `/transformers` in another tab — see gauges spike
5. Open `/meters` — show the household vs transformer gap
6. Reset one anomaly → node returns to green in ~3 seconds

---

## Requirements

- Python 3.8+
- `flask` (only external dependency)
- Modern browser (Chrome/Firefox/Safari)
