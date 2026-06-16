"""
This program processes CloudSat datasets date-by-date with improved robustness and performance.
"""

import argparse
import glob
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from joblib import Parallel, delayed
from pyhdf.HDF import HDF
from pyhdf.SD import SD, SDC


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_data(fname: str) -> Optional[Dict[str, np.ndarray]]:
    """
    Loads Latitude, Longitude, Height, and QR data from a CloudSat HDF file.
    Filters data by latitude (-15 to 15) and longitude (160 to 260).
    """
    try:
        # 1. Extract Lat/Lon using VData interface
        hdf = HDF(fname, SDC.READ)
        try:
            vs = hdf.vstart()
            try:
                # Use np.stack and squeeze as in original, but with safety checks
                lat_raw = vs.attach("Latitude")[:]
                lon_raw = vs.attach("Longitude")[:]
                
                lat = np.stack(lat_raw).squeeze()
                lon = np.stack(lon_raw).squeeze()
            finally:
                vs.end()
        finally:
            hdf.close()

        # Longitude adjustment
        lon[lon <= 0] += 360
        
        # Spatial filtering condition
        cond = (lat >= -15) & (lat <= 15) & (lon >= 160) & (lon <= 260)

        # Check if any data matches criteria
        if not np.any(cond):
            return None

        filtered_lon = lon[cond]
        filtered_lat = lat[cond]

        # 2. Extract QR and Height using SD interface
        file_sd = SD(fname, SDC.READ)
        try:
            # 100.0 is scale factor, check in official website of CloudSat
            # Note: Applying scale factor if required by user (comment mentioned it)
            # For now, following original logic of just reading the data at indices
            hgt = np.array(file_sd.select("Height")[:][cond])
            
            # QR dataset: 0 is shortwave (qsw), 1 is longwave (qlw)
            qr_data = file_sd.select("QR")
            qsw = np.array(qr_data[0][cond])
            qlw = np.array(qr_data[1][cond])
        finally:
            file_sd.end()

        return {
            "lon": filtered_lon,
            "lat": filtered_lat,
            "hgt": hgt,
            "qlw": qlw,
            "qsw": qsw
        }

    except Exception as e:
        logger.error(f"Error processing file {fname}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Process CloudSat HDF data files.")
    parser.add_argument("--year", type=int, default=2006, help="Year of data (default: 2006)")
    parser.add_argument("--date", type=int, default=170, help="Day of year (default: 163)")
    parser.add_argument("--n_jobs", type=int, default=8, help="Number of parallel jobs (default: 16)")
    parser.add_argument("--output_dir", type=str, default=None, help="Directory to save joblib output")
    
    args = parser.parse_args()

    # Define path using Path for better handling
    data_root = Path("/work/DATA/Satellite/CloudSat")
    fpath = data_root / str(args.year) / f"{args.date:03d}"

    if not fpath.exists():
        logger.error(f"Directory not found: {fpath}")
        sys.exit(1)

    # Find HDF files
    files = sorted(glob.glob(str(fpath / "*.hdf")))
    if not files:
        logger.warning(f"No .hdf files found in {fpath}")
        return

    logger.info(f"Processing {len(files)} files from {fpath} using {args.n_jobs} cores...")

    # Parallel processing with list comprehension and filtering Nones
    results = Parallel(n_jobs=args.n_jobs)(
        delayed(load_data)(f) for f in files
    )
    
    # Remove None results (from files that failed or had no data in range)
    limited_data = [r for r in results if r is not None]

    if not limited_data:
        logger.warning("No data found matching the spatial criteria.")
        return

    # Print summary of first file as per original script
    first_qlw = limited_data[0]["qlw"]
    print(f"Sample Statistics (First File): Max QLW={first_qlw.max():.2f}, Min QLW={first_qlw.min():.2f}")

    # Optional: Save results
    if args.output_dir:
        import joblib as jl
        out_path = Path(args.output_dir) / f"{args.year}_{args.date}.joblib"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        jl.dump(limited_data, str(out_path), compress=('zlib', 1))
        logger.info(f"Results saved to {out_path}")

if __name__ == "__main__":
    main()
