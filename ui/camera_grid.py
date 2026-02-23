"""
AetherWatch — Camera Grid UI
Renders a 2×2 (or n×m) grid of live camera feeds with optional YOLO detection overlays.
Each panel shows: live/mock feed, detection boxes, anomaly indicators, FPS counter.
"""

import time
import threading
from typing import Optional
import streamlit as st
from PIL import Image

from data_sources.cameras import fetch_camera_frame, get_all_cameras
from config import settings


def render_camera_grid(
    selected_camera_ids: list[str],
    detection_enabled: bool = False,
    detector=None,
    cols: int = 2,
):
    """
    Render a responsive grid of camera feeds in the Streamlit UI.
    
    Args:
        selected_camera_ids: List of camera IDs to display (up to 4)
        detection_enabled:   Run YOLO on each frame
        detector:            YOLODetector instance (or None)
        cols:                Number of grid columns (1 or 2)
    """
    cameras = {c["id"]: c for c in get_all_cameras()}
    selected = [cameras[cid] for cid in selected_camera_ids if cid in cameras][:4]
    
    if not selected:
        st.info("📷 No cameras selected. Use the sidebar to choose camera feeds.")
        return
    
    # Create grid columns
    grid_cols = st.columns(min(cols, len(selected)))
    
    for idx, camera in enumerate(selected):
        col = grid_cols[idx % cols]
        
        with col:
            _render_camera_panel(camera, detection_enabled, detector)


def _render_camera_panel(camera: dict, detection_enabled: bool, detector):
    """Render a single camera panel with frame and metadata."""
    cam_id = camera["id"]
    cam_name = camera["name"]
    
    # Panel header
    with st.container():
        # Status badge + name
        st.markdown(
            f"<div style='background:#161b22; padding:6px 10px; border-radius:6px 6px 0 0; "
            f"border:1px solid #30363d; font-size:13px; color:#e6edf3'>"
            f"<b>📷 {cam_name}</b> &nbsp;|&nbsp; "
            f"<span style='color:#8b949e'>{camera.get('city','')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        
        # Fetch frame
        t0 = time.time()
        img, is_live = fetch_camera_frame(camera)
        fetch_ms = (time.time() - t0) * 1000
        
        if img is None:
            st.error(f"❌ Cannot load camera: {cam_name}")
            return
        
        # Resize for display
        display_size = (640, 360)
        img = img.resize(display_size, Image.LANCZOS)
        
        # Run YOLO detection if enabled
        anomalies = []
        inference_ms = 0.0
        det_count = 0
        
        if detection_enabled and detector is not None:
            try:
                result = detector.detect(img, camera_id=cam_id)
                img = result.annotated_image or img
                anomalies = result.anomalies
                inference_ms = result.inference_ms
                det_count = len(result.detections)
                
                # Show anomaly alerts inline
                for anomaly in anomalies:
                    st.warning(anomaly)
            except Exception as e:
                pass  # Graceful degradation — show frame without detection
        
        # Display the frame
        status_label = "🟢 LIVE" if is_live else "🟡 SIM"
        st.image(
            img,
            use_container_width=True,
            caption=(
                f"{status_label}  |  "
                f"Fetch: {fetch_ms:.0f}ms  "
                + (f"|  YOLO: {inference_ms:.0f}ms  |  Detected: {det_count}" if detection_enabled else "")
            ),
        )
        
        # Bottom info bar
        info_cols = st.columns(3)
        with info_cols[0]:
            st.caption(f"📍 {camera.get('description', '')[:30]}")
        with info_cols[1]:
            st.caption(f"🔗 {camera.get('type','static').upper()}")
        with info_cols[2]:
            if anomalies:
                st.caption(f"🚨 {len(anomalies)} anomal{'y' if len(anomalies)==1 else 'ies'}")
            else:
                st.caption("✅ Normal")


def render_add_camera_form() -> Optional[dict]:
    """
    Render a form for users to add custom camera URLs.
    Returns a new camera dict if submitted, else None.
    """
    with st.expander("➕ Add Custom Camera Feed", expanded=False):
        with st.form("add_camera_form"):
            name = st.text_input("Camera Name", placeholder="e.g., My Street Cam")
            url = st.text_input("Feed URL", placeholder="http://example.com/cam.jpg or mjpeg URL")
            feed_type = st.selectbox("Feed Type", ["static", "mjpeg"])
            col1, col2 = st.columns(2)
            with col1:
                lat = st.number_input("Latitude", value=0.0, format="%.4f")
            with col2:
                lon = st.number_input("Longitude", value=0.0, format="%.4f")
            city = st.text_input("City / Location", placeholder="e.g., Paris, France")
            submitted = st.form_submit_button("Add Camera", type="primary")
            
            if submitted and name and url:
                return {
                    "id": f"custom_{int(time.time())}",
                    "name": name,
                    "url": url,
                    "type": feed_type,
                    "lat": lat,
                    "lon": lon,
                    "city": city,
                    "description": "User-added camera",
                }
    return None
