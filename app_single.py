"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               AetherWatch v1.0.0 — SINGLE FILE VERSION                      ║
║        Everything in one file for quick deployment / experimentation         ║
║  Run: streamlit run app_single.py                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 0 — IMPORTS & PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════════
import io, os, time, math, random, datetime, threading, smtplib
from typing import Optional, Any
from email.mime.text import MIMEText

import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import streamlit as st
import folium
import folium.plugins
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Page config must be first ─────────────────────────────────────────────────
st.set_page_config(
    page_title="AetherWatch", page_icon="🛰️", layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════
OPENSKY_URL       = "https://opensky-network.org/api/states/all"
NASA_GIBS_WMS     = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
FORCE_MOCK        = os.getenv("FORCE_MOCK_DATA", "false").lower() == "true"
DEFAULT_REFRESH   = 30
YOLO_MODEL        = "yolov8n.pt"
YOLO_CONF         = 0.35
MAX_AIRCRAFT      = 400
API_TIMEOUT       = 10

SATELLITE_LAYERS = {
    "True Color (MODIS Terra)":  "MODIS_Terra_CorrectedReflectance_TrueColor",
    "True Color (MODIS Aqua)":   "MODIS_Aqua_CorrectedReflectance_TrueColor",
    "VIIRS Night Lights":        "VIIRS_SNPP_DayNightBand_ENCC",
    "Sea Surface Temperature":   "GHRSST_L4_MUR_Sea_Surface_Temperature",
    "Snow Ice Cover":            "MODIS_Terra_Snow_Cover_Daily",
    "Aerosol (Dust/Smoke)":      "MODIS_Terra_Aerosol",
    "Vegetation (NDVI)":         "MODIS_Terra_NDVI_8Day",
    "Land Surface Temp":         "MODIS_Terra_Land_Surface_Temp_Day",
}

PUBLIC_CAMERAS = [
    {"id":"c1","name":"NYC — Broadway & 42nd","url":"https://webcams.nyc.gov/cameras/1.jpg","type":"static","lat":40.756,"lon":-73.986,"city":"New York, USA","description":"Times Square area"},
    {"id":"c2","name":"NYC — 34th & 7th Ave","url":"https://webcams.nyc.gov/cameras/2.jpg","type":"static","lat":40.748,"lon":-73.997,"city":"New York, USA","description":"Penn Station area"},
    {"id":"c3","name":"LA — I-405 Freeway","url":"https://cwwp2.dot.ca.gov/data/d7/cctv/image/la40405rdbr/la40405rdbr.jpg","type":"static","lat":34.052,"lon":-118.444,"city":"Los Angeles, USA","description":"Caltrans traffic camera"},
    {"id":"c4","name":"San Francisco — Bay Bridge","url":"https://511.org/sites/default/files/cameras/BAYTOLL_17.jpg","type":"static","lat":37.798,"lon":-122.378,"city":"San Francisco, USA","description":"Bay Bridge approach"},
    {"id":"c5","name":"Chicago — Michigan Ave","url":"https://tinyurl.com/ycyw29me","type":"static","lat":41.878,"lon":-87.630,"city":"Chicago, USA","description":"The Magnificent Mile"},
    {"id":"c6","name":"Las Vegas — Strip","url":"https://nvroads.com/cctvImage/get?IpCameraId=1","type":"static","lat":36.115,"lon":-115.173,"city":"Las Vegas, USA","description":"Nevada DOT"},
    {"id":"c7","name":"Amsterdam — Centraal","url":"https://camera.centrum-amsterdam.nl/axis-cgi/jpg/image.cgi?resolution=640x360","type":"mjpeg","lat":52.379,"lon":4.899,"city":"Amsterdam, NL","description":"Central Station"},
    {"id":"c8","name":"Sydney — Harbour Bridge","url":"https://www.webvcr.com/static/snapshots/aus_syd_harbour.jpg","type":"static","lat":-33.852,"lon":151.211,"city":"Sydney, AU","description":"Harbour view"},
    {"id":"c9","name":"Tokyo — Shibuya","url":"https://www.worldcam.eu/static/img/webcams/japan_shibuya_crossing.jpg","type":"static","lat":35.660,"lon":139.700,"city":"Tokyo, JP","description":"Shibuya Crossing"},
    {"id":"c10","name":"London — Westminster","url":"https://www.london.gov.uk/sites/default/files/styles/gla_2_1_large/public/images/2022-04/Westminster%20Bridge.jpg","type":"static","lat":51.501,"lon":-0.122,"city":"London, UK","description":"Westminster Bridge"},
]

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ALERTS SYSTEM
# ════════════════════════════════════════════════════════════════════════════════
class AL:
    INFO = "ℹ️ INFO"; WARNING = "⚠️ WARNING"; CRITICAL = "🚨 CRITICAL"; ANOMALY = "🔴 ANOMALY"

_alert_log: list[dict] = []

def fire_alert(level: str, source: str, msg: str, details: str = "") -> dict:
    record = {"timestamp": datetime.datetime.utcnow().strftime("%H:%M:%S"),
              "level": level, "source": source, "message": msg, "details": details}
    _alert_log.append(record)
    if len(_alert_log) > 150:
        _alert_log.pop(0)
    return record

def get_alerts(limit: int = 50) -> list[dict]:
    return list(reversed(_alert_log[-limit:]))

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AVIATION DATA (OpenSky + Mock)
# ════════════════════════════════════════════════════════════════════════════════
_MOCK_AIRLINES = ["UAL","DAL","AAL","SWA","BAW","DLH","AFR","KLM","UAE","QFA","SIA","CCA","JAL","ANA","THY"]
_MOCK_COUNTRIES = ["United States","United Kingdom","Germany","France","Japan","Australia","Canada","Brazil"]
_MOCK_TYPES = ["B738","A320","B77W","A359","B789","A321","E190","CRJ9","B737","A319"]

def generate_mock_aircraft(n: int = 180) -> list[dict]:
    """Generate realistic simulated aircraft across major flight corridors."""
    random.seed(int(time.time() / 60))
    corridors = [
        (52,-30,15,40,0.25), (48,10,12,30,0.20), (37,-95,15,40,0.25),
        (25,120,20,40,0.15), (-25,135,20,30,0.10), (5,30,20,40,0.05),
    ]
    aircraft = []
    for _ in range(n):
        weights = [c[4] for c in corridors]
        lat_c,lon_c,lat_s,lon_s,_ = random.choices(corridors, weights=weights)[0]
        lat = max(-85, min(85, lat_c + random.gauss(0, lat_s)))
        lon = ((lon_c + random.gauss(0, lon_s) + 180) % 360) - 180
        airline = random.choice(_MOCK_AIRLINES)
        alt_ft = max(1000, min(45000, random.gauss(35000, 5000)))
        aircraft.append({
            "icao24": f"{random.randint(0,0xFFFFFF):06x}",
            "callsign": f"{airline}{random.randint(100,9999)}",
            "country": random.choice(_MOCK_COUNTRIES),
            "lat": round(lat, 5), "lon": round(lon, 5),
            "alt_ft": round(alt_ft),
            "speed_kts": round(random.gauss(470,50) if alt_ft > 10000 else random.gauss(250,50)),
            "heading": round(random.uniform(0,360)),
            "on_ground": False,
            "squawk": "7700" if random.random()<0.002 else "0000",
            "type": random.choice(_MOCK_TYPES),
            "is_mock": True,
        })
    return aircraft

@st.cache_data(ttl=30, show_spinner=False)
def fetch_aircraft(opensky_user: str = "", opensky_pass: str = "") -> tuple[list[dict], bool]:
    if FORCE_MOCK:
        return generate_mock_aircraft(), False
    try:
        auth = (opensky_user, opensky_pass) if opensky_user else None
        r = requests.get(OPENSKY_URL, auth=auth, timeout=API_TIMEOUT,
                        headers={"User-Agent":"AetherWatch/1.0"})
        r.raise_for_status()
        states = r.json().get("states") or []
        out = []
        for s in states[:MAX_AIRCRAFT]:
            if len(s) < 11 or s[5] is None or s[6] is None: continue
            out.append({
                "icao24": s[0] or "", "callsign": (s[1] or "").strip(),
                "country": s[2] or "", "lat": float(s[6]), "lon": float(s[5]),
                "alt_ft": round(float(s[7] or 0) * 3.28084),
                "speed_kts": round(float(s[9] or 0) * 1.94384),
                "heading": round(float(s[10] or 0)),
                "on_ground": bool(s[8]),
                "squawk": s[14] or "",
                "type": "Unknown", "is_mock": False,
            })
        return out, True
    except Exception as e:
        fire_alert(AL.WARNING, "Aviation API", f"OpenSky unavailable: {type(e).__name__}. Using mock data.")
        return generate_mock_aircraft(), False

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CAMERA FETCHER + MOCK FRAME GENERATOR
# ════════════════════════════════════════════════════════════════════════════════
_cam_status: dict = {}
_mock_vehicles: dict = {}

def fetch_camera_frame(cam: dict) -> tuple[Optional[Image.Image], bool]:
    if FORCE_MOCK:
        return _mock_frame(cam), False
    cam_id = cam["id"]
    try:
        headers = {"User-Agent":"Mozilla/5.0","Cache-Control":"no-cache"}
        if cam["type"] == "mjpeg":
            with requests.get(cam["url"], timeout=6, headers=headers, stream=True) as r:
                r.raise_for_status()
                buf = b""
                for chunk in r.iter_content(4096):
                    buf += chunk
                    s, e = buf.find(b'\xff\xd8'), buf.find(b'\xff\xd9')
                    if s != -1 and e != -1:
                        img = Image.open(io.BytesIO(buf[s:e+2])).convert("RGB")
                        _cam_status[cam_id] = {"online": True}
                        return img, True
                    if len(buf) > 800_000: break
        else:
            r = requests.get(cam["url"], timeout=6, headers=headers)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            _cam_status[cam_id] = {"online": True}
            return img, True
    except Exception:
        _cam_status[cam_id] = {"online": False}
    return _mock_frame(cam), False

def _mock_frame(cam: dict, W: int = 640, H: int = 360) -> Image.Image:
    cid = cam["id"]
    if cid not in _mock_vehicles:
        rng = random.Random(hash(cid) % 9999)
        _mock_vehicles[cid] = [
            {"x": rng.uniform(50,W-50), "y": rng.uniform(H*0.6,H*0.85),
             "speed": rng.uniform(0.3,2.0), "color": rng.choice(["#c0392b","#2980b9","#27ae60","#f39c12","#ecf0f1"]),
             "w": rng.randint(25,55), "lane": rng.randint(0,1)}
            for _ in range(rng.randint(4,10))
        ]
    for v in _mock_vehicles[cid]:
        d = 1 if v["lane"]==0 else -1
        v["x"] = (v["x"] + d * v["speed"]) % (W + 160) - 80
    img = Image.new("RGB", (W,H))
    draw = ImageDraw.Draw(img)
    for y in range(int(H*0.45)):
        ratio = y / (H*0.45)
        r,g,b = int(30+ratio*105), int(100+ratio*85), int(200+ratio*35)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    draw.rectangle([0,int(H*0.45),W,H], fill=(55,55,55))
    draw.rectangle([0,int(H*0.5),W,H], fill=(45,45,45))
    for ly in [int(H*0.63), int(H*0.75)]:
        for x in range(0,W,70):
            draw.rectangle([x,ly,x+40,ly+3], fill=(200,200,120))
    for v in _mock_vehicles[cid]:
        x,y,w,h = int(v["x"]),int(v["y"]),v["w"],14
        draw.rectangle([x,y-h,x+w,y], fill=v["color"])
        draw.rectangle([x+4,y-h+2,x+w-4,y-h+8], fill=(150,200,255))
    draw.rectangle([0,0,W,22], fill=(0,0,0))
    try: font = ImageFont.load_default()
    except: font = None
    draw.text((4,5), f"📷 {cam['name']} | {time.strftime('%H:%M:%S')} UTC | ⚠ SIMULATED", fill=(255,80,80), font=font)
    draw.rectangle([0,H-20,W,H], fill=(0,0,0))
    draw.text((4,H-15), f"📍 {cam.get('city','')} — {cam.get('description','')}", fill=(180,180,180), font=font)
    return img.filter(ImageFilter.GaussianBlur(0.4))

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — NASA GIBS SATELLITE IMAGERY
# ════════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_satellite(layer_id: str, date_str: str, region: str) -> tuple[Optional[Image.Image], bool]:
    regions = {
        "Global":(-180,-90,180,90), "North America":(-170,15,-50,80),
        "Europe":(-30,30,45,75), "Asia Pacific":(60,-15,180,60),
        "Africa":(-25,-40,60,40), "South America":(-85,-60,-30,15),
    }
    bbox = regions.get(region, (-180,-90,180,90))
    lon_s, lat_s = bbox[2]-bbox[0], bbox[3]-bbox[1]
    W, H = 800, max(200, int(800 * lat_s / lon_s)) if lon_s > 0 else (800,400)
    
    if FORCE_MOCK:
        return _mock_satellite(layer_id, W, H), False
    
    params = {"SERVICE":"WMS","VERSION":"1.1.1","REQUEST":"GetMap","LAYERS":layer_id,
              "STYLES":"","SRS":"EPSG:4326",
              "BBOX":f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
              "WIDTH":str(W),"HEIGHT":str(H),"FORMAT":"image/jpeg","TIME":date_str}
    try:
        r = requests.get(NASA_GIBS_WMS, params=params, timeout=15,
                        headers={"User-Agent":"AetherWatch/1.0"})
        r.raise_for_status()
        if "image" not in r.headers.get("Content-Type",""):
            raise ValueError("Non-image response")
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0,0,W,20], fill=(0,0,0))
        try: font = ImageFont.load_default()
        except: font = None
        draw.text((4,3), f"🛰 NASA GIBS | {layer_id[:40]} | {date_str}", fill=(80,200,80), font=font)
        return img, True
    except Exception as e:
        fire_alert(AL.WARNING, "Satellite API", f"NASA GIBS error: {e}. Using mock imagery.")
        return _mock_satellite(layer_id, W, H), False

