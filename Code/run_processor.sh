#!/bin/bash

START_YEAR=2006
END_YEAR=2017
MAX_JOBS=16

# Set the data directory path
data_dir="/data92/b11209013/CloudSat/DATA"

# ERA5 source directory
era5_file="/data92/b11209013/ERA5_GRIB/Data/ERA5_PRS_Z_2006-2017_r1440x721_day.nc"

# final file name
final_file="${data_dir}/QR_gridded_15layer.nc"

# Loop through each year
for year in $(seq "$START_YEAR" "$END_YEAR"); do

  # Check for leap year to set max days to 365 or 366
  if ((year % 4 == 0 && year % 100 != 0 || year % 400 == 0)); then
    MAX_DAYS=366
  else
    MAX_DAYS=365
  fi

  # Loop through each Julian day
  # We pass the year as $1 and the day as $2 to the inner bash script
  seq 1 "$MAX_DAYS" | xargs -n 1 -P "$MAX_JOBS" bash -c '
        YEAR=$1
        DAY=$2
        PADDED_DATE=$(printf "%03d" "$DAY")
        TARGET_DIR="/work/DATA/Satellite/CloudSat/${YEAR}/${PADDED_DATE}"
        
        if [ -d "$TARGET_DIR" ]; then
            nice -n 19 python /data92/b11209013/CloudSat/Code/QR_Itp.py --year "$YEAR" --date "$DAY" --era5 "$era5_file"
        else
            echo "Skipping Year: $YEAR, Date: ${PADDED_DATE} (Directory not found)"
        fi
    ' _ "$year"

  echo "Start concatenate and fill data for year ${year}"

  # nice -n 19 python /data92/b11209013/CloudSat/Code/yearly_concat.py --year "$year"
  nice -n 19 python /data92/b11209013/CloudSat/Code/yearly_concat.py --year "$year"

  rm -rf /data92/b11209013/CloudSat/DATA/${year}

done

echo "All years processed successfully!"

echo "Merge all-year radiative heating data"

cdo -P 16 -L -O mergetime "${data_dir}/yearly/tmp_20"*.nc ${final_file}

rm -rf "${data_dir}/yearly"

echo "Finish merging"
