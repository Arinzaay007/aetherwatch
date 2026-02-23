with open("config/settings.py", "r", encoding="utf-8") as f:
    content = f.read()

old = """except Exception:
    OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD: str = os.getenv("OPENSKY_PASSWORD", "")"""

new = """except Exception:
    OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")
    OPENSKY_PASSWORD: str = os.getenv("OPENSKY_PASSWORD", "")"""

if old in content:
    with open("config/settings.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Not found - printing area around OPENSKY_PASSWORD...")
    idx = content.find("OPENSKY_PASSWORD")
    print(repr(content[idx-50:idx+100]))