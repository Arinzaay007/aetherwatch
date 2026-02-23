"""
AetherWatch — Realistic Mock / Fallback Data Generator
Produces convincing synthetic data for all sources when APIs are unavailable.
All mock data is clearly labelled so users are never misled.
"""

import random
import math
import io
from datetime import datetime, timezone
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

# ── Seed data pools ──────────────────────────────────────────────────────────

_AIRPORTS = [
    ("KJFK", 40.6413, -73.7781, "New York"),
    ("KLAX", 33.9416, -118.4085, "Los Angeles"),
    ("KORD", 41.9742, -87.9073, "Chicago"),
    ("KDEN", 39.8561, -104.6737, "Denver"),
    ("KMIA", 25.7959, -80.2870, "Miami"),
    ("EGLL", 51.4700, -0.4543, "London"),
    ("LFPG", 49.0097,  2.5479, "Paris"),
    ("EDDF", 50.0379,  8.5622, "Frankfurt"),
    ("RJTT", 35.5533, 139.7811, "Tokyo"),
    ("OMDB", 25.2528,  55.3644, "Dubai"),
    ("YSSY", -33.9461, 151.1772, "Sydney"),
    ("SBGR", -23.4356, -46.4731, "São Paulo"),
    ("FAOR", -26.1392,  28.2460, "Johannesburg"),
    ("VHHH",  22.3080, 113.9185, "Hong Kong"),
    ("WSSS",   1.3644, 103.9915, "Singapore"),
]

_AIRCRAFT_TYPES = [
    "B738", "B739", "B77W", "B787", "B748",
    "A320", "A321", "A330", "A350", "A380",
    "E190", "CRJ9", "DH8D", "C172", "GLF6",
]

_AIRLINES = [
    ("UAL", "United Airlines"),
    ("DAL", "Delta Air Lines"),
    ("AAL", "American Airlines"),
    ("SWA", "Southwest Airlines"),
    ("BAW", "British Airways"),
    ("DLH", "Lufthansa"),
    ("AFR", "Air France"),
    ("UAE", "Emirates"),
    ("QFA", "Qantas"),
    ("SIA", "Singapore Airlines"),
    ("CPA", "Cathay Pacific"),
    ("ANA", "All Nippon Airways"),
]

_COUNTRIES = [
    "United States", "United Kingdom", "Germany", "France",
    "Japan", "Australia", "UAE", "Singapore", "Canada", "Brazil",
]


def _icao24() -> str:
    return f"{random.randint(0, 0xFFFFFF):06x}"


# ── Aircraft ─────────────────────────────────────────────────────────────────

def generate_mock_aircraft(count: int = 80) -> list[dict]:
    """Return a list of realistic fake aircraft state vectors."""
    aircraft: list[dict] = []
    now_ts = int(datetime.now(timezone.utc).timestamp())

    for _ in range(count):
        origin = random.choice(_AIRPORTS)
        dest = random.choice([a for a in _AIRPORTS if a[0] != origin[0]])

        # Position along great-circle approximation (linear for short-range demo)
        t = random.random()
        lat = origin[1] + t * (dest[1] - origin[1]) + random.gauss(0, 0.3)
        lon = origin[2] + t * (dest[2] - origin[2]) + random.gauss(0, 0.3)
        lat = max(-85.0, min(85.0, lat))
        lon = max(-180.0, min(180.0, lon))

        # Heading toward destination (rough)
        dlat = dest[1] - origin[1]
        dlon = dest[2] - origin[2]
        heading = math.degrees(math.atan2(dlon, dlat)) % 360

        airline_code, airline_name = random.choice(_AIRLINES)
        altitude = random.randint(15000, 42000)
        velocity = random.randint(350, 580)

        aircraft.append({
            "icao24": _icao24(),
            "callsign": f"{airline_code}{random.randint(100, 9999)}",
            "origin_country": random.choice(_COUNTRIES),
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "altitude_ft": altitude,
            "altitude_m": round(altitude * 0.3048),
            "velocity_kts": velocity,
            "velocity_ms": round(velocity * 0.5144, 1),
            "heading": round(heading, 1),
            "vertical_rate": random.randint(-1500, 1500),
            "aircraft_type": random.choice(_AIRCRAFT_TYPES),
            "squawk": f"{random.randint(0, 7777):04d}",
            "on_ground": False,
            "last_contact": now_ts,
            "is_mock": True,
        })

    return aircraft


# ── Camera Frames ─────────────────────────────────────────────────────────────

