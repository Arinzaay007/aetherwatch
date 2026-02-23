addition = """

def cache_stats() -> dict:
    total = len(aviation_cache._cache) + len(satellite_cache._cache) + len(camera_cache._cache)
    return {
        "valid_entries": total,
        "total_entries": total,
        "aviation": len(aviation_cache._cache),
        "satellite": len(satellite_cache._cache),
        "camera": len(camera_cache._cache),
    }
"""

with open("utils/cache.py", "r") as f:
    content = f.read()

if "def cache_stats" not in content:
    with open("utils/cache.py", "a") as f:
        f.write(addition)
    print("Done!")
else:
    print("Already there!")