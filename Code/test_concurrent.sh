#!/bin/bash
seq 1 4 | xargs -n 1 -P 4 bash -c '
    /work/b11209013/external/miniconda3/envs/pyhdf/bin/python -c "
import xarray as xr;
import sys;
ds = xr.open_dataset(\"/data92/b11209013/ERA5_GRIB/Data/ERA5_PRS_Z_2006-2017_r1440x721_day.nc\", chunks={}, engine=\"netcdf4\")
print(\"Loaded in proc \" + sys.argv[1])
" $1
' _ 
