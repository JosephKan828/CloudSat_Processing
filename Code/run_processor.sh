#!/bin/bash

START_YEAR=2006
END_YEAR=2017

# Loop through each year
for year in $(seq $START_YEAR $END_YEAR); do
    
    # Check for leap year to set max days to 365 or 366
    if [ $((year % 4)) -eq 0 ] && [ $((year % 100)) -ne 0 ] || [ $((year % 400)) -eq 0 ]; then
        MAX_DAYS=366
    else
        MAX_DAYS=365
    fi

    # Loop through each Julian day
    for date in $(seq 1 $MAX_DAYS); do
        
        # --- THE FIX ---
        # Format the integer date into a 3-digit string (e.g., 1 becomes 001)
        printf -v PADDED_DATE "%03d" $date
        
        # Use the padded date for the directory check
        TARGET_DIR="/work/DATA/Satellite/CloudSat/${year}/${PADDED_DATE}"

        # Only run Python if the data directory actually exists
        if [ -d "$TARGET_DIR" ]; then
            # We can still pass the unpadded $date to Python, 
            # since argparse parses it as a standard integer!
            nice -n 19 python QR_Itp.py --year $year --date $date
        else
            echo "Skipping Year: $year, Date: $PADDED_DATE (Directory not found)"
        fi

    done
done

echo "All years processed successfully!"