def _mock_satellite(layer_id: str, W: int, H: int) -> Image.Image:
    ocean = (20,60,140) if "Night" not in layer_id else (5,5,20)
    land = (80,130,60) if "Night" not in layer_id else (255,200,50)
    pixels = np.full((H,W,3), ocean, dtype=np.uint8)
    np.random.seed(42)
    noise = np.random.rand(H//4+1, W//4+1)
    noise_img = Image.fromarray((noise*255).astype(np.uint8)).resize((W,H), Image.BILINEAR)
    mask = np.array(noise_img) > 110
    for c in range(3):
        pixels[:,:,c] = np.where(mask, land[c], ocean[c])
    pixels = np.clip(pixels.astype(np.int16) + (np.random.rand(H,W)*20-10)[...,np.newaxis], 0, 255).astype(np.uint8)
    img = Image.fromarray(pixels)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0,0,W,20], fill=(0,0,0))
    try: font = ImageFont.load_default()
    except: font = None
    draw.text((4,3), f"🛰 SIMULATED | {layer_id[:40]} | Connect to NASA GIBS for real data", fill=(255,80,80), font=font)
    return img

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — YOLO DETECTOR
# ════════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="🤖 Loading YOLO model…")
def load_yolo():
    try:
        from ultralytics import YOLO
        import torch
        device = "cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends,"mps") and torch.backends.mps.is_available() else "cpu")
        model = YOLO(YOLO_MODEL)
        model(np.zeros((640,640,3),dtype=np.uint8), device=device, verbose=False)  # warm up
        return model, device
    except Exception as e:
        return None, "cpu"

