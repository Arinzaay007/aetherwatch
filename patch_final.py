import re

with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace entire fetch_opensky function
start = content.find("def fetch_opensky(")
end = content.find("\ndef ", start + 1)

new_func = '''def fetch_opensky(
    lamin: float = -90, lomin: float = -180,
    lamax: float = 90,  lomax: float = 180,
) -> list[dict]:
    cache_key = f"opensky:{lamin},{lomin},{lamax},{lomax}"
    cached = aviation_cache.get(cache_key)
    if cached is not None:
        return cached

    if FORCE_MOCK_DATA:
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
        aircraft = [a for a in aircraft if not a["on_ground"]]
        logger.info("OpenSky: fetched {} airborne aircraft", len(aircraft))
        aviation_cache.set(cache_key, aircraft)
        return aircraft
    except Exception as e:
        logger.warning("OpenSky failed: {} - trying adsb.fi", e)

    return _fallback_aircraft(aviation_cache, cache_key)

'''

content = content[:start] + new_func + content[end:]

with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done!")