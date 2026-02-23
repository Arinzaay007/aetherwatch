with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("generate_mock_aircraft(80)", "generate_mock_aircraft(500)")

with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done!")