_SCENE_PALETTES = {
    "highway": {
        "sky": [(60, 100, 160), (100, 150, 200)],
        "road": [(70, 70, 70), (90, 90, 90)],
        "line_color": (220, 220, 180),
    },
    "urban": {
        "sky": [(50, 80, 120), (80, 120, 160)],
        "road": [(60, 60, 65), (80, 80, 85)],
        "line_color": (200, 200, 160),
    },
    "port": {
        "sky": [(40, 80, 130), (90, 140, 190)],
        "road": [(30, 60, 80), (50, 80, 100)],
        "line_color": (200, 230, 200),
    },
}

_VEHICLE_COLORS = [
    (200, 50,  50),  # red
    (50, 100, 200),  # blue
    (220, 220, 50),  # yellow
    (200, 200, 200), # white/silver
    (40, 160, 40),   # green
    (160, 50, 200),  # purple
    (240, 140, 30),  # orange
    (30,  30,  30),  # black
]


def generate_mock_camera_frame(
    camera_name: str = "CAM",
    width: int = 640,
    height: int = 360,
    scene: str = "highway",
) -> Image.Image:
    """
    Generate a convincing synthetic traffic-camera JPEG frame using PIL.
    Includes sky, road, buildings/structures, vehicles, timestamp overlay.
    """
    palette = _SCENE_PALETTES.get(scene, _SCENE_PALETTES["highway"])
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    sky_h = int(height * 0.38)
    road_start = sky_h

    # Sky gradient
    sky_lo, sky_hi = palette["sky"]
    for y in range(sky_h):
        t = y / max(sky_h - 1, 1)
        r = int(sky_lo[0] + t * (sky_hi[0] - sky_lo[0]))
        g = int(sky_lo[1] + t * (sky_hi[1] - sky_lo[1]))
        b = int(sky_lo[2] + t * (sky_hi[2] - sky_lo[2]))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Road gradient
    road_lo, road_hi = palette["road"]
    for y in range(road_start, height):
        t = (y - road_start) / max(height - road_start - 1, 1)
        r = int(road_lo[0] + t * (road_hi[0] - road_lo[0]))
        g = int(road_lo[1] + t * (road_hi[1] - road_lo[1]))
        b = int(road_lo[2] + t * (road_hi[2] - road_lo[2]))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Perspective road edges
    vp_x = width // 2
    draw.polygon(
        [(vp_x - 20, sky_h), (vp_x + 20, sky_h), (width, height), (0, height)],
        fill=road_lo,
    )

    # Lane markings
    lanes = 3
    for lane in range(1, lanes):
        x_top = vp_x + (lane - lanes // 2) * 20
        x_bot = lane * (width // lanes)
        for step in range(6):
            t0 = step / 6
            t1 = (step + 0.5) / 6
            y0 = int(road_start + t0 * (height - road_start))
            y1 = int(road_start + t1 * (height - road_start))
            x_0 = int(x_top + t0 * (x_bot - x_top))
            x_1 = int(x_top + t1 * (x_bot - x_top))
            draw.line([(x_0, y0), (x_1, y1)], fill=palette["line_color"], width=2)

    # Buildings silhouette
    rng = random.Random(hash(camera_name) % 10000)
    for i in range(14):
        bx = i * (width // 14)
        bw = rng.randint(28, 55)
        bh = rng.randint(35, 130)
        by = sky_h - bh
        shade = rng.randint(15, 45)
        draw.rectangle([bx, by, bx + bw, sky_h], fill=(shade, shade, shade + 10))
        # Windows
        for wy in range(by + 4, sky_h - 4, 11):
            for wx in range(bx + 3, bx + bw - 3, 9):
                lit = rng.random() > 0.35
                draw.rectangle([wx, wy, wx + 5, wy + 7],
                               fill=(255, 240, 150) if lit else (20, 20, 30))

    # Vehicles
    for _ in range(rng.randint(4, 10)):
        lane_frac = rng.uniform(0.05, 0.95)
        depth = rng.uniform(0.15, 0.90)
        vx = int(vp_x + (lane_frac - 0.5) * width * (0.2 + 0.8 * depth))
        vy = int(road_start + depth * (height - road_start))
        scale = 0.4 + 0.6 * depth
        vw = int(50 * scale)
        vh = int(24 * scale)
        color = rng.choice(_VEHICLE_COLORS)
        draw.rectangle([vx, vy - vh, vx + vw, vy], fill=color)
        # Windshield
        draw.rectangle([vx + vw - int(14 * scale), vy - vh + int(3 * scale),
                        vx + vw - int(3 * scale), vy - int(3 * scale)],
                       fill=(160, 210, 250))

    # Film grain
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-12, 12, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # HUD overlay — top bar
    draw.rectangle([0, 0, width, 20], fill=(0, 0, 0))
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    draw.text((5, 3), f"[MOCK] {camera_name}", fill=(0, 255, 80))
    draw.text((width - 155, 3), ts, fill=(255, 220, 0))

    # LIVE badge
    draw.rectangle([0, height - 20, 58, height], fill=(180, 0, 0))
    draw.text((6, height - 17), "● LIVE", fill=(255, 255, 255))

    # JPEG compression simulation
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    buf.seek(0)
    return Image.open(buf).copy()


# ── Satellite ─────────────────────────────────────────────────────────────────

def generate_mock_satellite_image(
    width: int = 512,
    height: int = 512,
    layer_name: str = "MODIS Terra",
) -> Image.Image:
    """Generate a plausible-looking mock satellite image tile."""
    img = Image.new("RGB", (width, height))
    arr = np.zeros((height, width, 3), dtype=np.uint8)

    # Base terrain noise
    for _ in range(3):
        scale = random.randint(4, 16)
        noise = np.random.randint(0, 80, (height // scale + 1, width // scale + 1, 3))
        noise_up = np.kron(noise, np.ones((scale, scale, 1), dtype=np.uint8))
        arr = np.clip(arr + noise_up[:height, :width], 0, 255).astype(np.uint8)

    # Green-ish land base
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 40, 0, 255)

    # Cloud patches
    for _ in range(random.randint(3, 8)):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        cr = random.randint(20, 100)
        for y in range(max(0, cy - cr), min(height, cy + cr)):
            for x in range(max(0, cx - cr), min(width, cx + cr)):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if d < cr:
                    alpha = 1 - (d / cr) ** 2
                    arr[y, x] = np.clip(arr[y, x] + int(alpha * 200), 0, 255)

    img = Image.fromarray(arr.astype(np.uint8))
    draw = ImageDraw.Draw(img)
    ts = datetime.now().strftime("%Y-%m-%d")
    draw.rectangle([0, 0, width, 18], fill=(0, 0, 0))
    draw.text((4, 2), f"[MOCK] {layer_name}  |  {ts}", fill=(0, 220, 255))
    return img


# ── Alerts ───────────────────────────────────────────────────────────────────

_ALERT_TEMPLATES: list[tuple[str, str, str]] = [
    ("INFO",    "✈",  "Aircraft {cs} at {alt}ft, {spd}kts — entering monitored zone"),
    ("WARNING", "⚠",  "Stopped vehicle cluster detected on {cam} — {n} vehicles stationary"),
    ("INFO",    "🛰",  "OpenSky refresh: {n} aircraft in current bounding box"),
    ("WARNING", "🔴", "High aircraft density: {n} flights within 50nm of {apt}"),
    ("INFO",    "🖼",  "NASA GIBS imagery updated: {layer}"),
    ("ERROR",   "📷", "Camera feed timeout: {cam} — falling back to mock frame"),
    ("INFO",    "🤖", "YOLO: {n_v} vehicles, {n_p} pedestrians detected in frame"),
    ("WARNING", "✈",  "Low-altitude flight: {cs} at only {alt}ft over {city}"),
    ("INFO",    "🌐", "API rate limit OK — next window in {s}s"),
    ("WARNING", "🚗", "Unusual traffic density on {cam}: {n}× normal congestion"),
]

_CALLSIGNS = [f"{a}{n}" for a in ["UAL","DAL","AAL","BAW","DLH"] for n in range(100, 200)]
_CAMS = ["NYC-001", "CHI-042", "LAX-07", "LHR-12", "MIA-33", "SEA-09"]
_APTS = ["JFK", "LAX", "ORD", "LHR", "CDG", "DXB"]
_LAYERS = ["MODIS Terra True Color", "VIIRS Day/Night Band", "GOES-East Visible"]
_CITIES = ["Manhattan", "Chicago Loop", "Downtown LA", "Heathrow Corridor"]


def generate_mock_alert() -> dict:
    """Return a single realistic mock alert dictionary."""
    level, icon, template = random.choice(_ALERT_TEMPLATES)
    msg = template.format(
        cs=random.choice(_CALLSIGNS),
        alt=random.randint(800, 42000),
        spd=random.randint(120, 600),
        cam=random.choice(_CAMS),
        n=random.randint(2, 60),
        n_v=random.randint(1, 20),
        n_p=random.randint(0, 12),
        apt=random.choice(_APTS),
        layer=random.choice(_LAYERS),
        city=random.choice(_CITIES),
        s=random.randint(5, 30),
    )
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "icon": icon,
        "message": msg,
    }
