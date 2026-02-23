"""
AetherWatch — NASA Satellite Imagery (GIBS WMS)
Uses NASA's Global Imagery Browse Services (GIBS) — no API key required!
Documentation: https://wiki.earthdata.nasa.gov/display/GIBS

Provides true-color, thermal, and other satellite imagery layers via
the OGC Web Map Service (WMS) standard.
"""

import io
import math
import datetime
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from utils.logger import get_logger
from utils.cache import cached
from utils.alerts import dispatch_alert, AlertLevel
from config import settings

log = get_logger(__name__)


def fetch_gibs_image(
    layer_name: str,
    date: Optional[datetime.date] = None,
    bbox: tuple = (-180, -90, 180, 90),
    width: int = 800,
    height: int = 400,
) -> tuple[Optional[Image.Image], bool]:
    """
    Fetch a satellite image tile from NASA GIBS WMS.
    
    Args:
        layer_name: GIBS layer identifier (from settings.SATELLITE_LAYERS values)
        date:       Image date (defaults to yesterday — MODIS has ~1 day lag)
        bbox:       (west, south, east, north) in decimal degrees
        width:      Output image width in pixels
        height:     Output image height in pixels
    
    Returns:
        (PIL Image, is_live) — is_live=False means mock/fallback was used
    """
    if date is None:
        # GIBS has ~1-2 day latency for most products
        date = datetime.date.today() - datetime.timedelta(days=2)
    
    if settings.FORCE_MOCK_DATA:
        return _generate_mock_satellite(layer_name, bbox, width, height), False
    
    date_str = date.strftime("%Y-%m-%d")
    
    # Build WMS request parameters
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "LAYERS": layer_name,
        "STYLES": "",
        "SRS": "EPSG:4326",
        "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "FORMAT": "image/jpeg",
        "TRANSPARENT": "FALSE",
        "TIME": date_str,
    }
    
    try:
        log.info(f"Fetching NASA GIBS layer '{layer_name}' for {date_str}")
        resp = requests.get(
            settings.NASA_GIBS_WMS,
            params=params,
            timeout=15,
            headers={"User-Agent": "AetherWatch/1.0 (scientific/educational use)"},
        )
        resp.raise_for_status()
        
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type:
            # GIBS returns XML error if layer/date not available
            log.warning(f"GIBS returned non-image response ({content_type}) — using mock")
            return _generate_mock_satellite(layer_name, bbox, width, height), False
        
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        # Annotate with metadata
        _annotate_satellite_image(img, layer_name, date_str, bbox)
        
        log.info(f"GIBS image fetched: {img.size}")
        return img, True
    
    except Exception as e:
        log.error(f"Failed to fetch GIBS image: {e}")
        dispatch_alert(AlertLevel.WARNING, "Satellite API", f"NASA GIBS unavailable: {e}. Using mock imagery.")
        return _generate_mock_satellite(layer_name, bbox, width, height), False


def get_available_dates(layer_name: str, count: int = 10) -> list[datetime.date]:
    """
    Return the most recent available dates for a GIBS layer.
    For most MODIS/VIIRS products, data is available within 1-2 days.
    """
    today = datetime.date.today()
    return [today - datetime.timedelta(days=i) for i in range(1, count + 1)]


@cached(ttl=settings.CACHE_TTL_SATELLITE)
def fetch_region_image(layer_name: str, date_str: str, region: str) -> tuple[Optional[Image.Image], bool]:
    """
    Fetch a pre-defined region. Cached aggressively as satellite data doesn't change.
    """
    regions = {
        "Global":          (-180, -90, 180, 90),
        "North America":   (-170, 15, -50, 80),
        "Europe":          (-30, 30, 45, 75),
        "Asia Pacific":    (60, -15, 180, 60),
        "Africa":          (-25, -40, 60, 40),
        "Middle East":     (25, 10, 75, 45),
        "South America":   (-85, -60, -30, 15),
        "Arctic":          (-180, 60, 180, 90),
    }
    bbox = regions.get(region, (-180, -90, 180, 90))
    date = datetime.date.fromisoformat(date_str)
    
    # Adjust width/height aspect ratio for bbox
    lon_span = bbox[2] - bbox[0]
    lat_span = bbox[3] - bbox[1]
    ratio = lon_span / lat_span if lat_span > 0 else 2
    width = 800
    height = max(200, int(width / ratio))
    
    return fetch_gibs_image(layer_name, date, bbox, width, height)


def _annotate_satellite_image(img: Image.Image, layer_name: str, date_str: str, bbox: tuple):
    """Add metadata annotation to the satellite image."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    
    # Top banner
    draw.rectangle([0, 0, w, 22], fill=(0, 0, 0, 200))
    draw.text(
        (4, 4),
        f"🛰 NASA GIBS | Layer: {layer_name} | Date: {date_str} | "
        f"BBox: {bbox[0]:.1f},{bbox[1]:.1f} → {bbox[2]:.1f},{bbox[3]:.1f}",
        fill=(100, 200, 100),
        font=font,
    )


def _generate_mock_satellite(
    layer_name: str, bbox: tuple, width: int, height: int
) -> Image.Image:
    """
    Generate a plausible-looking mock satellite image when NASA GIBS is unavailable.
    Renders a stylised Earth map with ocean/land colours.
    """
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    pixels = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Choose colour scheme based on layer type
    if "Night" in layer_name or "NightTime" in layer_name:
        bg_color = (5, 5, 15)       # space black
        land_color = (255, 200, 50) # city lights yellow
        ocean_color = (5, 5, 15)
    elif "Temperature" in layer_name or "Temp" in layer_name:
        bg_color = (0, 50, 100)
        land_color = (200, 100, 50)
        ocean_color = (0, 80, 150)
    elif "Snow" in layer_name:
        bg_color = (50, 100, 180)
        land_color = (230, 230, 255)
        ocean_color = (30, 80, 160)
    else:
        # Default: true-colour-ish
        bg_color = (30, 80, 160)    # ocean blue
        land_color = (80, 130, 60)  # land green
        ocean_color = (20, 60, 140)
    
    # Fill with ocean
    pixels[:, :] = ocean_color
    
    # Generate simplified land masses using noise
    np.random.seed(42)
    noise = np.random.rand(height // 4, width // 4)
    from PIL import Image as PILImage
    noise_img = PILImage.fromarray((noise * 255).astype(np.uint8), mode="L")
    noise_img = noise_img.resize((width, height), PILImage.BILINEAR)
    noise_arr = np.array(noise_img)
    
    threshold = 100
    land_mask = noise_arr > threshold
    
    # Apply colours
    for c in range(3):
        pixels[:, :, c] = np.where(land_mask, land_color[c], ocean_color[c])
    
    # Add some texture variation
    variation = (np.random.rand(height, width) * 20 - 10).astype(np.int16)
    pixels = np.clip(pixels.astype(np.int16) + variation[..., np.newaxis], 0, 255).astype(np.uint8)
    
    mock_img = PILImage.fromarray(pixels, "RGB")
    draw = ImageDraw.Draw(mock_img)
    
    # Mock annotation banner
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    
    draw.rectangle([0, 0, width, 22], fill=(0, 0, 0))
    draw.text(
        (4, 4),
        f"🛰 SIMULATED IMAGERY | Layer: {layer_name} | "
        f"BBox: {bbox[0]:.0f},{bbox[1]:.0f}→{bbox[2]:.0f},{bbox[3]:.0f} | Connect NASA GIBS for real data",
        fill=(255, 100, 100),
        font=font,
    )
    
    return mock_img
