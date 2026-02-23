with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the entire Aircraft class
import re
old_class = re.search(r'class Aircraft:.*?(?=\ndef |\Z)', content, re.DOTALL)
if old_class:
    new_class = '''class Aircraft:
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

'''
    content = content[:old_class.start()] + new_class + content[old_class.end():]
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Class not found")