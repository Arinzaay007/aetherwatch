with open("utils/cache.py", "r") as f:
    content = f.read()

old = """def cache_stats() -> dict:
    return {
        "aviation": {
            "size": len(aviation_cache._cache),
            "valid_entries": len(aviation_cache._cache),
            "total_entries": len(aviation_cache._cache),
        },
        "satellite": {
            "size": len(satellite_cache._cache),
            "valid_entries": len(satellite_cache._cache),
            "total_entries": len(satellite_cache._cache),
        },
        "camera": {
            "size": len(camera_cache._cache),
            "valid_entries": len(camera_cache._cache),
            "total_entries": len(camera_cache._cache),
        },
    }"""

new = """def cache_stats() -> dict:
    total = len(aviation_cache._cache) + len(satellite_cache._cache) + len(camera_cache._cache)
    return {
        "valid_entries": total,
        "total_entries": total,
        "aviation": len(aviation_cache._cache),
        "satellite": len(satellite_cache._cache),
        "camera": len(camera_cache._cache),
    }"""

if old in content:
    with open("utils/cache.py", "w") as f:
        f.write(content.replace(old, new))
    print("Fixed!")
else:
    print("Pattern not found - checking...")
    print("cache_stats" in content)