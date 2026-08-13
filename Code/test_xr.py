import sys
import numpy as np
import pandas as pd
import xarray as xr

era5_file = "/data92/b11209013/ERA5_GRIB/Data/ERA5_PRS_Z_2006-2017_r1440x721_day.nc"
year = 2006
date = 1

time_series = pd.date_range(start="2006-01-01", end="2017-12-31", freq="D")
time_idx = (time_series.year == year) & (time_series.dayofyear == date)

print(f"time_idx shape: {time_idx.shape}, sum: {time_idx.sum()}")

try:
    with xr.open_dataset(era5_file, chunks={}, engine="netcdf4") as z_ds:
        print("Opened dataset successfully")
        print(f"Time dim size: {z_ds.sizes['time']}")
        z_ds_sel = z_ds.isel(time=time_idx)
        print(f"Selected time dim size: {z_ds_sel.sizes['time']}")
        # try to compute something small to trigger loading
        print("Test passed")
except Exception as e:
    print(f"Error: {e}")
