"""
AetherWatch — Satellite Imagery Viewer
Renders the NASA GIBS satellite imagery panel with layer selector,
date picker, region selector, and optional YOLO detection.
"""

import datetime
import streamlit as st
from PIL import Image
from data_sources.satellite import fetch_gibs_image, fetch_region_image, get_available_dates
from config import settings


def render_satellite_panel(detector=None, detection_enabled: bool = False):
    """
    Render the full satellite imagery viewer panel.
    Includes layer picker, date selector, region selector, and image display.
    """
    st.subheader("🛰️ Satellite Imagery — NASA GIBS")
    
    # ── Controls row
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])
    
    with ctrl1:
        layer_display_name = st.selectbox(
            "Imagery Layer",
            list(settings.SATELLITE_LAYERS.keys()),
            index=0,
            help="Select the satellite data product to display",
        )
        layer_id = settings.SATELLITE_LAYERS[layer_display_name]
    
    with ctrl2:
        available_dates = get_available_dates(layer_id)
        date_options = [d.strftime("%Y-%m-%d") for d in available_dates]
        selected_date_str = st.selectbox(
            "Date",
            date_options,
            help="Most layers have 1–2 day latency",
        )
    
    with ctrl3:
        region = st.selectbox(
            "Region",
            ["Global", "North America", "Europe", "Asia Pacific",
             "Africa", "Middle East", "South America", "Arctic"],
        )
    
    # Custom bounding box expander
    with st.expander("🔲 Custom Bounding Box", expanded=False):
        bbox_cols = st.columns(4)
        with bbox_cols[0]:
            west = st.number_input("West (lon)", value=-180.0, min_value=-180.0, max_value=180.0)
        with bbox_cols[1]:
            south = st.number_input("South (lat)", value=-90.0, min_value=-90.0, max_value=90.0)
        with bbox_cols[2]:
            east = st.number_input("East (lon)", value=180.0, min_value=-180.0, max_value=180.0)
        with bbox_cols[3]:
            north = st.number_input("North (lat)", value=90.0, min_value=-90.0, max_value=90.0)
        use_custom_bbox = st.checkbox("Use custom bounding box")
    
    # ── Fetch imagery
    with st.spinner(f"Loading {layer_display_name} for {selected_date_str}…"):
        if use_custom_bbox:
            bbox = (west, south, east, north)
            img, is_live = fetch_gibs_image(layer_id, datetime.date.fromisoformat(selected_date_str), bbox)
        else:
            img, is_live = fetch_region_image(layer_id, selected_date_str, region)
    
    if img is None:
        st.error("❌ Failed to load satellite imagery. Check your connection or try a different date.")
        return
    
    # ── Optional YOLO detection on satellite image
    if detection_enabled and detector is not None:
        try:
            result = detector.detect(img, camera_id=f"sat_{layer_id}")
            if result.annotated_image:
                img = result.annotated_image
            if result.anomalies:
                for anomaly in result.anomalies:
                    st.warning(f"🛰️ Satellite Anomaly: {anomaly}")
        except Exception:
            pass
    
    # ── Display
    status = "🟢 LIVE NASA DATA" if is_live else "🟡 SIMULATED IMAGERY"
    st.image(img, use_container_width=True, caption=f"{status} | {layer_display_name} | {selected_date_str} | {region}")
    
    # ── Layer info
    layer_info = {
        "True Color (MODIS Terra)": "Daily true-color composite from MODIS Terra satellite. Shows clouds, land cover, ocean colour.",
        "True Color (MODIS Aqua)": "Daily true-color composite from MODIS Aqua satellite. Complements Terra's coverage.",
        "VIIRS Night Lights": "Nighttime lights from VIIRS/SNPP. Shows city lights, gas flares, fishing vessels.",
        "Sea Surface Temperature": "Ocean surface temperature from GHRSST. Reveals currents and thermal patterns.",
        "Snow Ice Cover": "Daily snow and ice extent from MODIS. Important for climate monitoring.",
        "Aerosol (Dust/Smoke)": "Atmospheric aerosol optical depth. Shows dust storms, smoke, and pollution.",
        "Vegetation (NDVI)": "Normalized Difference Vegetation Index. Green = healthy vegetation.",
        "Land Surface Temp": "Daytime land surface temperature. Reveals urban heat islands, drought.",
    }
    
    if layer_display_name in layer_info:
        st.caption(f"ℹ️ {layer_info[layer_display_name]}")
    
    st.caption(
        "Data source: NASA Earth Observing System Data and Information System (EOSDIS) — "
        "[Global Imagery Browse Services (GIBS)](https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs)"
    )
