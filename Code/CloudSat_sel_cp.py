# This program is to process CloudSat dataset date-by-date
# import package
import os
import sys
import glob
import numpy as np

from pyhdf.HC  import HC
from pyhdf.SD  import SD, SDC, HDF4Error
from pyhdf.VS  import VS
from pyhdf.HDF import HDF

import joblib as jl
from joblib import Parallel, delayed

# year = int(sys.argv[1])
# date = int(sys.argv[2])

year = 2006
date = 170

# ======================= #

# %% define function
# # load data
def load_data(fname):
    from pyhdf.VS  import VS

    hdf = HDF(fname, SDC.READ)

    vs = hdf.vstart()
    lat = np.stack(vs.attach("Latitude")[:]).squeeze()
    lon = np.stack(vs.attach("Longitude")[:]).squeeze()
    vs.end()

    lon[lon <= 0] += 360
    
    cond = (lat >= -15) & (lat <= 15) & (lon >= 160) & (lon <= 260)

    lon = lon[cond]; lat = lat[cond]

    file_sd = SD(fname, SDC.READ)
    # 100.0 is scale factor, check in official website of CloudSat
    hgt = np.array(file_sd.select("Height")[:][cond])
    # 0 of QR stands for shortwave radiation
    qsw = np.array(file_sd.select("QR")[0][cond])
    # 1 of QR stands for longwave radiation
    qlw = np.array(file_sd.select("QR")[1][cond])
    file_sd.end()

    result = {
        "lon": lon, "lat": lat, "hgt": hgt,
        "qlw": qlw, "qsw": qsw
    }

    return result


def check_file_exists(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File path '{filepath}' does not exist.")
        sys.exit(1)  # Shut down the script with a non-zero exit code

# ======================== #

fpath: str = f'/work/DATA/Satellite/CloudSat/{year}/{date}/'

check_file_exists(fpath) # check whether the file exist or not

fname = glob.glob(f'{fpath}*.hdf')

limited_data = Parallel(n_jobs=16)(delayed(load_data)(f) for f in fname)

print(limited_data[0]["qlw"].max(), limited_data[0]["qlw"].min())

# jl.dump(limited_data, f'/work/b11209013/LRF/data/CloudSat/Daily/{year}_{date}.joblib', compress=('zlib', 1))
