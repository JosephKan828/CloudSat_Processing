# ----------------------------------------------------
# This script is to concatenate CloudSat radiative 
# heating dataset, and insert NAN value into missing
# ----------------------------------------------------

# limit CPU usage
CPU_LIMIT = 1

import os
os.environ["OMP_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["MKL_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["OPENBLAS_NUM_THREADS"] = str(CPU_LIMIT)
os.environ["VECLIB_MAXIMUM_THREADS"] = str(CPU_LIMIT)
os.environ["NUMEXPR_NUM_THREADS"] = str(CPU_LIMIT)

import sys
import glob
import numpy as np
import pandas as pd
import netCDF4 as nc
from datetime import datetime
from tqdm import tqdm

def main(year: int) -> None:
    """
    Main function for this script
    """
    file_dir = f"/data92/b11209013/CloudSat/DATA/{year}"
    files = sorted(list(glob.glob(f"{file_dir}/*.nc")))

    if not files:
        print(f"No files found for year {year}")
        return

    # Assign file saving directory
    save_dir = "/data92/b11209013/CloudSat/DATA/yearly"
    os.makedirs(save_dir, exist_ok=True)
    save_path = f"{save_dir}/{year}.nc"

    # Determine number of days in the year (accounting for leap years)
    days_in_year = 366 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 365
    
    # 1. Read the first file to grab dimensions and grid coordinates
    with nc.Dataset(files[0], 'r') as src:
        lev = src.variables['level'][:]
        lat = src.variables['lat'][:]
        lon = src.variables['lon'][:]
        n_lev, n_lat, n_lon = len(lev), len(lat), len(lon)

    print(f"Creating master yearly dataset: {save_path}")
    
    # 2. Pre-allocate the master NetCDF file
    with nc.Dataset(save_path, 'w', format='NETCDF4') as dst:
        
        # Dimensions
        dst.createDimension('time', days_in_year)
        dst.createDimension('lev', n_lev)
        dst.createDimension('lat', n_lat)
        dst.createDimension('lon', n_lon)
        
        # Coordinate Variables
        time_var = dst.createVariable('time', 'f8', ('time',))
        lev_var = dst.createVariable('lev', 'f4', ('lev',))
        lat_var = dst.createVariable('lat', 'f4', ('lat',))
        lon_var = dst.createVariable('lon', 'f4', ('lon',))
        
        # Assign coordinate values
        # Time array: days since 1900-01-01
        base_date = datetime(1900, 1, 1)
        year_start = datetime(year, 1, 1)
        start_offset = (year_start - base_date).days
        time_var[:] = np.arange(start_offset, start_offset + days_in_year)
        time_var.units = "days since 1900-01-01 00:00:00"
        
        lev_var[:] = lev
        lat_var[:] = lat
        lon_var[:] = lon
        
        # 3. Create Main Data Variables
        # Chunks: 1 time step, all spatial points (since we write 1 day at a time)
        var_kwargs = {
            'zlib': True, 
            'complevel': 1, 
            'fill_value': np.nan,
            'chunksizes': (1, n_lev, n_lat, n_lon)
        }
        
        qsw_var = dst.createVariable('QSW', 'f4', ('time', 'lev', 'lat', 'lon'), **var_kwargs)
        qlw_var = dst.createVariable('QLW', 'f4', ('time', 'lev', 'lat', 'lon'), **var_kwargs)
        
        # Global Attributes
        dst.title = "CloudSat Radiative Heating Rate"
        dst.description = "Annual concatenated CloudSat Radiative Heating dataset. Interpolated to ERA5 spatial grid. Missing days are filled with NaNs."
        dst.author = "Yu-Chuan Kan"
        dst.institution = "Department of Atmospheric Sciences, National Taiwan University"
        dst.contact = "r14229003@ntu.edu.tw"
        dst.history = f"Created on {pd.Timestamp.now().strftime('%Y-%m-%d')} via Python netCDF4."
        dst.source = "CloudSat Level 2 FLXHR-Lidar product (or appropriate source)"
        dst.Conventions = "CF-1.8"
        
        # 4. Loop through daily files and drop data directly into the time slot
        print(f"Inserting {len(files)} daily files into yearly dataset...")
        for f in tqdm(files, desc=f"Processing Year {year}"):
            # Filename is {JulianDay}.nc, e.g., 001.nc -> day 1
            day_num = int(os.path.basename(f).split('.')[0])
            idx = day_num - 1 # 0-indexed for the time array
            
            with nc.Dataset(f, 'r') as src:
                # Read 3D daily data and reshape to guarantee exact match
                qsw_var[idx, :, :, :] = src.variables['QSW'][:].reshape(n_lev, n_lat, n_lon)
                qlw_var[idx, :, :, :] = src.variables['QLW'][:].reshape(n_lev, n_lat, n_lon)

    print(f"Successfully generated {save_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="concatenate data")
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    
    main(year=args.year)
