with open("data_sources/aviation.py", "r") as f:
    content = f.read()

old = """def check_aviation_anomalies(aircraft):
    anomalies = []
    for ac in aircraft:
        squawk = str(ac.get("squawk", "----")).strip()
        if squawk in EMERGENCY_SQUAWKS:
            anomalies.append({
                "icao24": ac.get("icao24"),
                "callsign": ac.get("callsign"),
                "squawk": squawk,
                "label": SQUAWK_LABELS.get(squawk, "Emergency"),
                "latitude": ac.get("latitude", 0.0),
                "longitude": ac.get("longitude", 0.0)
            })
    return anomalies"""

new = """def check_aviation_anomalies(aircraft):
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
    return anomalies"""

if old in content:
    with open("data_sources/aviation.py", "w") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Pattern not found")