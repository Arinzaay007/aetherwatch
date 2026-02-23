with open("utils/cache.py", "r") as f:
    content = f.read()

if "def cached" not in content:
    with open("utils/cache.py", "a") as f:
        f.write("""

def cached(ttl: int = 60):
    import functools, time
    def decorator(fn):
        _store = {}
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in _store:
                result, ts = _store[key]
                if time.time() - ts < ttl:
                    return result
            result = fn(*args, **kwargs)
            _store[key] = (result, time.time())
            return result
        return wrapper
    return decorator
""")
    print("Done 1/2")
else:
    print("Skip 1/2")

with open("data_sources/aviation.py", "r") as f:
    content = f.read()

if "class Aircraft" not in content:
    with open("data_sources/aviation.py", "a") as f:
        f.write("""

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

    @property
    def popup_html(self):
        status = "Ground" if self.on_ground else "Airborne"
        mock_tag = "<br><em>Simulated</em>" if self.is_mock else ""
        return f\"\"\"<div style='font-family:monospace;font-size:12px'>
          <b>{self.callsign}</b> {self.icao24}<br>
          {status} | {self.origin_country}<br>
          Squawk: {self.squawk} | {self.aircraft_type}<br>
          Alt: {self.altitude_ft:,.0f} ft<br>
          Speed: {self.velocity_kts:.0f} kts | Hdg: {self.heading:.0f}deg
          {mock_tag}</div>\"\"\"
""")
    print("Done 2/2")
else:
    print("Skip 2/2")

old = '    aircraft = get_aircraft(bbox)\n    is_live = any(not a.get("is_mock", True) for a in aircraft)\n    return aircraft, is_live'
new = '    raw = get_aircraft(bbox)\n    aircraft = [Aircraft(a) for a in raw]\n    is_live = any(not a.is_mock for a in aircraft)\n    return aircraft, is_live'
with open("data_sources/aviation.py", "r") as f:
    content = f.read()
if old in content:
    with open("data_sources/aviation.py", "w") as f:
        f.write(content.replace(old, new))
    print("Done 3/3")
else:
    print("Skip 3/3")