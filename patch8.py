with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "    def popup_html(self):"
new = """    def to_dict(self) -> dict:
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

    def popup_html(self):"""

if old in content:
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Not found")