def run_yolo(img: Image.Image, model, device: str) -> tuple[Image.Image, list[str], int]:
    if model is None:
        return img, [], 0
    try:
        arr = np.array(img)
        results = model(arr, device=device, conf=YOLO_CONF, verbose=False)
        r = results[0]
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.load_default()
        except: font = None
        counts: dict[str,int] = {}
        class_colors = {"person":"#FF4444","car":"#44FF44","truck":"#FF8800","bus":"#FF8800","motorcycle":"#00FFFF","airplane":"#FF44FF","boat":"#4488FF"}
        for box in r.boxes:
            cid = int(box.cls[0]); conf = float(box.conf[0])
            name = r.names.get(cid, str(cid))
            x1,y1,x2,y2 = [int(v) for v in box.xyxy[0].tolist()]
            color = class_colors.get(name, "#FFFFFF")
            draw.rectangle([x1,y1,x2,y2], outline=color, width=2)
            label = f"{name} {conf:.0%}"
            draw.rectangle([x1,y1-14,x1+len(label)*6+4,y1], fill=color)
            draw.text((x1+2,y1-13), label, fill=(0,0,0), font=font)
            counts[name] = counts.get(name,0) + 1
        anomalies = []
        if counts.get("person",0) >= 8: anomalies.append(f"🚨 Crowd: {counts['person']} persons")
        vehicles = sum(counts.get(c,0) for c in ["car","truck","bus","motorcycle"])
        if vehicles >= 10: anomalies.append(f"⚠️ Vehicle cluster: {vehicles}")
        n = sum(counts.values())
        if counts and n > 0:
            w,h = img.size
            draw.rectangle([0,h-18,w,h], fill=(0,0,0))
            draw.text((4,h-14), "Detected: " + " | ".join(f"{k}:{v}" for k,v in counts.items()), fill=(100,255,100), font=font)
        return img, anomalies, n
    except Exception as e:
        return img, [], 0

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MAP BUILDER
# ════════════════════════════════════════════════════════════════════════════════
def build_folium_map(aircraft: list[dict], cameras: list[dict], map_tile: str,
                     show_ac: bool, show_cam: bool, cluster: bool) -> folium.Map:
    tiles_map = {
        "Dark":"CartoDB dark_matter", "Light":"CartoDB positron",
        "Satellite":"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Street":"OpenStreetMap",
    }
    tile = tiles_map.get(map_tile, "CartoDB dark_matter")
    m = folium.Map(location=[25,10], zoom_start=3, tiles=tile, prefer_canvas=True)

    if show_ac and aircraft:
        grp = folium.plugins.MarkerCluster(name="Aircraft", maxClusterRadius=40, disableClusteringAtZoom=6) if (cluster and len(aircraft)>100) else folium.FeatureGroup(name="Aircraft")
        for ac in aircraft:
            color = "#d29922" if ac.get("is_mock") else ("#8b949e" if ac.get("on_ground") else "#58a6ff")
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" style="transform:rotate({ac["heading"]}deg)"><path fill="{color}" d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2 1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>'
            popup_html = f"<b>✈ {ac['callsign']}</b><br>Alt: {ac['alt_ft']:,} ft<br>Speed: {ac['speed_kts']} kts<br>Country: {ac['country']}<br>Squawk: {ac['squawk'] or 'N/A'}{'<br><b style=color:red>⚠ MOCK</b>' if ac.get('is_mock') else ''}"
            folium.Marker(
                [ac["lat"], ac["lon"]],
                icon=folium.DivIcon(html=svg, icon_size=(16,16), icon_anchor=(8,8)),
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=f"{ac['callsign']} | {ac['alt_ft']:,}ft",
            ).add_to(grp)
        grp.add_to(m)

    if show_cam and cameras:
        cam_grp = folium.FeatureGroup(name="Cameras")
        for cam in cameras:
            online = _cam_status.get(cam["id"],{}).get("online", None)
            col = "🟢" if online else ("🔴" if online is False else "⚪")
            folium.Marker(
                [cam["lat"], cam["lon"]],
                icon=folium.DivIcon(html=f'<div style="font-size:15px">{col}📷</div>', icon_size=(30,20), icon_anchor=(15,10)),
                popup=f"<b>{cam['name']}</b><br>{cam['city']}<br>{cam.get('description','')}",
                tooltip=cam["name"],
            ).add_to(cam_grp)
        cam_grp.add_to(m)

    folium.plugins.Fullscreen(position="topright").add_to(m)
    folium.LayerControl().add_to(m)
    live = sum(1 for a in aircraft if not a.get("is_mock"))
    mock = len(aircraft) - live
    folium.Element(f"""<div style="position:fixed;bottom:25px;left:10px;z-index:999;
        background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px 12px;
        font-family:monospace;font-size:12px;color:#e6edf3">
        🛰️ <b>AetherWatch</b><br>✈ {len(aircraft)} aircraft
        {'(live)' if live==len(aircraft) else f'({live} live, {mock} sim)'}<br>📷 {len(cameras)} cameras
        </div>""").add_to(m.get_root().html)
    return m

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 8 — CSS
# ════════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""<style>
    .main{background:#0d1117}
    .stTabs [data-baseweb="tab"]{background:#161b22;border:1px solid #30363d;color:#8b949e;border-radius:6px 6px 0 0;padding:8px 20px}
    .stTabs [aria-selected="true"]{background:#1f6feb!important;color:white!important}
    .block-container{padding-top:0.8rem}
    .stMetric{background:#161b22;padding:10px;border-radius:8px;border:1px solid #30363d}
    ::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
    </style>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MAIN APP
# ════════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()

    # ── Session state
    for k,v in [("custom_cams",[]),("selected_cams",[c["id"] for c in PUBLIC_CAMERAS[:4]])]:
        if k not in st.session_state: st.session_state[k] = v

    all_cams = PUBLIC_CAMERAS + st.session_state.custom_cams

    # ── Sidebar
    with st.sidebar:
        st.markdown("<div style='text-align:center;padding:8px 0'><div style='font-size:32px'>🛰️</div><div style='font-size:20px;font-weight:bold;color:#58a6ff'>AetherWatch</div><div style='font-size:11px;color:#8b949e'>Real-Time Surveillance Dashboard</div></div><hr style='border-color:#30363d'>", unsafe_allow_html=True)

        refresh_rate = st.slider("🔄 Refresh (seconds)", 10, 120, DEFAULT_REFRESH, 5)
        
        with st.expander("🔑 API Credentials"):
            osky_user = st.text_input("OpenSky Username", type="default")
            osky_pass = st.text_input("OpenSky Password", type="password")
            st.caption("[Get free account](https://opensky-network.org)")
        
        st.subheader("🗺️ Map")
        map_tile = st.selectbox("Style", ["Dark","Light","Satellite","Street"])
        show_ac = st.checkbox("Aircraft", True)
        show_cam_map = st.checkbox("Camera pins", True)
        cluster = st.checkbox("Cluster aircraft", True)
        
        st.subheader("📷 Cameras")
        cam_choices = {c["id"]:c["name"] for c in all_cams}
        sel_ids = st.multiselect("Active Feeds (max 4)", list(cam_choices.keys()),
            default=st.session_state.selected_cams[:4], format_func=lambda x: cam_choices.get(x,x), max_selections=4)
        st.session_state.selected_cams = sel_ids
        cam_cols = st.selectbox("Grid columns", [1,2], index=1)
        
        st.subheader("🤖 YOLO Detection")
        yolo_on = st.checkbox("Enable detection", False)
        
        st.subheader("🛰️ Satellite")
        sat_layer_name = st.selectbox("Layer", list(SATELLITE_LAYERS.keys()))
        sat_region = st.selectbox("Region", ["Global","North America","Europe","Asia Pacific","Africa","South America"])
        sat_date = st.date_input("Date", datetime.date.today() - datetime.timedelta(days=2))
        
        st.markdown("---")
        st.markdown("<div style='font-size:10px;color:#8b949e'>⚖️ Educational/research use only. Comply with local laws & provider ToS. Not for surveillance of individuals.</div>", unsafe_allow_html=True)

    # ── Auto-refresh
    st_autorefresh(interval=refresh_rate*1000, key="main_refresh")

    # ── Fetch data
    aircraft, is_live = fetch_aircraft(osky_user, osky_pass)
    model, device = load_yolo() if yolo_on else (None, "cpu")

    # Emergency squawk alerts
    for ac in aircraft:
        if ac["squawk"] in ("7700","7600","7500"):
            names = {"7700":"Emergency","7600":"Radio Failure","7500":"Hijack"}
            fire_alert(AL.CRITICAL, "Aviation", f"{ac['callsign']} squawking {ac['squawk']} — {names[ac['squawk']]}")

    # ── Header
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    live_badge = "🟢 LIVE" if is_live else "🟡 SIMULATED"
    st.markdown(f"""<div style="background:linear-gradient(135deg,#0d1117,#1a237e,#0d1117);border-bottom:1px solid #30363d;padding:10px 18px;border-radius:8px;margin-bottom:12px">
    <table style="width:100%;border-collapse:collapse"><tr>
    <td style="font-size:18px;font-weight:bold;color:#58a6ff">🛰️ AetherWatch</td>
    <td style="text-align:center;color:#8b949e;font-size:13px">✈️ {len(aircraft)} Aircraft &nbsp;|&nbsp; 📷 {len(all_cams)} Cameras</td>
    <td style="text-align:right;font-size:12px;color:#8b949e">{live_badge} &nbsp; {ts}</td>
    </tr></table></div>""", unsafe_allow_html=True)

    # ── Metrics
    mc = st.columns(5)
    mc[0].metric("✈️ Aircraft", len(aircraft))
    mc[1].metric("🛫 Airborne", sum(1 for a in aircraft if not a.get("on_ground")))
    mc[2].metric("🚨 Alerts", len([a for a in get_alerts(50) if "CRITICAL" in a["level"]]))
    mc[3].metric("📷 Cameras", len(sel_ids))
    mc[4].metric("📡 Source", "OpenSky" if is_live else "Simulated")

    # ── Tabs
    t_map, t_cams, t_sat, t_alerts = st.tabs(["🗺️ World Map","📷 Cameras","🛰️ Satellite","🚨 Alerts"])

    # ── MAP TAB
    with t_map:
        fmap = build_folium_map(aircraft, all_cams, map_tile, show_ac, show_cam_map, cluster)
        st_folium(fmap, width=None, height=530, use_container_width=True, returned_objects=[])
        with st.expander(f"📊 Aircraft Table ({len(aircraft)} total)"):
            import pandas as pd
            df = pd.DataFrame(aircraft)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("⬇️ CSV", df.to_csv(index=False), f"aircraft_{int(time.time())}.csv", "text/csv")

    # ── CAMERAS TAB
    with t_cams:
        # Add custom camera
        with st.expander("➕ Add Custom Camera"):
            with st.form("add_cam"):
                cn = st.text_input("Name"); cu = st.text_input("URL")
                ct = st.selectbox("Type",["static","mjpeg"])
                cc1,cc2 = st.columns(2)
                clat = cc1.number_input("Lat",value=0.0,format="%.4f")
                clon = cc2.number_input("Lon",value=0.0,format="%.4f")
                ccity = st.text_input("City")
                if st.form_submit_button("Add",type="primary") and cn and cu:
                    nc = {"id":f"cu_{int(time.time())}","name":cn,"url":cu,"type":ct,
                          "lat":clat,"lon":clon,"city":ccity,"description":"Custom"}
                    st.session_state.custom_cams.append(nc)
                    fire_alert(AL.INFO,"UI",f"Custom camera added: {cn}")
                    st.rerun()
        
        selected = [c for c in all_cams if c["id"] in sel_ids]
        if not selected:
            st.info("👈 Select cameras from the sidebar.")
        else:
            grid = st.columns(min(cam_cols, len(selected)))
            for idx, cam in enumerate(selected[:4]):
                with grid[idx % cam_cols]:
                    st.markdown(f"**📷 {cam['name']}** &nbsp; `{cam['city']}`")
                    t0 = time.time()
                    img, live_feed = fetch_camera_frame(cam)
                    fetch_ms = (time.time()-t0)*1000
                    img = img.resize((640,360), Image.LANCZOS)
                    anomalies_det = []
                    if yolo_on and model:
                        img, anomalies_det, nd = run_yolo(img, model, device)
                        for a in anomalies_det: st.warning(a)
                    badge = "🟢 LIVE" if live_feed else "🟡 SIM"
                    st.image(img, use_container_width=True,
                        caption=f"{badge} | {fetch_ms:.0f}ms" + (f" | YOLO: {nd} objects" if yolo_on else ""))

    # ── SATELLITE TAB
    with t_sat:
        st.subheader("🛰️ NASA GIBS Satellite Imagery")
        lay_id = SATELLITE_LAYERS[sat_layer_name]
        with st.spinner("Loading satellite imagery…"):
            sat_img, sat_live = fetch_satellite(lay_id, sat_date.strftime("%Y-%m-%d"), sat_region)
        if sat_img:
            sat_img_display = sat_img.copy()
            if yolo_on and model:
                sat_img_display, sat_anom, _ = run_yolo(sat_img_display, model, device)
                for a in sat_anom: st.warning(f"🛰️ {a}")
            badge = "🟢 NASA LIVE DATA" if sat_live else "🟡 SIMULATED IMAGERY"
            st.image(sat_img_display, use_container_width=True,
                caption=f"{badge} | {sat_layer_name} | {sat_date} | {sat_region}")
        else:
            st.error("Failed to load satellite imagery.")
        st.caption("Source: [NASA GIBS](https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs) — no API key required")

    # ── ALERTS TAB
    with t_alerts:
        st.subheader("🚨 Alerts & System Log")
        alerts = get_alerts(100)
        ac1,ac2,ac3 = st.columns([2,2,1])
        lvl_filter = ac1.multiselect("Level", [AL.CRITICAL,AL.ANOMALY,AL.WARNING,AL.INFO],
                                     default=[AL.CRITICAL,AL.ANOMALY,AL.WARNING,AL.INFO])
        src_filter = ac2.text_input("Source filter")
        if ac3.button("🗑️ Clear"):
            _alert_log.clear(); st.rerun()
        
        filtered = [a for a in alerts if a["level"] in lvl_filter and
                   (not src_filter or src_filter.lower() in a["source"].lower())]
        
        mc2 = st.columns(4)
        mc2[0].metric("Total", len(_alert_log))
        mc2[1].metric("🚨 Critical", sum(1 for a in _alert_log if "CRITICAL" in a["level"]))
        mc2[2].metric("🔴 Anomalies", sum(1 for a in _alert_log if "ANOMALY" in a["level"]))
        mc2[3].metric("⚠️ Warnings", sum(1 for a in _alert_log if "WARNING" in a["level"]))
        
        st.markdown("---")
        if not filtered:
            st.info("✅ No alerts matching filters.")
        else:
            level_styles = {
                AL.CRITICAL:("#3d0000","#f85149"),
                AL.ANOMALY:("#2d1800","#d29922"),
                AL.WARNING:("#1f2200","#d29922"),
                AL.INFO:("#0d1f0d","#3fb950"),
            }
            html = ""
            for a in filtered:
                bg,border = level_styles.get(a["level"],("#161b22","#30363d"))
                html += f"""<div style="background:{bg};border-left:3px solid {border};
                    border-radius:4px;padding:7px 12px;margin-bottom:5px;font-family:monospace;
                    font-size:12px;color:#e6edf3">
                    <span style="color:{border}">{a['level']}</span>
                    <span style="color:#8b949e;margin-left:8px">{a['timestamp']}</span>
                    <span style="color:#58a6ff;margin-left:8px">[{a['source']}]</span><br>
                    {a['message']}</div>"""
            st.markdown(f"<div style='max-height:450px;overflow-y:auto'>{html}</div>", unsafe_allow_html=True)

    # ── Footer
    st.markdown("<hr style='border-color:#30363d;margin-top:16px'><div style='text-align:center;font-size:11px;color:#8b949e'>AetherWatch v1.0.0 | Data: <a href='https://opensky-network.org' style='color:#58a6ff'>OpenSky</a> • <a href='https://earthdata.nasa.gov' style='color:#58a6ff'>NASA GIBS</a> | Educational use only | Not for surveillance of individuals</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
