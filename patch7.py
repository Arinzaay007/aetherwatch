# Add to_dict() to Aircraft class and limit aircraft display
with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add to_dict method to Aircraft class
old = "    @property\n    def popup_html(self) -> str:"
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

    @property
    def popup_html(self) -> str:"""

if old in content:
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Done 1/2 - to_dict added!")
else:
    print("Skip 1/2")

# Limit aircraft in fetch_aircraft to 500 for performance
with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "    raw = get_aircraft(bbox)\n    aircraft = [Aircraft(a) for a in raw]\n    is_live = any(not a.is_mock for a in aircraft)\n    return aircraft, is_live"
new = "    raw = get_aircraft(bbox)\n    aircraft = [Aircraft(a) for a in raw[:500]]\n    is_live = any(not a.is_mock for a in aircraft)\n    return aircraft, is_live"

if old in content:
    with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Done 2/2 - aircraft limited to 500!")
else:
    print("Skip 2/2")