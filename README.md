# 🛰️ AetherWatch
### Real-Time Multi-Source Surveillance Dashboard

[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![OpenSky](https://img.shields.io/badge/Aviation-OpenSky%20Network-orange)](https://opensky-network.org)
[![NASA GIBS](https://img.shields.io/badge/Satellite-NASA%20GIBS-0B3D91?logo=nasa)](https://earthdata.nasa.gov)

A production-grade, real-time surveillance dashboard combining live aviation tracking,
public traffic camera feeds, NASA satellite imagery, and YOLO object detection — all
deployable for **free** on Streamlit Community Cloud.

---

## ✨ Features

| Feature | Details |
|---|---|
| ✈️ **Aviation Tracking** | Live global aircraft via OpenSky Network (free) or FR24 (paid) |
| 📷 **Traffic Cameras** | 10 public city camera feeds (NYC, LA, London, Tokyo, etc.) + custom URLs |
| 🛰️ **Satellite Imagery** | 8 NASA GIBS layers — true-color, night lights, temperature, more |
| 🤖 **YOLO Detection** | YOLOv8n object detection on camera/satellite frames, auto GPU/MPS/CPU |
| 🚨 **Anomaly Alerts** | Emergency squawk detection (7700/7600/7500), crowd/traffic clustering |
| 🗺️ **Interactive Map** | Folium/Leaflet with aircraft, cameras, satellite WMS overlay |
| 📊 **Data Export** | Download aircraft and alert data as CSV |
| 🔄 **Auto-Refresh** | Configurable 10–120 second refresh cycle |
| 🎭 **Mock Fallback** | Realistic simulated data whenever APIs are unavailable |

---

## 🚀 Quick Start

### Option A — Local (recommended for development)

```bash
# 1. Clone
git clone https://github.com/your-org/aetherwatch.git
cd aetherwatch

# 2. Create a virtual environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your credentials (all optional — works without any)

# 5. Run
streamlit run app.py               # Modular version
# or
streamlit run app_single.py        # Single-file version
```

Open **http://localhost:8501** in your browser.

---

### Option B — Free Cloud Deployment (Streamlit Community Cloud)

1. **Fork** this repo to your GitHub account
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub
3. Click **"New app"** → select your forked repo → set **Main file**: `app.py`
4. Add secrets (optional) in the **Secrets** tab:
   ```toml
   OPENSKY_USERNAME = "your_username"
   OPENSKY_PASSWORD = "your_password"
   ```
5. Click **Deploy** — live in ~2 minutes ✅

> **Note**: Streamlit Community Cloud is CPU-only. YOLO will use CPU inference (~5–10 FPS).
> For GPU acceleration, deploy to a VM with NVIDIA GPU or use Google Colab.

---

## 🔑 API Keys — How to Get Them (All Free)

### OpenSky Network (Aviation Data) — FREE
1. Go to **https://opensky-network.org/index.php?option=com_users&view=registration**
2. Create a free account (email + password, no credit card)
3. Add to `.env`:
   ```
   OPENSKY_USERNAME=your_username
   OPENSKY_PASSWORD=your_password
   ```
**Without credentials**: Anonymous access still works, but with lower rate limits
(10 requests per 10 seconds, 400 per day). AetherWatch caches results to stay within limits.

### NASA GIBS (Satellite Imagery) — NO KEY NEEDED
NASA's Global Imagery Browse Services WMS endpoint is fully open. No registration required.
Optional: Register at **https://urs.earthdata.nasa.gov/** for NASA Earthdata token
(needed for authenticated endpoints, not required for GIBS).

### FlightRadar24 (Optional Upgrade)
Requires a paid subscription at **https://fr24api.flightradar24.com**.
AetherWatch uses OpenSky by default — FR24 is an optional paid upgrade for higher
refresh rates and richer aircraft metadata.

---

## 📁 Project Structure

```
aetherwatch/
├── app.py                    # 🚀 Main entry point (modular version)
├── app_single.py             # 📄 Self-contained single-file version
├── requirements.txt          # 📦 All dependencies with pinned versions
├── .env.example              # 🔑 Environment variable template
├── .streamlit/
│   └── config.toml           # 🎨 Dark theme + server settings
│
├── config/
│   └── settings.py           # ⚙️  All constants, endpoints, camera registry
│
├── data_sources/
│   ├── aviation.py           # ✈️  OpenSky + FR24 + mock aircraft data
│   ├── cameras.py            # 📷  Camera frame fetcher + mock frame generator
│   └── satellite.py          # 🛰️  NASA GIBS WMS satellite imagery
│
├── vision/
│   └── detector.py           # 🤖  YOLOv8 detector (auto GPU/MPS/CPU)
│
├── ui/
│   ├── map_view.py           # 🗺️  Folium map builder
│   ├── camera_grid.py        # 📷  Camera grid renderer
│   ├── satellite_view.py     # 🛰️  Satellite imagery panel
│   └── alerts_panel.py       # 🚨  Alerts & log panel
│
└── utils/
    ├── logger.py             # 📋  Loguru-based structured logging
    ├── cache.py              # ⚡  TTL caching decorator
    └── alerts.py             # 🔔  Multi-channel alert dispatch
```

---

## ⚙️ Configuration

All settings live in `config/settings.py`. Key options:

| Setting | Default | Description |
|---|---|---|
| `DEFAULT_REFRESH_RATE` | 30s | Auto-refresh interval |
| `MAX_AIRCRAFT_DISPLAY` | 500 | Max aircraft on map |
| `YOLO_MODEL_NAME` | `yolov8n.pt` | Swap to `yolov8s.pt` for accuracy |
| `YOLO_CONFIDENCE` | 0.35 | Detection confidence threshold |
| `ANOMALY_CROWD_THRESHOLD` | 8 | Persons in frame to trigger crowd alert |
| `CACHE_TTL_AVIATION` | 30s | Aviation data cache lifetime |

### Environment Variables (`.env`)
```bash
OPENSKY_USERNAME=          # OpenSky account (optional)
OPENSKY_PASSWORD=          # OpenSky password (optional)
FR24_TOKEN=                # FR24 API token (optional, paid)
FORCE_MOCK_DATA=false      # true = always use simulated data
LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
SMTP_USER=                 # For email alerts (optional)
SMTP_PASSWORD=             # For email alerts (optional)
ALERT_EMAIL_TO=            # Recipient for email alerts (optional)
```

---

## 🎮 Using the Dashboard

### World Map Tab
- **Aircraft markers**: Rotated airplane icons (blue=live, yellow=simulated, grey=ground)
- **Camera pins**: Green (online) / Red (offline) / White (unchecked)
- **Satellite overlay**: Enable in sidebar to layer NASA imagery on the map
- **Fullscreen**: Click the fullscreen button (top-right of map)
- **Clustering**: Toggle aircraft clustering for performance on dense traffic areas

### Camera Grid Tab
- Select up to **4 cameras** from the sidebar
- Cameras auto-refresh every 5 seconds
- **Add custom cameras**: Expand "Add Custom Camera" to paste your own MJPEG/JPEG URL
- **YOLO overlay**: Enable detection in sidebar to see bounding boxes live

### Satellite Tab
- Choose from **8 imagery layers** (true-color, night lights, temperature, NDVI, etc.)
- Select **date** (1–2 day latency for most products is normal)
- Pick a **region** or enter a custom bounding box
- YOLO detection can be applied to satellite frames too

### Alerts & Log Tab
- **Filter** by severity (Critical, Anomaly, Warning, Info) and source
- **Emergency squawks** (7700/7600/7500) trigger Critical alerts automatically
- **Export** full alert log as CSV
- **Email alerts**: Configure SMTP in `.env` to receive email notifications

---

## 🤖 YOLO Performance Guide

| Hardware | Model | Expected FPS |
|---|---|---|
| NVIDIA GPU (any CUDA) | yolov8n | 30–60 FPS |
| Apple M1/M2/M3 (MPS) | yolov8n | 20–40 FPS |
| CPU (4-core laptop) | yolov8n | 5–15 FPS |
| Streamlit Cloud (CPU) | yolov8n | 3–8 FPS |

To improve accuracy at cost of speed, change `YOLO_MODEL_NAME = "yolov8s.pt"` in `config/settings.py`.
The model auto-downloads on first run (~6MB for nano).

---

## 📷 Public Camera Sources

AetherWatch includes 10 curated public camera URLs. These are from government/institutional sources:

| Camera | Source |
|---|---|
| NYC DOT cameras | webcams.nyc.gov (NYC Department of Transportation) |
| Caltrans (California) | cwwp2.dot.ca.gov |
| Nevada DOT | nvroads.com |
| SF Bay Bridge | 511.org |
| Amsterdam, Tokyo, London, Sydney | Public institutional webcams |

> ⚠️ **Camera URLs may change over time.** When a camera goes offline, AetherWatch automatically
> shows a realistic simulated feed so the dashboard remains usable. You'll see "⚠ SIMULATED" in
> the camera frame header. Use the "Add Custom Camera" form to add fresh URLs.

---

## 🛰️ NASA Satellite Layers

| Layer | Update Frequency | Best For |
|---|---|---|
| True Color (MODIS Terra/Aqua) | Daily | General overview, clouds, fires |
| VIIRS Night Lights | Daily | City lights, gas flares, fishing |
| Sea Surface Temperature | Daily | Ocean currents, fishing, climate |
| Snow Ice Cover | Daily | Arctic/Antarctic monitoring |
| Aerosol (Dust/Smoke) | Daily | Wildfire smoke, dust storms |
| Vegetation (NDVI) | 8-day composite | Agriculture, drought, deforestation |
| Land Surface Temperature | Daily | Urban heat islands, drought |

---

## ⚠️ Known Limitations

- **OpenSky anonymous rate limit**: 400 requests/day. With a free account: 4,000/day.
  AetherWatch caches results aggressively (30s TTL) to stay within limits.
- **FR24 API requires paid subscription**: Use OpenSky (free) as primary source.
- **GIBS latency**: Most satellite products have 1–2 day latency. Real-time imagery is
  not available through GIBS.
- **Camera URLs are volatile**: Public IP cameras go offline, change URLs, or restrict access.
  The mock fallback ensures the dashboard always shows something useful.
- **YOLO on CPU is slow**: On Streamlit Community Cloud (~1-core CPU), detection adds
  2–5 seconds per frame. Consider disabling for faster camera refresh.
- **RTSP streams**: Not supported in this version (requires OpenCV with RTSP backend and
  is not compatible with Streamlit Cloud). Use MJPEG or static JPEG feeds instead.

---

## ⚖️ Legal Disclaimer

**AetherWatch is designed for educational and research purposes only.**

- Aircraft position data is publicly broadcast via ADS-B transponders and is freely available.
- Traffic camera feeds are from official government/institutional public sources only.
- NASA satellite imagery is public domain under NASA's open data policy.
- **Do not use AetherWatch for surveillance of private individuals.**
- Comply with GDPR, CCPA, and all applicable local privacy laws.
- Respect the Terms of Service of each data provider (OpenSky, NASA, camera operators).
- The authors assume no liability for misuse of this software.

OpenSky Network Terms: https://opensky-network.org/about/terms-of-use
NASA Data Use Policy: https://www.earthdata.nasa.gov/engage/open-data-services-and-software

---

## 🛠️ Development

```bash
# Run with debug logging
LOG_LEVEL=DEBUG streamlit run app.py

# Force mock data (no API calls)
FORCE_MOCK_DATA=true streamlit run app.py

# Run single-file version
streamlit run app_single.py

# Check logs
tail -f aetherwatch.log
```

---

## 📄 License

MIT License — see LICENSE file for details.

---

*AetherWatch v1.0.0 — Built with Streamlit, OpenSky Network, NASA GIBS, and Ultralytics YOLOv8*
