"""
AetherWatch — Aviation Data Source
Primary: OpenSky Network (free, real-time, global ADS-B)
Optional upgrade: FlightRadar24 REST API (paid, higher data quality)

OpenSky API docs: https://openskynetwork.github.io/opensky-api/rest.html
"""

import time
import requests
from requests.auth import HTTPBasicAuth
from typing import Any

from config.settings import (
    OPENSKY_STATES_URL,
    OPENSKY_USERNAME,
    OPENSKY_PASSWORD,
    FR24_API_TOKEN,
    FR24_FLIGHTS_URL,
    FORCE_MOCK_DATA,
)
from utils.cache import aviation_cache
from utils.logger import logger
from utils.mock_data import generate_mock_aircraft


# HTTP session reuse for connection pooling
_session = requests.Session()
_session.headers.update({"User-Agent": "AetherWatch/1.0 (educational project)"})


def _parse_opensky_state(state: list) -> dict | None:
    """
    Parse a single OpenSky state vector.
    State vector fields: https://openskynetwork.github.io/opensky-api/rest.html#response
    """
    if state is None or len(state) < 17:
        return None
    if state[5] is None or state[6] is None:
        return None  # No position data

    altitude_m = state[7] or state[13] or 0.0  # geo altitude or baro altitude
    altitude_ft = round(altitude_m * 3.28084)
    velocity_ms = state[9] or 0.0
    velocity_kts = round(velocity_ms * 1.94384)

    return {
        "icao24":        state[0],
        "callsign":      (state[1] or "").strip() or "UNKNOWN",
        "origin_country": state[2] or "Unknown",
        "latitude":      round(state[6], 4),
        "longitude":     round(state[5], 4),
        "altitude_m":    round(altitude_m),
        "altitude_ft":   altitude_ft,
        "velocity_ms":   round(velocity_ms, 1),
        "velocity_kts":  velocity_kts,
        "heading":       round(state[10] or 0.0, 1),
        "vertical_rate": round(state[11] or 0.0, 1),
        "on_ground":     bool(state[8]),
        "squawk":        state[14] or "----",
        "last_contact":  state[4] or int(time.time()),
        "is_mock":       False,
    }



def _fallback_aircraft(cache, cache_key):
    """Try adsb.fi, fall back to mock."""
    try:
        import requests as _req
        resp = _req.get(
            "https://opendata.adsb.fi/api/v2/aircraft",
            timeout=10,
            headers={"User-Agent": "AetherWatch/1.0"}
        )
        if resp.status_code == 200:
            data = resp.json()
            aircraft = []
            for ac in data.get("aircraft", [])[:500]:
                if not ac.get("lat") or not ac.get("lon"):
                    continue
                aircraft.append({
                    "icao24": ac.get("hex", ""),
                    "callsign": (ac.get("flight") or "UNKNOWN").strip(),
                    "origin_country": ac.get("r", ""),
                    "latitude": float(ac.get("lat", 0)),
                    "longitude": float(ac.get("lon", 0)),
                    "altitude_ft": float(ac.get("alt_baro", 0) or 0),
                    "altitude_m": float(ac.get("alt_baro", 0) or 0) * 0.3048,
                    "velocity_kts": float(ac.get("gs", 0) or 0),
                    "heading": float(ac.get("track", 0) or 0),
                    "vertical_rate": float(ac.get("baro_rate", 0) or 0),
                    "on_ground": ac.get("alt_baro") == "ground",
                    "squawk": ac.get("squawk", "----"),
                    "aircraft_type": ac.get("t", ""),
                    "last_contact": 0,
                    "is_mock": False,
                })
            if aircraft:
                cache.set(cache_key, aircraft)
                return aircraft
    except Exception:
        pass
    mock = generate_mock_aircraft(500)
    cache.set(cache_key, mock)
    return mock

