"""
AetherWatch — Traffic Camera Data Source
Supports: Static JPEG (polling), MJPEG (frame grab), URL fallback
Mock: Generates realistic-looking synthetic camera frames when feeds are offline.

LEGAL NOTE: Only access publicly accessible camera feeds. Do not circumvent
authentication or access private cameras. Respect each city/operator's terms of use.
"""

import io
import time
import random
import colorsys
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional
from utils.logger import get_logger
from config import settings

log = get_logger(__name__)

# Connection timeout for camera URLs
CAMERA_TIMEOUT = 6  # seconds

# Per-camera state: tracks offline status to reduce spam logging
_camera_status: dict[str, dict] = {}


def fetch_camera_frame(camera: dict) -> tuple[Optional[Image.Image], bool]:
    """
    Fetch a single frame from a camera feed.
    
    Args:
        camera: Camera definition dict from settings.PUBLIC_CAMERAS
    
    Returns:
        (PIL Image or None, is_live) where is_live=False means mock used
    """
    if settings.FORCE_MOCK_DATA:
        return _generate_mock_frame(camera), False

    cam_id = camera["id"]
    url = camera["url"]
    stream_type = camera.get("type", "static")
    
    try:
        if stream_type == "mjpeg":
            img = _fetch_mjpeg_frame(url)
        else:
            img = _fetch_static_frame(url)
        
        if img:
            _camera_status[cam_id] = {"online": True, "last_success": time.time(), "fail_count": 0}
            return img, True
    
    except Exception as e:
        status = _camera_status.get(cam_id, {"fail_count": 0})
        status["fail_count"] = status.get("fail_count", 0) + 1
        status["online"] = False
        _camera_status[cam_id] = status
        
        # Only log warning every 5 failures to avoid spam
        if status["fail_count"] % 5 == 1:
            log.warning(f"Camera '{camera['name']}' offline: {type(e).__name__} — using mock frame")
    
    return _generate_mock_frame(camera), False


def _fetch_static_frame(url: str) -> Optional[Image.Image]:
    """Fetch a static JPEG/PNG image from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AetherWatch/1.0)",
        "Cache-Control": "no-cache",
    }
    resp = requests.get(url, timeout=CAMERA_TIMEOUT, headers=headers, stream=True)
    resp.raise_for_status()
    
    # Check content type
    content_type = resp.headers.get("Content-Type", "")
    if "image" not in content_type and "jpeg" not in content_type:
        raise ValueError(f"Unexpected content type: {content_type}")
    
    img = Image.open(io.BytesIO(resp.content))
    img = img.convert("RGB")
    return img


def _fetch_mjpeg_frame(url: str) -> Optional[Image.Image]:
    """
    Grab a single frame from an MJPEG stream.
    Reads until we find a complete JPEG frame (starts with FF D8, ends with FF D9).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AetherWatch/1.0)",
    }
    with requests.get(url, timeout=CAMERA_TIMEOUT, headers=headers, stream=True) as resp:
        resp.raise_for_status()
        
        buffer = b""
        bytes_read = 0
        max_bytes = 1_000_000  # 1MB limit per frame
        
        for chunk in resp.iter_content(chunk_size=4096):
            buffer += chunk
            bytes_read += len(chunk)
            
            # Look for JPEG start (FF D8) and end (FF D9)
            start = buffer.find(b'\xff\xd8')
            end = buffer.find(b'\xff\xd9', start + 2) if start != -1 else -1
            
            if start != -1 and end != -1:
                jpeg_data = buffer[start:end + 2]
                img = Image.open(io.BytesIO(jpeg_data)).convert("RGB")
                return img
            
            if bytes_read > max_bytes:
                raise ValueError("MJPEG frame exceeded 1MB limit")
    
    return None


def get_all_cameras() -> list[dict]:
    """Return the full list of configured public cameras."""
    return settings.PUBLIC_CAMERAS


def get_camera_status() -> dict[str, dict]:
    """Return status info for all cameras."""
    return _camera_status


# ── Mock Frame Generator ──────────────────────────────────────────────────────

# Persistent state per camera for continuous simulation
_mock_state: dict[str, dict] = {}


def _generate_mock_frame(camera: dict, width: int = 640, height: int = 360) -> Image.Image:
    """
    Generate a realistic-looking synthetic traffic camera frame.
    Creates a simulated road/street scene with moving vehicles.
    The scene evolves over time for animation effect.
    """
    cam_id = camera["id"]
    now = time.time()
    
    # Initialise state for this camera
    if cam_id not in _mock_state:
        seed = hash(cam_id) % 10000
        _mock_state[cam_id] = {
            "seed": seed,
            "vehicles": _init_mock_vehicles(seed, width, height),
            "time_of_day": random.choice([6, 8, 10, 12, 14, 16, 18, 20]),
        }
    
    state = _mock_state[cam_id]
    
    # Update vehicle positions
    state["vehicles"] = _update_mock_vehicles(state["vehicles"], width, height, now)
    
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    
    # Sky gradient based on time of day
    tod = state["time_of_day"]
    _draw_sky(draw, width, height, tod)
    
    # Road / scene
    _draw_road_scene(draw, width, height)
    
    # Vehicles
    for v in state["vehicles"]:
        _draw_vehicle(draw, v)
    
    # Overlay: camera info banner
    _draw_hud(draw, camera, width, height)
    
    # Slight blur for realism
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    return img


