"""
AetherWatch — Interactive Map View
Builds a Folium/Leaflet map with:
- Aircraft positions (with directional airplane icons)
- Traffic camera locations (clickable markers)
- NASA GIBS satellite overlay via WMS tile layer
"""

import math
import folium
import folium.plugins
from folium import IFrame
from typing import Optional
from data_sources.aviation import Aircraft
from config import settings

# ── Airplane SVG icon factory ─────────────────────────────────────────────────

def _airplane_svg(heading: float, color: str = "#58a6ff", size: int = 18) -> str:
    """Generate a rotated SVG airplane icon for the given heading."""
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
         width="{size}" height="{size}"
         style="transform: rotate({heading}deg); display:inline-block">
      <path fill="{color}" d="M21 16v-2l-8-5V3.5A1.5 1.5 0 0 0 11.5 2
                              1.5 1.5 0 0 0 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/>
    </svg>"""


def _make_airplane_icon(heading: float, on_ground: bool = False, is_mock: bool = False) -> folium.DivIcon:
    """Create a DivIcon for an aircraft marker."""
    if is_mock:
        color = "#d29922"   # yellow for mock
    elif on_ground:
        color = "#8b949e"   # grey for ground
    else:
        color = "#58a6ff"   # blue for airborne
    
    svg = _airplane_svg(heading, color)
    return folium.DivIcon(
        html=svg,
        icon_size=(18, 18),
        icon_anchor=(9, 9),
    )


# ── Camera marker ─────────────────────────────────────────────────────────────

def _camera_icon(is_online: bool = True) -> folium.DivIcon:
    color = "#3fb950" if is_online else "#f85149"
    html = f"""<div style="font-size:16px; color:{color}; 
                text-shadow: 0 0 4px black;">📷</div>"""
    return folium.DivIcon(html=html, icon_size=(20, 20), icon_anchor=(10, 10))


# ── Main map builder ──────────────────────────────────────────────────────────

