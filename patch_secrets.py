with open("config/settings.py", "r", encoding="utf-8") as f:
    content = f.read()

old = """OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")"""

new = """try:
    import streamlit as st
    OPENSKY_USERNAME: str = st.secrets.get("OPENSKY_USERNAME", os.getenv("OPENSKY_USERNAME", ""))
    OPENSKY_PASSWORD: str = st.secrets.get("OPENSKY_PASSWORD", os.getenv("OPENSKY_PASSWORD", ""))
except Exception:
    OPENSKY_USERNAME: str = os.getenv("OPENSKY_USERNAME", "")"""

if old in content:
    with open("config/settings.py", "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Not found")