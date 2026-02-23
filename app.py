"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           AetherWatch v1.0.0                               ║
║          Real-Time Multi-Source Surveillance Dashboard                      ║
║                                                                              ║
║  Data Sources:                                                               ║
║    ✈️  OpenSky Network — live global aircraft positions (free)              ║
║    📷  Public traffic cameras — MJPEG + static JPEG feeds                  ║
║    🛰️  NASA GIBS — near real-time satellite imagery (no key needed)        ║
║    🤖  YOLOv8 — on-device object detection & anomaly alerts                ║
║                                                                              ║
║  Deployment: Streamlit Community Cloud (free)                               ║
║  GitHub: https://github.com/your-org/aetherwatch                           ║
║                                                                              ║
║  ETHICS & LEGAL: This tool uses only publicly broadcast/available data.     ║
║  Always comply with local surveillance laws, GDPR, CCPA, and the           ║
║  terms of service of each data provider. Do not use for surveillance        ║
║  of private individuals.                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import datetime
import threading
import streamlit as st
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# ── Must be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="AetherWatch",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-org/aetherwatch",
        "Report a bug": "https://github.com/your-org/aetherwatch/issues",
        "About": "AetherWatch — Real-Time Surveillance Dashboard v1.0.0",
    },
)

# ── Internal imports ──────────────────────────────────────────────────────────
from config import settings
from data_sources.aviation import fetch_aircraft, check_aviation_anomalies
from data_sources.cameras import get_all_cameras
from ui.map_view import build_map
from ui.camera_grid import render_camera_grid, render_add_camera_form
from ui.satellite_view import render_satellite_panel
from ui.alerts_panel import render_alerts_panel
from utils.alerts import dispatch_alert, AlertLevel
from utils.logger import get_logger

log = get_logger(__name__)


# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    /* Dark theme overrides */
    .main { background-color: #0d1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 6px 6px 0 0;
        border: 1px solid #30363d;
        color: #8b949e;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: white !important;
    }
    .stMetric { background: #161b22; padding: 12px; border-radius: 8px; border: 1px solid #30363d; }
    
    /* Header gradient */
    .aetherwatch-header {
        background: linear-gradient(135deg, #0d1117 0%, #1a237e 50%, #0d1117 100%);
        border-bottom: 1px solid #30363d;
        padding: 12px 20px;
        margin-bottom: 16px;
        border-radius: 8px;
    }
    
    /* Status badge */
    .status-live { color: #3fb950; font-weight: bold; }
    .status-mock { color: #d29922; font-weight: bold; }
    .status-offline { color: #f85149; font-weight: bold; }
    
    /* Reduce padding */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)


# ── Session state initialisation ──────────────────────────────────────────────
def init_session_state():
    defaults = {
        "aircraft_list": [],
        "aircraft_is_live": False,
        "last_aviation_fetch": 0,
        "custom_cameras": [],
        "selected_camera_ids": [c["id"] for c in settings.PUBLIC_CAMERAS[:4]],
        "refresh_count": 0,
        "anomalies_detected": [],
        "yolo_detector": None,
        "detector_initialised": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── YOLO singleton loader (cached as resource) ─────────────────────────────────
@st.cache_resource(show_spinner="🤖 Loading YOLO model…")
def load_detector():
    """Load YOLOv8 detector once and cache for the session lifetime."""
    try:
        from vision.detector import YOLODetector
        detector = YOLODetector.get_instance()
        log.info(f"Detector ready: {detector.device_info}")
        return detector
    except Exception as e:
        log.error(f"Could not load YOLO detector: {e}")
        return None


# ── Aviation data fetcher ─────────────────────────────────────────────────────
@st.cache_data(ttl=settings.CACHE_TTL_AVIATION, show_spinner=False)
def get_aircraft_data():
    """Cached aircraft fetch — Streamlit caches by TTL automatically."""
    aircraft, is_live = fetch_aircraft()
    anomalies = check_aviation_anomalies(aircraft)
    for a in anomalies:
        dispatch_alert(a["level"], "Aviation Anomaly", a["message"])
    return aircraft, is_live, anomalies


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar(all_cameras: list[dict]) -> dict:
    """Render sidebar and return config dict of user selections."""
    with st.sidebar:
        # Logo / title
        st.markdown("""
        <div style="text-align:center; padding:10px 0">
          <div style="font-size:36px">🛰️</div>
          <div style="font-size:22px; font-weight:bold; color:#58a6ff">AetherWatch</div>
          <div style="font-size:11px; color:#8b949e">Real-Time Surveillance Dashboard</div>
        </div>
        <hr style="border-color:#30363d; margin:8px 0">
        """, unsafe_allow_html=True)
        
        # ── Refresh settings
        st.subheader("⏱️ Refresh")
        refresh_rate = st.slider(
            "Auto-refresh interval (seconds)",
            min_value=settings.MIN_REFRESH_RATE,
            max_value=settings.MAX_REFRESH_RATE,
            value=settings.DEFAULT_REFRESH_RATE,
            step=5,
        )
        
        # ── API credentials
        with st.expander("🔑 API Credentials", expanded=False):
            st.caption("Credentials are stored only in your session — never sent to our servers.")
            opensky_user = st.text_input("OpenSky Username", value=settings.OPENSKY_USERNAME, type="default")
            opensky_pass = st.text_input("OpenSky Password", value="", type="password")
            fr24_token = st.text_input("FlightRadar24 Token (optional)", value="", type="password")
            if fr24_token:
                settings.FR24_TOKEN = fr24_token
            if opensky_user:
                settings.OPENSKY_USERNAME = opensky_user
            if opensky_pass:
                settings.OPENSKY_PASSWORD = opensky_pass
            st.caption(
                "📝 [Get free OpenSky account](https://opensky-network.org/index.php?option=com_users&view=registration) | "
                "[FR24 API](https://fr24api.flightradar24.com)"
            )
        
        # ── Map settings
        st.subheader("🗺️ Map")
        map_tile = st.selectbox("Map Style", list(settings.MAP_TILES.keys()), index=0)
        show_aircraft = st.checkbox("Show Aircraft", value=True)
        show_cameras_map = st.checkbox("Show Camera Locations", value=True)
        cluster_aircraft = st.checkbox("Cluster Aircraft (faster)", value=True)
        
        with st.expander("🛰️ Satellite Overlay (on map)"):
            show_sat_overlay = st.checkbox("Enable satellite overlay", value=False)
            if show_sat_overlay:
                sat_overlay_layer = st.selectbox(
                    "Layer", list(settings.SATELLITE_LAYERS.keys()), key="map_sat_layer"
                )
                sat_overlay_id = settings.SATELLITE_LAYERS[sat_overlay_layer]
                import datetime as _dt
                sat_date = st.date_input(
                    "Date", value=_dt.date.today() - _dt.timedelta(days=2)
                )
                sat_date_str = sat_date.strftime("%Y-%m-%d")
            else:
                sat_overlay_id = ""
                sat_date_str = ""
        
        # ── Camera settings
        st.subheader("📷 Cameras")
        camera_options = {c["id"]: c["name"] for c in all_cameras}
        selected_ids = st.multiselect(
            "Active Camera Feeds (max 4)",
            options=list(camera_options.keys()),
            default=st.session_state.selected_camera_ids[:4],
            format_func=lambda x: camera_options.get(x, x),
            max_selections=4,
        )
        if selected_ids != st.session_state.selected_camera_ids:
            st.session_state.selected_camera_ids = selected_ids
        
        cam_cols = st.selectbox("Grid Columns", [1, 2], index=1)
        
        # ── YOLO settings
        st.subheader("🤖 Object Detection")
        detection_enabled = st.checkbox("Enable YOLO Detection", value=False,
            help="Runs YOLOv8 on camera frames. May be slower on CPU.")
        
        if detection_enabled:
            conf_threshold = st.slider("Confidence Threshold", 0.1, 0.9,
                                       settings.YOLO_CONFIDENCE, 0.05)
            settings.YOLO_CONFIDENCE = conf_threshold
            detect_satellite = st.checkbox("Also detect on satellite imagery", value=False)
        else:
            detect_satellite = False
        
        # ── System info
        st.markdown("---")
        with st.expander("⚙️ System Info"):
            st.caption(f"**App:** AetherWatch v{settings.APP_VERSION}")
            st.caption(f"**Mock data:** {settings.FORCE_MOCK_DATA}")
            
            detector = load_detector() if detection_enabled else None
            if detector:
                st.caption(f"**YOLO:** {detector.device_info}")
            else:
                st.caption("**YOLO:** Disabled")
            
            from utils.cache import cache_stats
            cs = cache_stats()
            st.caption(f"**Cache:** {cs['valid_entries']} valid / {cs['total_entries']} total entries")
        
        # ── Legal disclaimer
        st.markdown("""
        <div style="font-size:10px; color:#8b949e; margin-top:12px; line-height:1.4">
          ⚖️ <b>Legal:</b> For educational/research use only. 
          Uses publicly available data. Comply with local laws and 
          each provider's terms of service. Not for surveillance of individuals.
        </div>
        """, unsafe_allow_html=True)
    
    return {
        "refresh_rate": refresh_rate,
        "map_tile": map_tile,
        "show_aircraft": show_aircraft,
        "show_cameras_map": show_cameras_map,
        "cluster_aircraft": cluster_aircraft,
        "show_sat_overlay": show_sat_overlay if "show_sat_overlay" in locals() else False,
        "sat_overlay_id": sat_overlay_id if "sat_overlay_id" in locals() else "",
        "sat_date_str": sat_date_str if "sat_date_str" in locals() else "",
        "selected_camera_ids": selected_ids,
        "cam_cols": cam_cols,
        "detection_enabled": detection_enabled,
        "detect_satellite": detect_satellite,
    }


# ── Header banner ─────────────────────────────────────────────────────────────
def render_header(aircraft_count: int, is_live: bool, camera_count: int):
    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    live_badge = '<span class="status-live">● LIVE</span>' if is_live else '<span class="status-mock">● SIMULATED</span>'
    
    st.markdown(f"""
    <div class="aetherwatch-header">
      <table style="width:100%; border-collapse:collapse">
        <tr>
          <td style="font-size:20px; font-weight:bold; color:#58a6ff">🛰️ AetherWatch</td>
          <td style="text-align:center; color:#8b949e">✈️ {aircraft_count} Aircraft &nbsp;|&nbsp; 📷 {camera_count} Cameras &nbsp;|&nbsp; 🤖 YOLO Active</td>
          <td style="text-align:right; font-size:12px; color:#8b949e">{live_badge} &nbsp; {now_utc}</td>
        </tr>
      </table>
    </div>
    """, unsafe_allow_html=True)


# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    inject_css()
    init_session_state()
    
    # All cameras (public + any custom added)
    all_cameras = get_all_cameras() + st.session_state.custom_cameras
    
    # Sidebar config
    cfg = render_sidebar(all_cameras)
    
    # Auto-refresh ticker
    st_autorefresh(interval=cfg["refresh_rate"] * 1000, key="dashboard_refresh")
    
    # ── Fetch data
    with st.spinner("Fetching aviation data…"):
        aircraft_list, is_live, av_anomalies = get_aircraft_data()
    
    # Load detector if enabled
    detector = load_detector() if cfg["detection_enabled"] else None
    
    # Header
    render_header(len(aircraft_list), is_live, len(all_cameras))
    
    # ── Quick metrics row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("✈️ Aircraft", len(aircraft_list),
                  help="Live aircraft tracked globally")
    with m2:
        airborne = sum(1 for a in aircraft_list if not a.on_ground)
        st.metric("🛫 Airborne", airborne)
    with m3:
        from utils.alerts import get_recent_alerts
        recent = get_recent_alerts(limit=50)
        critical = sum(1 for a in recent if a.level == AlertLevel.CRITICAL)
        st.metric("🚨 Critical", critical, delta=None if critical == 0 else f"+{critical}")
    with m4:
        st.metric("📷 Cameras", len(cfg["selected_camera_ids"]))
    with m5:
        data_source = "OpenSky" if not settings.FR24_TOKEN else "FR24"
        if settings.FORCE_MOCK_DATA:
            data_source = "Simulated"
        st.metric("📡 Source", data_source if is_live else "Simulated")
    
    st.markdown("")
    
    # ── Anomaly banner
    if av_anomalies:
        for anom in av_anomalies[:3]:
            st.error(f"🚨 {anom['message']}")
    
    # ── Main content tabs
    tab_map, tab_cameras, tab_satellite, tab_alerts = st.tabs([
        "🗺️ World Map", "📷 Camera Grid", "🛰️ Satellite", "🚨 Alerts & Log"
    ])
    
    # ─────────────────────────────────────────────────────────────────────────
    with tab_map:
        st.subheader("✈️ Live World Map")
        
        from data_sources.cameras import get_camera_status
        
        fmap = build_map(
            aircraft_list=aircraft_list,
            cameras=all_cameras,
            tile_style=cfg["map_tile"],
            show_aircraft=cfg["show_aircraft"],
            show_cameras=cfg["show_cameras_map"],
            show_satellite_overlay=cfg["show_sat_overlay"],
            satellite_layer=cfg["sat_overlay_id"],
            satellite_date=cfg["sat_date_str"],
            camera_status=get_camera_status(),
            cluster_aircraft=cfg["cluster_aircraft"],
        )
        
        st_folium(
            fmap,
            width=None,
            height=550,
            returned_objects=[],  # Don't return click events (faster)
            use_container_width=True,
        )
        
        # Aircraft table
        with st.expander(f"📊 Aircraft Data Table ({len(aircraft_list)} aircraft)", expanded=False):
            import pandas as pd
            if aircraft_list:
                df = pd.DataFrame([a.to_dict() for a in aircraft_list])
                cols_order = ["callsign", "country", "alt_ft", "speed_kts", "heading",
                              "on_ground", "squawk", "type", "lat", "lon"]
                df = df[[c for c in cols_order if c in df.columns]]
                
                # Highlight emergency squawks
                def highlight_squawk(row):
                    if row.get("squawk") in ["7700", "7600", "7500"]:
                        return ["background-color: #3d0000"] * len(row)
                    return [""] * len(row)
                
                st.dataframe(
                    df.style.apply(highlight_squawk, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )
                
                csv = df.to_csv(index=False)
                st.download_button(
                    "⬇️ Export Aircraft CSV",
                    data=csv,
                    file_name=f"aircraft_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
    
    # ─────────────────────────────────────────────────────────────────────────
    with tab_cameras:
        # Custom camera form
        new_cam = render_add_camera_form()
        if new_cam:
            st.session_state.custom_cameras.append(new_cam)
            dispatch_alert(AlertLevel.INFO, "UI", f"Custom camera added: {new_cam['name']}")
            st.success(f"✅ Camera '{new_cam['name']}' added!")
            st.rerun()
        
        # Camera grid
        selected_ids = cfg["selected_camera_ids"]
        if not selected_ids:
            st.info("👈 Select cameras from the sidebar to display feeds here.")
        else:
            render_camera_grid(
                selected_camera_ids=selected_ids,
                detection_enabled=cfg["detection_enabled"],
                detector=detector,
                cols=cfg["cam_cols"],
            )
    
    # ─────────────────────────────────────────────────────────────────────────
    with tab_satellite:
        render_satellite_panel(
            detector=detector if cfg["detect_satellite"] else None,
            detection_enabled=cfg["detect_satellite"],
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    with tab_alerts:
        render_alerts_panel()
    
    # ── Footer
    st.markdown("""
    <hr style="border-color:#30363d; margin-top:20px">
    <div style="text-align:center; font-size:11px; color:#8b949e; padding:8px 0">
      AetherWatch v1.0.0 &nbsp;|&nbsp;
      Data: <a href="https://opensky-network.org" style="color:#58a6ff">OpenSky Network</a> &nbsp;•&nbsp;
      <a href="https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs" style="color:#58a6ff">NASA GIBS</a> &nbsp;|&nbsp;
      For educational/research use only &nbsp;|&nbsp;
      Not for surveillance of private individuals
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
