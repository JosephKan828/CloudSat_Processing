import xarray as xr
import numpy as np
import pandas as pd

ds1 = xr.Dataset(
    data_vars={"QSW": (["lev"], [1.0])},
    coords={"time": (["time"], [pd.Timestamp("2006-01-01")])}
)
ds2 = xr.Dataset(
    data_vars={"QSW": (["time", "lev"], [[2.0]])},
    coords={"time": (["time"], [pd.Timestamp("2006-01-02")])}
)
try:
    ds_cat = xr.concat([ds1, ds2], dim="time")
    print("Concat successful!")
    print(ds_cat)
except Exception as e:
    print(f"Concat failed: {e}")
