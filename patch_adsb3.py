with open("data_sources/aviation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the old fallback at the end and replace except blocks
old_end = """    mock = generate_mock_aircraft(500)
    aviation_cache.set(cache_key, mock)
    return mock"""

new_end = """    return _fallback_aircraft(aviation_cache, cache_key)"""

# Replace all the except blocks to use fallback
import re
pattern = r'(    except requests\.exceptions\.ConnectionError.*?    except Exception as e:.*?logger\.error.*?returning mock data.*?\n)'
def replace_excepts(m):
    return '''    except Exception:
        pass

    return _fallback_aircraft(aviation_cache, cache_key)
'''

content = re.sub(
    r'except requests\.exceptions\.ConnectionError:.*?logger\.error\("OpenSky unexpected error.*?\n',
    'except Exception:\n        pass\n\n    return _fallback_aircraft(aviation_cache, cache_key)\n',
    content,
    flags=re.DOTALL,
    count=1
)

if old_end in content:
    content = content.replace(old_end, "", 1)
    print("Removed old fallback!")

with open("data_sources/aviation.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done!")
```

Save, run `python patch_adsb3.py`, then check syntax:
```
python -c "import py_compile; py_compile.compile('data_sources/aviation.py', doraise=True); print('OK')"