def fetch_opensky(
    lamin: float = -90, lomin: float = -180,
    lamax: float = 90,  lomax: float = 180,
) -> list[dict]:
    """
    Fetch live aircraft states from OpenSky Network.
    Cached for OPENSKY_CACHE_TTL seconds to respect rate limits.
    Falls back to mock data on any error.
    """
    cache_key = f"opensky:{lamin},{lomin},{lamax},{lomax}"
    cached = aviation_cache.get(cache_key)
    if cached is not None:
        logger.debug("Aviation: serving from cache ({} aircraft)", len(cached))
        return cached

    if FORCE_MOCK_DATA:
        logger.info("Aviation: FORCE_MOCK_DATA — returning mock aircraft")
        mock = generate_mock_aircraft(500)
        aviation_cache.set(cache_key, mock)
        return mock

    params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
    auth = None
    if OPENSKY_USERNAME and OPENSKY_PASSWORD:
        auth = HTTPBasicAuth(OPENSKY_USERNAME, OPENSKY_PASSWORD)

    try:
        resp = _session.get(
            OPENSKY_STATES_URL,
            params=params,
            auth=auth,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states") or []
        aircraft = [p for s in states if (p := _parse_opensky_state(s)) is not None]
        # Filter airborne only by default
        aircraft = [a for a in aircraft if not a["on_ground"]]
        logger.info("OpenSky: fetched {} airborne aircraft", len(aircraft))
        aviation_cache.set(cache_key, aircraft)
        return aircraft

    except requests.exceptions.ConnectionError:
        logger.warning("OpenSky: connection error — returning mock data")
    except requests.exceptions.Timeout:
        logger.warning("OpenSky: timeout — returning mock data")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            logger.warning("OpenSky: rate limited (429) — returning mock data")
        else:
            logger.warning("OpenSky HTTP error: {} — returning mock data", e)
    except Exception as e:
        logger.error("OpenSky unexpected error: {} — returning mock data", e)

    # Try ADS-B Exchange public feed as fallback
    try:
        import requests
        resp = requests.get(
            "https://opendata.adsb.fi/api/v2/aircraft",
            timeout=10,
            headers={"User-Agent": "AetherWatch/1.0"}
        )
        if resp.status_code == 200:
            data = resp.json()
            aircraft = []
            for ac in data.get("aircraft", [])[:500]:
                if not ac.get("lat") or not ac.get("lon"):
                    continue
                aircraft.append({
                    "icao24": ac.get("hex", ""),
                    "callsign": ac.get("flight", "UNKNOWN").strip(),
                    "origin_country": ac.get("r", ""),
                    "latitude": float(ac.get("lat", 0)),
                    "longitude": float(ac.get("lon", 0)),
                    "altitude_ft": float(ac.get("alt_baro", 0) or 0),
                    "altitude_m": float(ac.get("alt_baro", 0) or 0) * 0.3048,
                    "velocity_kts": float(ac.get("gs", 0) or 0),
                    "heading": float(ac.get("track", 0) or 0),
                    "vertical_rate": float(ac.get("baro_rate", 0) or 0),
                    "on_ground": ac.get("alt_baro") == "ground",
                    "squawk": ac.get("squawk", "----"),
                    "aircraft_type": ac.get("t", ""),
                    "last_contact": 0,
                    "is_mock": False,
                })
            if aircraft:
                aviation_cache.set(cache_key, aircraft)
                return aircraft
    except Exception:
        pass

    mock = generate_mock_aircraft(500)
    aviation_cache.set(cache_key, mock)
    return mock


def fetch_fr24(bbox: dict | None = None) -> list[dict]:
    """
    Optional: Fetch from FlightRadar24 REST API.
    Requires a paid FR24 API subscription.
    Returns empty list and warns if token is not set.
    """
    if not FR24_API_TOKEN:
        logger.debug("FR24: no token set — skipping (using OpenSky instead)")
        return []

    headers = {"Authorization": f"Bearer {FR24_API_TOKEN}"}
    params = {}
    if bbox:
        params.update(bbox)

    try:
        resp = _session.get(FR24_FLIGHTS_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        flights = data.get("flights", [])
        parsed = []
        for f in flights:
            parsed.append({
                "icao24":        f.get("hex", ""),
                "callsign":      f.get("callsign", "UNKNOWN"),
                "origin_country": f.get("orig_iata", ""),
                "latitude":      f.get("lat", 0.0),
                "longitude":     f.get("lon", 0.0),
                "altitude_ft":   f.get("alt", 0),
                "altitude_m":    round(f.get("alt", 0) * 0.3048),
                "velocity_kts":  f.get("spd", 0),
                "heading":       f.get("track", 0),
                "vertical_rate": f.get("vsi", 0),
                "on_ground":     f.get("gnd", False),
                "squawk":        f.get("squawk", "----"),
                "aircraft_type": f.get("type", ""),
                "last_contact":  int(time.time()),
                "is_mock":       False,
            })
        logger.info("FR24: fetched {} flights", len(parsed))
        return parsed

    except Exception as e:
        logger.error("FR24 error: {}", e)
        return []


def get_aircraft(bbox: dict | None = None) -> list[dict]:
    """
    Main entry point. Uses FR24 if token available, else OpenSky.
    Always returns a list (possibly mock).
    """
    if FR24_API_TOKEN:
        result = fetch_fr24(bbox)
        if result:
            return result

    params = bbox or {}
    return fetch_opensky(**params) if params else fetch_opensky()
def fetch_aircraft(bbox=None):
    raw = get_aircraft(bbox)
    aircraft = [Aircraft(a) for a in raw[:500]]
    is_live = any(not a.is_mock for a in aircraft)
    return aircraft, is_live

EMERGENCY_SQUAWKS = {"7700", "7600", "7500"}
SQUAWK_LABELS = {"7700": "General Emergency", "7600": "Radio Failure", "7500": "Hijacking"}

def check_aviation_anomalies(aircraft):
    anomalies = []
    for ac in aircraft:
        squawk = str(ac.squawk if hasattr(ac, "squawk") else ac.get("squawk", "----")).strip()
        if squawk in EMERGENCY_SQUAWKS:
            anomalies.append({
                "icao24": ac.icao24 if hasattr(ac, "icao24") else ac.get("icao24"),
                "callsign": ac.callsign if hasattr(ac, "callsign") else ac.get("callsign"),
                "squawk": squawk,
                "label": SQUAWK_LABELS.get(squawk, "Emergency"),
                "latitude": ac.latitude if hasattr(ac, "latitude") else ac.get("latitude", 0.0),
                "longitude": ac.longitude if hasattr(ac, "longitude") else ac.get("longitude", 0.0),
            })
    return anomalies


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
            "callsign": self.callsign,
            "country": self.origin_country,
            "alt_ft": self.altitude_ft,
            "speed_kts": self.velocity_kts,
            "heading": self.heading,
            "on_ground": self.on_ground,
            "squawk": self.squawk,
            "type": self.aircraft_type,
            "lat": self.latitude,
            "lon": self.longitude,
            "is_mock": self.is_mock,
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
          Speed: {self.velocity_kts:.0f} kts | Hdg: {self.heading:.0f}deg
          {mock_tag}</div>"""