def _init_mock_vehicles(seed: int, width: int, height: int) -> list[dict]:
    """Initialise random vehicles for the mock scene."""
    rng = random.Random(seed)
    vehicles = []
    colors = ["#c0392b", "#2980b9", "#27ae60", "#f39c12", "#8e44ad", "#ecf0f1", "#2c3e50"]
    
    for i in range(rng.randint(4, 12)):
        vehicles.append({
            "x": rng.uniform(50, width - 50),
            "y": rng.uniform(height * 0.55, height * 0.85),
            "speed": rng.uniform(0.5, 2.5),
            "color": rng.choice(colors),
            "type": rng.choice(["car", "car", "car", "truck", "bus"]),
            "lane": rng.randint(0, 2),
            "phase": rng.uniform(0, 100),
        })
    return vehicles


def _update_mock_vehicles(vehicles: list, width: int, height: int, t: float) -> list:
    """Update vehicle positions (simple horizontal scroll per lane)."""
    for v in vehicles:
        direction = 1 if v["lane"] % 2 == 0 else -1
        v["x"] += direction * v["speed"] * 0.5
        # Wrap around edges
        if v["x"] > width + 80:
            v["x"] = -80
        elif v["x"] < -80:
            v["x"] = width + 80
    return vehicles


def _draw_sky(draw: ImageDraw.Draw, width: int, height: int, hour: int):
    """Draw a sky gradient appropriate for the time of day."""
    if 5 <= hour < 7:          # dawn
        top_col, bot_col = (255, 140, 0), (255, 200, 100)
    elif 7 <= hour < 18:       # day
        top_col, bot_col = (30, 100, 200), (135, 185, 235)
    elif 18 <= hour < 20:      # dusk
        top_col, bot_col = (200, 70, 30), (255, 160, 80)
    else:                       # night
        top_col, bot_col = (5, 5, 20), (20, 20, 60)
    
    sky_h = int(height * 0.45)
    for y in range(sky_h):
        ratio = y / sky_h
        r = int(top_col[0] + (bot_col[0] - top_col[0]) * ratio)
        g = int(top_col[1] + (bot_col[1] - top_col[1]) * ratio)
        b = int(top_col[2] + (bot_col[2] - top_col[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_road_scene(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a basic road/street perspective."""
    road_top = int(height * 0.45)
    
    # Ground/sidewalk
    draw.rectangle([0, road_top, width, height], fill=(80, 80, 80))
    
    # Road surface (slightly darker)
    road_y = int(height * 0.5)
    draw.rectangle([0, road_y, width, height], fill=(55, 55, 55))
    
    # Lane markings
    dash_w, dash_h, gap = 40, 4, 30
    y_lanes = [int(height * 0.63), int(height * 0.75)]
    for lane_y in y_lanes:
        for x in range(0, width, dash_w + gap):
            draw.rectangle([x, lane_y, x + dash_w, lane_y + dash_h], fill=(220, 220, 140))
    
    # Horizon line / buildings silhouette
    bldg_y = int(height * 0.45)
    bldg_colors = [(40, 40, 50), (50, 50, 65), (35, 35, 45)]
    bldg_seed = 42
    rng = random.Random(bldg_seed)
    x = 0
    while x < width:
        bw = rng.randint(30, 80)
        bh = rng.randint(30, 100)
        by = bldg_y - bh
        draw.rectangle([x, by, x + bw, bldg_y], fill=rng.choice(bldg_colors))
        # windows
        for wy in range(by + 5, bldg_y - 5, 12):
            for wx in range(x + 4, x + bw - 4, 8):
                if rng.random() > 0.4:
                    wc = (255, 240, 150) if rng.random() > 0.3 else (50, 50, 80)
                    draw.rectangle([wx, wy, wx + 4, wy + 6], fill=wc)
        x += bw + rng.randint(2, 10)


def _draw_vehicle(draw: ImageDraw.Draw, v: dict):
    """Draw a simple vehicle on the road."""
    x, y = int(v["x"]), int(v["y"])
    vtype = v["type"]
    color = v["color"]
    
    if vtype == "car":
        w, h = 30, 14
    elif vtype == "truck":
        w, h = 50, 18
    else:  # bus
        w, h = 55, 20
    
    # Body
    draw.rectangle([x, y - h, x + w, y], fill=color)
    # Windows
    draw.rectangle([x + 4, y - h + 2, x + w - 4, y - h + 8], fill=(150, 200, 255))
    # Wheels
    for wx in [x + 5, x + w - 8]:
        draw.ellipse([wx, y - 3, wx + 6, y + 3], fill=(20, 20, 20))


def _draw_hud(draw: ImageDraw.Draw, camera: dict, width: int, height: int):
    """Draw camera HUD overlay (name, timestamp, MOCK indicator)."""
    # Semi-transparent top bar
    draw.rectangle([0, 0, width, 28], fill=(0, 0, 0))
    
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    name = camera.get("name", "Unknown Camera")
    
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    
    draw.text((6, 6), f"📷 {name}  |  {ts}  |  ⚠ SIMULATED FEED", fill=(255, 60, 60), font=font)
    
    # Bottom: city + status bar
    draw.rectangle([0, height - 24, width, height], fill=(0, 0, 0))
    city = camera.get("city", "")
    desc = camera.get("description", "")
    draw.text((6, height - 18), f"📍 {city} — {desc}", fill=(200, 200, 200), font=font)
