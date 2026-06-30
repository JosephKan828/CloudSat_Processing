#!/bin/bash

START_YEAR=2006
END_YEAR=2017
MAX_JOBS=8

# Export variables so inner bash can access them
export START_YEAR END_YEAR

# Loop through each year
for year in $(seq $START_YEAR $END_YEAR); do
    
    # Check for leap year to set max days to 365 or 366
    if [ $((year % 4)) -eq 0 ] && [ $((year % 100)) -ne 0 ] || [ $((year % 400)) -eq 0 ]; then
        MAX_DAYS=366
    else
        MAX_DAYS=365
    fi

    # Export year so xargs inner bash can see it
    export year

    # Loop through each Julian day
    # We pass the day as argument "$1" to the inner bash script
    seq 1 $MAX_DAYS | xargs -n 1 -P $MAX_JOBS -I {} bash -c '
        PADDED_DATE=$(printf "%03d" "$1")
        TARGET_DIR="/work/DATA/Satellite/CloudSat/${year}/${PADDED_DATE}"
        
        if [ -d "$TARGET_DIR" ]; then
            nice -n 19 python /data92/b11209013/CloudSat/Code/QR_Itp.py --year "$year" --date "$1"
        else
            echo "Skipping Year: $year, Date: ${PADDED_DATE} (Directory not found)"
        fi
    ' _ {}

    echo "Start concatenate and fill data for year ${year}"

    nice -n 19 python /data92/b11209013/CloudSat/Code/concat_data.py --year "$year"

done

echo "All years processed successfully!"