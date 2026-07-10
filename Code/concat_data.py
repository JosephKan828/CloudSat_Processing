# ----------------------------------------------------
# This script is to concatenate CloudSat radiative 
# heating dataset, and insert NAN value into missing
# ----------------------------------------------------

# ----------------------------------------------------
# Environment Setup
# ----------------------------------------------------

# limit CPU usage
CPU_LIMIT: int = 1

import os
os.environ["OMP_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["MKL_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["OPENBLAS_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["VECLIB_MAXIMUM_THREADS"] = str(CPU_LIMIT)
os.environ["NUMEXPR_NUM_THREADS"] = str(CPU_LIMIT)

# import package
import sys
import glob
import numpy as np
import pandas as pd
import xarray as xr

xr.set_options(file_cache_maxsize=128)

from tqdm import tqdm
from pprint import pprint

import matplotlib.pyplot as plt

# import local package
sys.path.append("/data92/b11209013/CloudSat/Code/utils")
import cs_io
import grid

# ====================================================
# Main function
# ====================================================

def main(
    year: int
) -> None:
    """
    Main function for this script
    """

    # ------------------------------------------------
    # Load data
    # ------------------------------------------------
    # collect data

    file_dir: str = f"/data92/b11209013/CloudSat/DATA/{year}"
    files: list[str] = sorted(list(glob.glob(f"{file_dir}/*.nc")))

    if not files:
        print(f"No files found for year {year}")
        return

    # collect days
    dates: list[int] = [int(f.split("/")[-1].split(".")[0]) for f in files]
    
    # ------------------------------------------------
    # Save the data
    # ------------------------------------------------
    # assign file saving directory
    save_path: str = f"/data92/b11209013/CloudSat/DATA/yearly/{year}.nc"

    # 1. Load all available files instantly in parallel
    print(f"Loading {len(files)} files via open_mfdataset...")
    
    # We must chunk along time (e.g., 30 days) instead of 1 day to drastically reduce the number of disk I/O writes.
    ds_combine = xr.open_mfdataset(
        files, 
        combine="nested", 
        concat_dim="time", 
        parallel=True,
        chunks={'time': 30, 'lev': -1, 'lat': -1, 'lon': -1} 
    )
    
    # 2. Let Xarray automatically fill all missing dates with NaNs
    print("Reindexing to fill missing days...")
    year_date = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="1D")
    ds_combine = ds_combine.reindex(time=year_date)

    ds_combine.attrs = {
        "title": "CloudSat Radiative Heating Rate",
        "description": (
            "Annual concatenated CloudSat Radiative Heating dataset. "
            "Interpolated to ERA5 spatial grid. Missing days are filled with NaNs."
        ),
        "author": "Yu-Chuan Kan",
        "institution": "Department of Atmospheric Sciences, National Taiwan University",
        "contact": "r14229003@ntu.edu.tw",
        "history": f"Created on {pd.Timestamp.now().strftime('%Y-%m-%d')} via Python xarray.",
        "source": "CloudSat Level 2 FLXHR-Lidar product (or appropriate source)",
        "Conventions": "CF-1.8" 
    }

    ds_combine = ds_combine.transpose("time", "lev", "lat", "lon")
    ds_combine.encoding["unlimited_dims"] = ["time"]

    # 3. Add compression! Without this, it writes a 112GB raw uncompressed file, which takes forever!
    encoding_settings = {
        "QSW": {"zlib": True, "complevel": 5, "_FillValue": np.nan},
        "QLW": {"zlib": True, "complevel": 5, "_FillValue": np.nan},
        "time": {"units": "days since 1900-01-01 00:00:00"}
    }

    # write out the finalized dataset
    print(f"Writing concatenated dataset to {save_path}...")
    ds_combine.to_netcdf(save_path, encoding=encoding_settings)

    #  close ds
    ds_combine.close()


        


# ====================================================
# Execute main function
# ====================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="concatenate data")

    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()

    # Removed the explicit dask Client() here. 
    # Xarray will automatically fall back to the default Dask threaded scheduler, 
    # which has built-in thread locks specifically designed to safely write NetCDF4 files!

    main(year=args.year)

    # for year in range(2006, 2018):
    #     print(f"Processing Year: {year:04d}")
    #     main(year=year)
