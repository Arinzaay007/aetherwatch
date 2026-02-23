with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "    except requests.exceptions.ConnectionError:\n        logger.warning(\"OpenSky: connection error — returning mock data\")"
new = "    except requests.exceptions.ConnectionError as e:\n        logger.warning(\"OpenSky: connection error — returning mock data\")"

# Fix the real issue - mock variable scope in except blocks
old2 = """    except requests.exceptions.ConnectionError as e:
        logger.warning("OpenSky: connection error — returning mock data")
    except requests.exceptions.Timeout:
        logger.warning("OpenSky: timeout — returning mock data")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            logger.warning("OpenSky: rate limited (429) — returning mock data")
        else:
            logger.warning("OpenSky HTTP error: {} — returning mock data", e)
    except Exception as e:
        logger.error("OpenSky unexpected error: {} — returning mock data", e)"""

new2 = """    except requests.exceptions.ConnectionError:
        logger.warning("OpenSky: connection error — using fallback")
        return _fallback_aircraft(aviation_cache, cache_key)
    except requests.exceptions.Timeout:
        logger.warning("OpenSky: timeout — using fallback")
        return _fallback_aircraft(aviation_cache, cache_key)
    except requests.exceptions.HTTPError as e:
        logger.warning("OpenSky HTTP error: {} — using fallback", e)
        return _fallback_aircraft(aviation_cache, cache_key)
    except Exception as e:
        logger.error("OpenSky unexpected error: {} — using fallback", e)
        return _fallback_aircraft(aviation_cache, cache_key)"""

if old2 in content:
    content = content.replace(old2, new2)
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Step 1 done!")
else:
    print("Step 1 pattern not found")

# Now add the _fallback_aircraft helper function before fetch_opensky
with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

helper = '''
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

'''

if "_fallback_aircraft" not in content:
    idx = content.find("def fetch_opensky(")
    content = content[:idx] + helper + content[idx:]
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Step 2 done!")
else:
    print("Step 2 already done!")