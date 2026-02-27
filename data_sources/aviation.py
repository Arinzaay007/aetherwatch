"""
AetherWatch — Aviation Data Source
Primary:  airplanes.live  (free, no auth, wide radius grid)
Fallback: OpenSky Network via OAuth2 client credentials
Last:     Mock data
"""

import time
import requests
from requests.auth import HTTPBasicAuth

from config.settings import (
    OPENSKY_USERNAME,
    OPENSKY_PASSWORD,
    FR24_API_TOKEN,
    FORCE_MOCK_DATA,
    OPENSKY_CACHE_TTL,
)
from utils.cache import aviation_cache
from utils.logger import logger
from utils.mock_data import generate_mock_aircraft

OPENSKY_TOKEN_URL  = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"

# Read OAuth2 credentials from Streamlit secrets (same place as username/password)
import streamlit as st

def _get_opensky_oauth_token() -> str | None:
    """Get an OAuth2 bearer token using client credentials flow."""
    try:
        client_id     = st.secrets.get("OPENSKY_CLIENT_ID", "")
        client_secret = st.secrets.get("OPENSKY_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            logger.warning("OpenSky OAuth2: OPENSKY_CLIENT_ID or OPENSKY_CLIENT_SECRET not set in secrets")
            return None

        resp = requests.post(
            OPENSKY_TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("OpenSky token request failed: {}", resp.status_code)
            return None

        token = resp.json().get("access_token")
        if token:
            logger.info("OpenSky OAuth2 token obtained")
        return token
    except Exception as e:
        logger.warning("OpenSky OAuth2 token error: {}", e)
        return None


# Wide-coverage grid for airplanes.live (6000nm radius per point)
_GLOBAL_GRID = [
    (40,  -40),
    (40,  140),
    (-30, -60),
    (-30,  120),
]

_session = requests.Session()
_session.headers.update({"User-Agent": "AetherWatch/1.0"})


def _parse_v2_aircraft(ac: dict) -> dict | None:
    try:
        lat = ac.get("lat")
        lon = ac.get("lon")
        if lat is None or lon is None:
            return None
        alt_baro = ac.get("alt_baro", 0)
        if alt_baro == "ground":
            alt_baro = 0
            on_ground = True
        else:
            on_ground = False
            try:
                alt_baro = float(alt_baro or 0)
            except Exception:
                alt_baro = 0

        return {
            "icao24":         ac.get("hex", ""),
            "callsign":       (ac.get("flight") or "UNKNOWN").strip(),
            "origin_country": ac.get("r", ""),
            "latitude":       float(lat),
            "longitude":      float(lon),
            "altitude_ft":    float(alt_baro),
            "altitude_m":     float(alt_baro) * 0.3048,
            "velocity_kts":   float(ac.get("gs", 0) or 0),
            "heading":        float(ac.get("track", 0) or 0),
            "vertical_rate":  float(ac.get("baro_rate", 0) or 0),
            "on_ground":      on_ground,
            "squawk":         ac.get("squawk", "----"),
            "aircraft_type":  ac.get("t", ""),
            "last_contact":   int(time.time()),
            "is_mock":        False,
        }
    except Exception:
        return None


def _fetch_airplanes_live() -> list[dict] | None:
    seen = set()
    aircraft = []
    success = 0

    for lat, lon in _GLOBAL_GRID:
        url = f"https://api.airplanes.live/v2/point/{lat}/{lon}/6000"
        try:
            resp = _session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.warning("airplanes.live {}/{} status {}", lat, lon, resp.status_code)
                continue
            count = 0
            for ac in resp.json().get("ac", []):
                hex_id = ac.get("hex", "")
                if hex_id in seen:
                    continue
                seen.add(hex_id)
                parsed = _parse_v2_aircraft(ac)
                if parsed and not parsed["on_ground"]:
                    aircraft.append(parsed)
                    count += 1
            logger.info("airplanes.live {}/{}: {} aircraft", lat, lon, count)
            success += 1
        except Exception as e:
            logger.warning("airplanes.live {}/{} error: {}", lat, lon, e)

    if success == 0:
        logger.warning("airplanes.live: all grid points failed")
        return None

    if aircraft:
        result = aircraft[:500]
        logger.info("airplanes.live total: {} unique airborne aircraft", len(result))
        return result

    logger.warning("airplanes.live: connected but no airborne aircraft")
    return None


def _parse_opensky_state(state: list) -> dict | None:
    try:
        lat = state[6]
        lon = state[5]
        if lat is None or lon is None:
            return None
        alt_m = state[7] or 0
        return {
            "icao24":         state[0] or "",
            "callsign":       (state[1] or "UNKNOWN").strip(),
            "origin_country": state[2] or "",
            "latitude":       float(lat),
            "longitude":      float(lon),
            "altitude_m":     float(alt_m),
            "altitude_ft":    float(alt_m) * 3.28084,
            "velocity_kts":   float(state[9] or 0) * 1.94384,
            "heading":        float(state[10] or 0),
            "vertical_rate":  float(state[11] or 0) * 196.85,
            "on_ground":      bool(state[8]),
            "squawk":         state[14] or "----",
            "aircraft_type":  "",
            "last_contact":   int(time.time()),
            "is_mock":        False,
        }
    except Exception:
        return None


def _fetch_opensky(lamin=-90, lomin=-180, lamax=90, lomax=180) -> list[dict] | None:
    params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}

    # Try OAuth2 first
    token = _get_opensky_oauth_token()
    if token:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = _session.get(OPENSKY_STATES_URL, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            states = resp.json().get("states") or []
            aircraft = [p for s in states if (p := _parse_opensky_state(s)) is not None]
            aircraft = [a for a in aircraft if not a["on_ground"]]
            if aircraft:
                logger.info("OpenSky (OAuth2): {} airborne aircraft", len(aircraft))
                return aircraft
            logger.warning("OpenSky (OAuth2): connected but no aircraft returned")
            return None
        except Exception as e:
            logger.warning("OpenSky (OAuth2) request failed: {}", e)

    # Try anonymous as last resort
    try:
        resp = _session.get(OPENSKY_STATES_URL, params=params, timeout=20)
        resp.raise_for_status()
        states = resp.json().get("states") or []
        aircraft = [p for s in states if (p := _parse_opensky_state(s)) is not None]
        aircraft = [a for a in aircraft if not a["on_ground"]]
        if aircraft:
            logger.info("OpenSky (anonymous): {} airborne aircraft", len(aircraft))
            return aircraft
        return None
    except Exception as e:
        logger.warning("OpenSky (anonymous) failed: {}", e)
        return None


def fetch_opensky(lamin=-90, lomin=-180, lamax=90, lomax=180) -> list[dict]:
    cache_key = f"opensky:{lamin},{lomin},{lamax},{lomax}"
    cached = aviation_cache.get(cache_key)
    if cached is not None:
        return cached

    if FORCE_MOCK_DATA:
        logger.info("FORCE_MOCK_DATA is set — returning mock aircraft")
        mock = generate_mock_aircraft(500)
        aviation_cache.set(cache_key, mock)
        return mock

    # 1. airplanes.live
    logger.info("Trying airplanes.live…")
    aircraft = _fetch_airplanes_live()

    # 2. OpenSky OAuth2
    if not aircraft:
        logger.info("Trying OpenSky (OAuth2)…")
        aircraft = _fetch_opensky(lamin, lomin, lamax, lomax)

    # 3. Mock
    if not aircraft:
        logger.warning("All live sources failed — using mock data")
        aircraft = generate_mock_aircraft(500)

    aviation_cache.set(cache_key, aircraft)
    return aircraft


def get_aircraft(bbox: dict | None = None) -> list[dict]:
    params = bbox or {}
    return fetch_opensky(**params) if params else fetch_opensky()


class Aircraft:
    def __init__(self, data: dict):
        self.icao24         = data.get("icao24", "")
        self.callsign       = (data.get("callsign") or "UNKNOWN").strip()
        self.origin_country = data.get("origin_country", "")
        self.latitude       = float(data.get("latitude") or 0.0)
        self.longitude      = float(data.get("longitude") or 0.0)
        self.altitude_ft    = float(data.get("altitude_ft") or 0.0)
        self.altitude_m     = float(data.get("altitude_m") or 0.0)
        self.velocity_kts   = float(data.get("velocity_kts") or 0.0)
        self.heading        = float(data.get("heading") or 0.0)
        self.vertical_rate  = float(data.get("vertical_rate") or 0.0)
        self.on_ground      = bool(data.get("on_ground", False))
        self.squawk         = data.get("squawk", "----")
        self.aircraft_type  = data.get("aircraft_type", "")
        self.last_contact   = data.get("last_contact", 0)
        self.is_mock        = bool(data.get("is_mock", False))

    def to_dict(self) -> dict:
        return {
            "callsign":  self.callsign,
            "country":   self.origin_country,
            "alt_ft":    self.altitude_ft,
            "speed_kts": self.velocity_kts,
            "heading":   self.heading,
            "on_ground": self.on_ground,
            "squawk":    self.squawk,
            "type":      self.aircraft_type,
            "lat":       self.latitude,
            "lon":       self.longitude,
            "is_mock":   self.is_mock,
        }

    @property
    def popup_html(self):
        status = "Ground" if self.on_ground else "Airborne"
        mock_tag = "<br><em>Simulated</em>" if self.is_mock else ""
        return f"""<div style='font-family:monospace;font-size:12px'>
          <b>{self.callsign}</b> {self.icao24}<br>
          {status} | {self.origin_country}<br>
          Squawk: {self.squawk} | {self.aircraft_type}<br>
          Alt: {self.altitude_ft:,.0f} ft<br>
          Speed: {self.velocity_kts:.0f} kts | Hdg: {self.heading:.0f}°
          {mock_tag}</div>"""


def fetch_aircraft(bbox=None):
    raw = get_aircraft(bbox)
    aircraft = [Aircraft(a) for a in raw[:500]]
    is_live = any(not a.is_mock for a in aircraft)
    return aircraft, is_live


EMERGENCY_SQUAWKS = {"7700", "7600", "7500"}
SQUAWK_LABELS = {
    "7700": "General Emergency",
    "7600": "Radio Failure",
    "7500": "Hijacking",
}


def check_aviation_anomalies(aircraft):
    anomalies = []
    for ac in aircraft:
        squawk = str(ac.squawk if hasattr(ac, "squawk") else ac.get("squawk", "----")).strip()
        if squawk in EMERGENCY_SQUAWKS:
            anomalies.append({
                "icao24":    ac.icao24 if hasattr(ac, "icao24") else ac.get("icao24"),
                "callsign":  ac.callsign if hasattr(ac, "callsign") else ac.get("callsign"),
                "squawk":    squawk,
                "label":     SQUAWK_LABELS.get(squawk, "Emergency"),
                "latitude":  ac.latitude if hasattr(ac, "latitude") else ac.get("latitude", 0.0),
                "longitude": ac.longitude if hasattr(ac, "longitude") else ac.get("longitude", 0.0),
                "level":     "CRITICAL",
                "message":   f"{ac.callsign if hasattr(ac, 'callsign') else ac.get('callsign')} squawking {squawk} ({SQUAWK_LABELS.get(squawk, 'Emergency')})",
            })
    return anomalies
