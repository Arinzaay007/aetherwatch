with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '    mock = generate_mock_aircraft(500)\n    aviation_cache.set(cache_key, mock)\n    return mock'

new = '''    # Try ADS-B Exchange public feed as fallback
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
    return mock'''

if old in content:
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Pattern not found")