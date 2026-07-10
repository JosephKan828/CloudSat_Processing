# ====================================================
# This script is to process the radiative heating in 
# CloudSat data
# ====================================================

# ====================================================
# Environment Setup
# ====================================================

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
import concurrent.futures

from pprint import pprint

import matplotlib.pyplot as plt

# import local package
sys.path.append("/data92/b11209013/CloudSat/Code/utils")
import cs_io #type: ignore
import grid #type: ignore

# ====================================================
# Helper function
# ====================================================
# Single processing function
def _single_file(
    file: str,
    lon_era5: np.ndarray,
    lat_era5: np.ndarray,
    z_era5  : np.ndarray
) -> tuple[np.ndarray, ...]:

    # setup size
    n_lev, n_lat, n_lon = z_era5.shape

    # Pre-allocate array
    local_qr_sum = np.zeros((n_lev, n_lat, n_lon, 2))
    local_qr_cnt = np.zeros((n_lev, n_lat, n_lon, 2))

    # Load CloudSat data
    lon_ray, lat_ray, hgt, qlw, qsw = cs_io.load_data(file)

    # Assign swath bin to grid
    i_lat, i_lon, valid = grid.assign_rays_to_grid(
        lon_era5, lat_era5, lon_ray, lat_ray
    ) 

    i_lat = np.atleast_1d(i_lat)
    i_lon = np.atleast_1d(i_lon)
    valid = np.atleast_1d(valid)

    valid_idx = np.where(valid)[0]
    num_valid = len(valid_idx)
    
    if num_valid == 0:
        return local_qr_sum, local_qr_cnt

    # Pre-allocate profile arrays
    qlw_profiles = np.full((n_lev, num_valid), np.nan)
    qsw_profiles = np.full((n_lev, num_valid), np.nan)

    # Apply interpolation
    for p, k in enumerate(valid_idx):
        z_col: np.ndarray = z_era5[:, i_lat[k], i_lon[k]]

        qlw_profiles[:, p] = grid.interp_profile_to_era5_levels(hgt[k], qlw[k], z_col)
        qsw_profiles[:, p] = grid.interp_profile_to_era5_levels(hgt[k], qsw[k], z_col)

    # Gather grid coordinates for all valid footprints
    lat_idx = i_lat[valid_idx]
    lon_idx = i_lon[valid_idx]

    # Create 2D arrays of coordinates for np.add.at broadcasting
    # Shape: (n_lev, num_valid)
    lev_2d, lat_2d = np.broadcast_arrays(np.arange(n_lev)[:, None], lat_idx[None, :])
    _, lon_2d = np.broadcast_arrays(np.arange(n_lev)[:, None], lon_idx[None, :])

    # Flatten for np.add.at
    lev_flat = lev_2d.flatten()
    lat_flat = lat_2d.flatten()
    lon_flat = lon_2d.flatten()
    
    qsw_flat = qsw_profiles.flatten()
    qlw_flat = qlw_profiles.flatten()

    # calculate for sw using np.add.at
    m_sw = np.isfinite(qsw_flat)
    np.add.at(local_qr_sum[..., 0], (lev_flat[m_sw], lat_flat[m_sw], lon_flat[m_sw]), qsw_flat[m_sw])
    np.add.at(local_qr_cnt[..., 0], (lev_flat[m_sw], lat_flat[m_sw], lon_flat[m_sw]), 1)

    # calculate for lw using np.add.at
    m_lw = np.isfinite(qlw_flat)
    np.add.at(local_qr_sum[..., 1], (lev_flat[m_lw], lat_flat[m_lw], lon_flat[m_lw]), qlw_flat[m_lw])
    np.add.at(local_qr_cnt[..., 1], (lev_flat[m_lw], lat_flat[m_lw], lon_flat[m_lw]), 1)

    return local_qr_sum, local_qr_cnt

# ====================================================
# Main function
# ====================================================

def main(
        year: int,
        date: int,
        z_ds: xr.Dataset,
        data_dir: str
        ) -> None:

    # ------------------------------------------------
    # Verify the existence of data
    # ------------------------------------------------
    fpath: str = f"/work/DATA/Satellite/CloudSat/{year}/{date:03d}" # file directory

    # check for the existence
    if not os.path.exists(fpath):
        print(f"Error: File path '{fpath}' does not exist.")
        sys.exit(1)  # Shut down the script with a non-zero exit code

    # ------------------------------------------------
    # Load CloudSat data
    # ------------------------------------------------

    # file collection
    files: list[str] = list(glob.glob(fpath+"/*.hdf"))
    
    # ------------------------------------------------
    # unpack ERA5 data
    # ------------------------------------------------
    lon_era5: np.ndarray = z_ds["lon"].values
    lat_era5: np.ndarray = z_ds["lat"].values
    lev_era5: np.ndarray = z_ds["level"].values
    z_era5  : np.ndarray = z_ds["z"].values / 9.80665 # convert geopotential into geopotential height
    
    n_lev, n_lat, n_lon = z_era5.shape

    # ------------------------------------------------
    # Process file
    # ------------------------------------------------

    # initialzie the master arrays
    qr_sum: np.ndarray = np.zeros((n_lev, n_lat, n_lon, 2))
    qr_cnt: np.ndarray = np.zeros((n_lev, n_lat, n_lon, 2))

    num_cores = 8 

    for f in files:
        local_sum, local_cnt = _single_file(f, lon_era5, lat_era5, z_era5)

        qr_sum += local_sum
        qr_cnt += local_cnt

    # Calculate final mean
    qr_mean = np.full_like(qr_sum, np.nan) 
    np.divide(qr_sum, qr_cnt, out=qr_mean, where=qr_cnt > 0)

    # ------------------------------------------------
    # save file
    # ------------------------------------------------
    cs_io.save_data(
        year = year,
        date = date,
        data = qr_mean,
        lon  = lon_era5,
        lat  = lat_era5,
        lev  = lev_era5,
        data_dir = data_dir
    )

# ====================================================
# Execute main function
# ====================================================

if __name__ == "__main__":

    import argparse

    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Process CloudSat Radiative Heating")
    parser.add_argument("--year", type=int, required=True, help="Processing Year (YYYY)")
    parser.add_argument("--date", type=int, required=True, help="Processing Julian Date (1-366)")
    args = parser.parse_args()

    year = args.year
    date = args.date

    print(f"Processing Year: {year} Date: {date:03d}")

    # check whether the saving exist or not, if not create one.
    data_path: str = f"/data92/b11209013/CloudSat/DATA/{year}/"
    os.makedirs(data_path, exist_ok=True)

    # Load geopotential height from ERA5
    with xr.open_dataset(f"/data92/b11209013/ERA5/z/z_{year}.nc", chunks={}, engine="netcdf4") as z_ds:
        z_ds: xr.Dataset = z_ds.isel(time=date-1)

        # use main function
        main(year=year, date=date, z_ds=z_ds, data_dir=data_path+f"{date:03d}.nc")
