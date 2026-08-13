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
from builtins import str
import numpy as np
import pandas as pd
import xarray as xr

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
# Test function
# ====================================================
def test_interpolation_match(
        year: int,
        date: int,
        z_ds: xr.Dataset,
        fpath: str
        ) -> None:
    """
    Test whether the interpolation matches the original data by plotting and numerical comparison.
    """
    import matplotlib.pyplot as plt
    
    files = list(glob.glob(fpath+"/*.hdf"))
    if not files:
        print("No CloudSat files found for testing.")
        return
        
    lon_name: str = "lon"
    lat_name: str = "lat"
    lev_name: str = "plev"
    var_name: str = "Z"

    lon_era5: np.ndarray = z_ds[lon_name].values
    lat_era5: np.ndarray = z_ds[lat_name].values
    
    z_da: xr.DataArray = z_ds[var_name].squeeze().transpose(lev_name, lat_name, lon_name)
    if z_da.attrs.get("units", "") in ["m**2 s**-2", "m2 s-2"]:
        z_era5: np.ndarray = z_da.values / 9.80665
    else:
        z_era5: np.ndarray = z_da.values
        
    for file in files:
        lon_ray, lat_ray, hgt, qlw, qsw = cs_io.load_data(file)
        i_lat, i_lon, valid = grid.assign_rays_to_grid(lon_era5, lat_era5, lon_ray, lat_ray)
        valid_idx = np.where(valid)[0]
        
        if len(valid_idx) > 0:
            k = valid_idx[len(valid_idx) // 2] # pick a footprint in the middle
            
            z_col = z_era5[:, i_lat[k], i_lon[k]]
            qlw_interp = grid.interp_profile_to_era5_levels(hgt[k], qlw[k], z_col)
            qsw_interp = grid.interp_profile_to_era5_levels(hgt[k], qsw[k], z_col)
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6))
            
            good_lw = np.isfinite(hgt[k]) & np.isfinite(qlw[k])
            good_sw = np.isfinite(hgt[k]) & np.isfinite(qsw[k])
            
            ax1.plot(qlw[k][good_lw], hgt[k][good_lw], 'o-', label='Original', markersize=3)
            ax1.plot(qlw_interp, z_col, 'x-', label='Interpolated', markersize=5)
            ax1.set_title('QLW Interpolation Match')
            ax1.set_xlabel('QLW')
            ax1.set_ylabel('Height [m]')
            ax1.legend()
            
            ax2.plot(qsw[k][good_sw], hgt[k][good_sw], 'o-', label='Original', markersize=3)
            ax2.plot(qsw_interp, z_col, 'x-', label='Interpolated', markersize=5)
            ax2.set_title('QSW Interpolation Match')
            ax2.set_xlabel('QSW')
            ax2.set_ylabel('Height [m]')
            ax2.legend()
            
            save_path = f"/data92/b11209013/CloudSat/Code/interpolation_test_{year}_{date:03d}.png"
            plt.tight_layout()
            plt.savefig(save_path)
            print(f"Interpolation test plot saved to {save_path}")
            
            print("\nNumerical comparison for the valid interpolated points (QLW):")
            print("Height [m]\tInterpolated\tOriginal (nearest point)")
            count = 0
            for i in range(len(z_col)):
                if np.isfinite(qlw_interp[i]):
                    nearest_idx = np.nanargmin(np.abs(hgt[k][good_lw] - z_col[i]))
                    orig_val = qlw[k][good_lw][nearest_idx]
                    print(f"{z_col[i]:.1f}\t\t{qlw_interp[i]:.4f}\t\t{orig_val:.4f}")
                    count += 1
                    if count >= 10: # Just show first 10 for brevity
                        print("...")
                        break
            
            return

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
    lon_name: str = "lon"
    lat_name: str = "lat"
    lev_name: str = "plev"
    var_name: str = "Z"


    lon_era5: np.ndarray = z_ds[lon_name].values
    lat_era5: np.ndarray = z_ds[lat_name].values
    lev_era5: np.ndarray = z_ds[lev_name].values

    z_da: xr.DataArray = z_ds[var_name].squeeze().transpose(lev_name, lat_name, lon_name)  # Remove any singleton dimensions

    if z_da.attrs.get("units", "") in ["m**2 s**-2", "m2 s-2"]:
        z_era5: np.ndarray = z_da.values / 9.80665  # convert geopotential into geopotential height
    else:
        print(f"Warning: Unexpected units for geopotential height: {z_da.attrs.get('units', 'unknown')}. Proceeding without conversion.")
        z_era5: np.ndarray = z_da.values  # Use the values as-is if units are unexpected
    
    n_lev, n_lat, n_lon = z_era5.shape

    # ------------------------------------------------
    # Process file
    # ------------------------------------------------

    # initialzie the master arrays
    qr_sum: np.ndarray = np.zeros((n_lev, n_lat, n_lon, 2))
    qr_cnt: np.ndarray = np.zeros((n_lev, n_lat, n_lon, 2))

    # num_cores = 8 

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
    parser.add_argument("--era5", type=str, required=True, help="Path to ERA5 geopotential height NetCDF file")
    parser.add_argument("--test_interp", action="store_true", help="Run interpolation test and plot the result instead of processing")
    args = parser.parse_args()

    year = args.year
    date = args.date
    era5_file = args.era5

    print(f"Processing Year: {year} Date: {date:03d}")

    # check whether the saving exist or not, if not create one.
    data_path: str = f"/data92/b11209013/CloudSat/DATA/{year}/"
    os.makedirs(data_path, exist_ok=True)

    # Assign time series
    time_series: pd.DatetimeIndex = pd.date_range(start=f"2006-01-01", end=f"2017-12-31", freq="D")

    # boolean mask for the requested date in the time series
    time_idx: np.ndarray = (time_series.year == year) & (time_series.dayofyear == date)

    if not time_idx.any():
        print(f"Error: The specified year {year} and date {date} do not correspond to a valid date in the time series.")
        sys.exit(1)

    # Load geopotential height from ERA5
    with xr.open_dataset(era5_file, chunks={}, engine="netcdf4") as z_ds:
        z_ds_sel: xr.Dataset = z_ds.isel(time=time_idx)

        if args.test_interp:
            fpath: str = f"/work/DATA/Satellite/CloudSat/{year}/{date:03d}"
            test_interpolation_match(year=year, date=date, z_ds=z_ds_sel, fpath=fpath)
            sys.exit(0)

        # use main function
        main(year=year, date=date, z_ds=z_ds_sel, data_dir=data_path+f"{date:03d}.nc")
