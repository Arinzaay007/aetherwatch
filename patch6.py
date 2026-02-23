with open("ui/map_view.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '                location=[cam["lat"], cam["lon"]],'
new = '                location=[cam["location"][0] if "location" in cam else cam["lat"], cam["location"][1] if "location" in cam else cam["lon"]],'

if old in content:
    with open("ui/map_view.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Pattern not found")