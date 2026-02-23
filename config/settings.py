"""
AetherWatch — Central Configuration
All API endpoints, camera URLs, model settings, and constants live here.
Edit this file to customise AetherWatch for your use case.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY & ETHICS NOTICE
# ─────────────────────────────────────────────────────────────────────────────
# AetherWatch is designed exclusively for use with:
#   • Publicly available APIs under their respective Terms of Service
#   • Open-source or freely licensed data (OpenSky, NASA GIBS)
#   • Public traffic camera feeds operated by government/civic agencies
#
# Do NOT:
#   • Use this tool to surveil private individuals
#   • Attempt to access restricted airspace data without authorisation
#   • Violate the Terms of Service of any integrated API
#   • Deploy in jurisdictions where such monitoring is restricted
#
# Always comply with local privacy laws (GDPR, CCPA, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Credentials (loaded from .env) ──────────────────────────────────────────
OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD: str = os.getenv("OPENSKY_PASSWORD", "")
NASA_EARTHDATA_USERNAME: str = os.getenv("NASA_EARTHDATA_USERNAME", "")
NASA_EARTHDATA_PASSWORD: str = os.getenv("NASA_EARTHDATA_PASSWORD", "")
FR24_API_TOKEN: str = os.getenv("FR24_API_TOKEN", "")

# Alert integrations
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_TO_NUMBER: str = os.getenv("TWILIO_TO_NUMBER", "")

# Developer overrides
FORCE_MOCK_DATA: bool = os.getenv("FORCE_MOCK_DATA", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── OpenSky Network ──────────────────────────────────────────────────────────
OPENSKY_BASE_URL = "https://opensky-network.org/api"
OPENSKY_STATES_URL = f"{OPENSKY_BASE_URL}/states/all"
OPENSKY_CACHE_TTL = 15  # seconds — respect rate limits

# Geographic bounding box defaults (entire world)
DEFAULT_BBOX = {
    "lamin": -90.0,
    "lomin": -180.0,
    "lamax": 90.0,
    "lomax": 180.0,
}

# ── FlightRadar24 (optional upgrade) ─────────────────────────────────────────
FR24_BASE_URL = "https://fr24api.flightradar24.com/api"
FR24_FLIGHTS_URL = f"{FR24_BASE_URL}/live/flight-positions/light"

# ── NASA GIBS ────────────────────────────────────────────────────────────────
NASA_GIBS_WMS_URL = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
NASA_CACHE_TTL = 300  # 5 minutes

NASA_LAYERS: dict[str, str] = {
    "MODIS Terra — True Color": "MODIS_Terra_CorrectedReflectance_TrueColor",
    "MODIS Aqua — True Color": "MODIS_Aqua_CorrectedReflectance_TrueColor",
    "VIIRS SNPP — True Color": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
    "VIIRS SNPP — Day/Night Band": "VIIRS_SNPP_DayNightBand_ENCC",
    "MODIS Terra — Land Surface Temp": "MODIS_Terra_Land_Surface_Temp_Day",
    "MODIS Terra — Fires & Thermal": "MODIS_Terra_Thermal_Anomalies_All",
}

# ── Traffic Cameras ──────────────────────────────────────────────────────────
# Mix of public government / civic JPEG snapshot cameras.
# System gracefully falls back to mock frames if a feed is unavailable.
# All URLs are from public/open government sources.
PUBLIC_CAMERAS: list[dict] = [
    {
        "id": "cam_nyc_01",
        "name": "NYC — Manhattan Bridge",
        "url": "https://511ny.org/cameras/statewide/NYSDOT/camera000001.jpg",
        "location": [40.7074, -73.9903],
        "city": "New York, USA",
        "type": "static_jpeg",
        "refresh_s": 10,
    },
    {
        "id": "cam_chi_01",
        "name": "Chicago — Lake Shore Dr",
        "url": "https://www.chicago.gov/content/dam/city/depts/cdot/traffic_video/camera_1.jpg",
        "location": [41.8827, -87.6233],
        "city": "Chicago, USA",
        "type": "static_jpeg",
        "refresh_s": 15,
    },
    {
        "id": "cam_la_01",
        "name": "Los Angeles — I-405",
        "url": "https://cwwp2.dot.ca.gov/vm/streamhub/CCTV1090.jpg",
        "location": [33.9416, -118.4085],
        "city": "Los Angeles, USA",
        "type": "static_jpeg",
        "refresh_s": 10,
    },
    {
        "id": "cam_ga_01",
        "name": "Atlanta — I-75 North",
        "url": "https://www.511ga.org/imap/images/cameras/GDOT001.jpg",
        "location": [33.7490, -84.3880],
        "city": "Atlanta, USA",
        "type": "static_jpeg",
        "refresh_s": 15,
    },
    {
        "id": "cam_london_01",
        "name": "London — Tower Bridge",
        "url": "https://www.tfl.gov.uk/tfl/livetravelnews/realtime/cctv/14401.jpg",
        "location": [51.5055, -0.0754],
        "city": "London, UK",
        "type": "static_jpeg",
        "refresh_s": 10,
    },
    {
        "id": "cam_pearson_01",
        "name": "Toronto — Pearson Airport Approach",
        "url": "https://511on.ca/api/v2/get/cameras?lang=en&format=json",
        "location": [43.6777, -79.6248],
        "city": "Toronto, Canada",
        "type": "static_jpeg",
        "refresh_s": 20,
    },
    {
        "id": "cam_beach_01",
        "name": "Miami — South Beach",
        "url": "https://www.earthcam.com/usa/florida/miami/southbeach/?cam=southbeach",
        "location": [25.7617, -80.1918],
        "city": "Miami, USA",
        "type": "static_jpeg",
        "refresh_s": 30,
    },
    {
        "id": "cam_port_01",
        "name": "Los Angeles — Port of LA",
        "url": "https://www.portoflosangeles.org/img/cams/cam1.jpg",
        "location": [33.7397, -118.2640],
        "city": "San Pedro, USA",
        "type": "static_jpeg",
        "refresh_s": 20,
    },
    {
        "id": "cam_sea_01",
        "name": "Seattle — I-5 Downtown",
        "url": "https://images.wsdot.wa.gov/nw/005vc13581.jpg",
        "location": [47.6062, -122.3321],
        "city": "Seattle, USA",
        "type": "static_jpeg",
        "refresh_s": 10,
    },
    {
        "id": "cam_vegas_01",
        "name": "Las Vegas — The Strip",
        "url": "https://nvroads.com/cctvimage/NV_CCTV_1001.jpg",
        "location": [36.1699, -115.1398],
        "city": "Las Vegas, USA",
        "type": "static_jpeg",
        "refresh_s": 15,
    },
]

# ── YOLO ─────────────────────────────────────────────────────────────────────
YOLO_MODEL = "yolov8n.pt"          # Nano model — fastest, auto-downloaded
YOLO_CONFIDENCE = 0.35             # Minimum detection confidence
YOLO_INPUT_SIZE = 640              # Inference image size (px)
YOLO_TARGET_CLASSES = [            # COCO class IDs to highlight
    0,   # person
    1,   # bicycle
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
    8,   # boat
    9,   # traffic light
    11,  # stop sign
]

# ── Anomaly Detection Thresholds ─────────────────────────────────────────────
ANOMALY_VEHICLE_CLUSTER_MIN = 6    # N+ vehicles in frame → alert
ANOMALY_PERSON_CLUSTER_MIN = 10    # N+ people in frame → crowd alert
ANOMALY_LOW_ALTITUDE_FT = 3000     # Aircraft below this → alert
ANOMALY_HIGH_SPEED_KTS = 600       # Aircraft above this → alert

# ── UI Defaults ──────────────────────────────────────────────────────────────
DEFAULT_MAP_CENTER = [30.0, 0.0]
DEFAULT_MAP_ZOOM = 3
MAX_ALERT_LOG_SIZE = 200           # Keep last N alerts in memory
DEFAULT_REFRESH_S = 20             # Auto-refresh interval in seconds
CAMERA_GRID_MAX = 4                # Max simultaneous camera panels
# ── Missing settings (patch) ─────────────────────────────────────────────────
APP_VERSION = "1.0.0"
DEFAULT_MAP_TILE = "CartoDB dark_matter"
DEFAULT_REFRESH_RATE = 30
MIN_REFRESH_RATE = 10
MAX_REFRESH_RATE = 120
CACHE_TTL_AVIATION = 30
CACHE_TTL_SATELLITE = 300
NASA_GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")

MAP_TILES = {
    "CartoDB dark_matter": "CartoDB dark_matter",
    "CartoDB positron": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap",
}
SATELLITE_LAYERS = {
    "True Color (MODIS Terra)": "MODIS_Terra_CorrectedReflectance_TrueColor",
    "Night Lights (VIIRS)": "VIIRS_Black_Marble",
    "Sea Surface Temperature": "MUR-JPL-L4-GLOB-v4.1",
    "Snow & Ice Cover": "MODIS_Terra_Snow_Cover",
    "Aerosol (Dust/Smoke)": "MODIS_Terra_Aerosol",
    "Vegetation (NDVI)": "MODIS_Terra_NDVI_8Day",
    "Land Surface Temp": "MODIS_Terra_Land_Surface_Temp_Day",
    "Aqua True Color": "MODIS_Aqua_CorrectedReflectance_TrueColor",
}
FR24_TOKEN: str = os.getenv("FR24_API_TOKEN", "")
YOLO_MODEL_NAME = "yolov8n.pt"