def build_map(
    aircraft_list: list[Aircraft],
    cameras: list[dict],
    tile_style: str = settings.DEFAULT_MAP_TILE,
    show_aircraft: bool = True,
    show_cameras: bool = True,
    show_satellite_overlay: bool = False,
    satellite_layer: str = "",
    satellite_date: str = "",
    camera_status: Optional[dict] = None,
    cluster_aircraft: bool = True,
) -> folium.Map:
    """
    Build and return a fully configured Folium map.
    
    Args:
        aircraft_list:           List of Aircraft objects to plot
        cameras:                 List of camera dicts to plot
        tile_style:              Base map tile style name
        show_aircraft:           Toggle aircraft markers
        show_cameras:            Toggle camera markers
        show_satellite_overlay:  Add NASA GIBS WMS overlay
        satellite_layer:         GIBS layer identifier string
        satellite_date:          ISO date string for satellite data
        camera_status:           Dict of camera_id → status dict
        cluster_aircraft:        Use MarkerCluster for performance
    
    Returns:
        Configured folium.Map instance
    """
    # ── Base map
    tiles = settings.MAP_TILES.get(tile_style, "CartoDB dark_matter")
    
    m = folium.Map(
        location=settings.DEFAULT_MAP_CENTER,
        zoom_start=settings.DEFAULT_MAP_ZOOM,
        tiles=tiles,
        prefer_canvas=True,   # Better performance for many markers
    )
    
    # ── Add tile layer options
    for name, tile_url in settings.MAP_TILES.items():
        if name != tile_style:
            if tile_url.startswith("http"):
                folium.TileLayer(
                    tiles=tile_url,
                    attr="Esri World Imagery",
                    name=name,
                    overlay=False,
                ).add_to(m)
            else:
                folium.TileLayer(tiles=tile_url, name=name, overlay=False).add_to(m)
    
    # ── NASA GIBS WMS Overlay
    if show_satellite_overlay and satellite_layer:
        try:
            wms_url = settings.NASA_GIBS_WMS
            date_param = satellite_date or ""
            folium.WmsTileLayer(
                url=wms_url,
                layers=satellite_layer,
                fmt="image/jpeg",
                transparent=True,
                name=f"Satellite: {satellite_layer[:30]}",
                overlay=True,
                control=True,
                time=date_param,
                opacity=0.6,
            ).add_to(m)
        except Exception:
            pass  # WMS overlay is best-effort
    
    # ── Aircraft markers
    if show_aircraft and aircraft_list:
        if cluster_aircraft and len(aircraft_list) > 100:
            aircraft_group = folium.plugins.MarkerCluster(
                name="Aircraft",
                overlay=True,
                control=True,
                options={"maxClusterRadius": 40, "disableClusteringAtZoom": 6},
            )
        else:
            aircraft_group = folium.FeatureGroup(name="Aircraft", show=True)
        
        for ac in aircraft_list:
            if not (-90 <= ac.latitude <= 90 and -180 <= ac.longitude <= 180):
                continue
            
            icon = _make_airplane_icon(ac.heading, ac.on_ground, ac.is_mock)
            popup = folium.Popup(IFrame(ac.popup_html, width=220, height=200), max_width=220)
            tooltip = folium.Tooltip(
                f"{ac.callsign} | {ac.altitude_ft:,.0f}ft | {ac.velocity_kts:.0f}kts",
                sticky=True,
            )
            
            folium.Marker(
                location=[ac.latitude, ac.longitude],
                icon=icon,
                popup=popup,
                tooltip=tooltip,
            ).add_to(aircraft_group)
        
        aircraft_group.add_to(m)
    
    # ── Camera markers
    if show_cameras and cameras:
        cam_group = folium.FeatureGroup(name="Traffic Cameras", show=True)
        
        for cam in cameras:
            if cam_status := (camera_status or {}).get(cam["id"], {}):
                is_online = cam_status.get("online", False)
                status_str = "🟢 Online" if is_online else "🔴 Offline (Mock)"
            else:
                is_online = None
                status_str = "⚪ Not checked"
            
            popup_html = f"""
            <div style='font-family:monospace; min-width:180px'>
              <b>📷 {cam['name']}</b><br>
              <hr style='margin:4px 0'>
              City: {cam['city']}<br>
              Type: {cam.get('type','static').upper()}<br>
              Status: {status_str}<br>
              <small>{cam.get('description','')}</small>
            </div>"""
            
            folium.Marker(
                location=[cam["location"][0] if "location" in cam else cam["lat"], cam["location"][1] if "location" in cam else cam["lon"]],
                icon=_camera_icon(is_online is True),
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=folium.Tooltip(cam["name"], sticky=True),
            ).add_to(cam_group)
        
        cam_group.add_to(m)
    
    # ── Map controls
    folium.plugins.Fullscreen(
        position="topright",
        title="Fullscreen",
        title_cancel="Exit Fullscreen",
    ).add_to(m)
    
    folium.plugins.MiniMap(toggle_display=True, tile_layer="CartoDB positron").add_to(m)
    
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    
    # ── Stats legend
    live_count = sum(1 for ac in aircraft_list if not ac.is_mock)
    mock_count = sum(1 for ac in aircraft_list if ac.is_mock)
    
    legend_html = f"""
    <div style="position:fixed; bottom:30px; left:10px; z-index:1000;
                background:#161b22; border:1px solid #30363d; border-radius:8px;
                padding:10px; font-family:monospace; font-size:12px; color:#e6edf3">
      <b>🛰️ AetherWatch</b><br>
      ✈️ Aircraft: <b>{len(aircraft_list)}</b>
        {'(live)' if live_count == len(aircraft_list) else f'({live_count} live, {mock_count} simulated)'}<br>
      📷 Cameras: <b>{len(cameras)}</b><br>
      <span style="color:#d29922">■</span> Simulated &nbsp;
      <span style="color:#58a6ff">■</span> Live &nbsp;
      <span style="color:#8b949e">■</span> Ground
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m
