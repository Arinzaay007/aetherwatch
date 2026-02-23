with open("config/settings.py", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

import re
new = '''MAP_TILES = {
    "CartoDB dark_matter": "CartoDB dark_matter",
    "CartoDB positron": "CartoDB positron",
    "OpenStreetMap": "OpenStreetMap",
}'''

content = re.sub(r'MAP_TILES\s*=\s*\{[^}]*\}', new, content, flags=re.DOTALL)

with open("config/settings.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed!")