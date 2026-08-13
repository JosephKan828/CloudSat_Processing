import sys
missing = []
for mod in ['numpy', 'pandas', 'xarray', 'netCDF4', 'pyhdf', 'tqdm']:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)
if missing:
    print(f"Missing modules: {', '.join(missing)}")
    sys.exit(1)
print("All Python dependencies installed.")
