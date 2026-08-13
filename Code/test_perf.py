import time
import xarray as xr
import pandas as pd
import numpy as np

era5_file = "/data92/b11209013/ERA5_GRIB/Data/ERA5_PRS_Z_2006-2017_r1440x721_day.nc"
year = 2006
date = 1

time_series = pd.date_range(start="2006-01-01", end="2017-12-31", freq="D")
time_idx = (time_series.year == year) & (time_series.dayofyear == date)

t0 = time.time()
with xr.open_dataset(era5_file, chunks={}, engine="netcdf4") as z_ds:
    z_ds_sel = z_ds.isel(time=time_idx)
    data = z_ds_sel["Z"].values
print(f"With chunks={{}}: {time.time()-t0:.2f}s")

t0 = time.time()
with xr.open_dataset(era5_file, engine="netcdf4") as z_ds:
    z_ds_sel = z_ds.isel(time=time_idx)
    data = z_ds_sel["Z"].values
print(f"Without chunks={{}}: {time.time()-t0:.2f}s")
