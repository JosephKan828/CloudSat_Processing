#!/bin/sh

data_dir="/data92/b11209013/CloudSat/DATA"

cdo -P 8 -L -mergetime $data_dir"/yearly/20*.nc" $data_dir"/QR_gridded.nc" 