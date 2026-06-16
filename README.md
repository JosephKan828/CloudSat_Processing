# CloudSat 2B-FLXHR-LIDAR Pre-processing Pipeline

## Abstract
This repository contains a high-efficiency preprocessing pipeline for the CloudSat 2B-FLXHR-LIDAR dataset. The algorithm bins native 1D satellite swath data into a standard 2D ERA5 spatial grid and vertically interpolates the staggered radiative profiles to ERA5 geopotential height levels. Finally, it computes a domain-mean vertical profile for any grid cell containing valid observations and outputs the result as a compressed NetCDF4 file.

## Repository Structure
```text
.
├── QR_Itp.py              # Main execution script (multiprocessing orchestrator)
├── run_processor.sh       # Bash wrapper for automated multi-year processing
└── utils/
    ├── cs_io.py           # Handles HDF4 I/O and NetCDF4 formatted export
    └── grid.py            # Core spatial binning and vertical interpolation math
```

## Prerequisites & Environment

This pipeline is designed for Linux-based High-Performance Computing (HPC) environments. The following Python libraries are strictly required:
 - numpy
 - pandas
 - xarray
 - pyhdf
 - netcdf4
Important Note on CPU Constraints: The Python script explicitly restricts underlying C-libraries (OpenBLAS, MKL, OpenMP) to a single thread (CPU_LIMIT=1) to prevent thread oversubscription when the ProcessPoolExecutor launches multiple independent parallel workers.

## Data Acquisition

This pipeline requires two distinct datasets:
CloudSat 2B-FLXHR-LIDAR: Along-track swath observations of radiation fluxes and radiative heating rates. Stored in HDF4 format.
ERA5 Geopotential: Standard atmospheric grids used as the reference coordinate system. Geopotential is converted to geopotential height internally using standard gravity ($g = 9.80665$ m/s$^2$).

## Methodology & Algorithm

The core preprocessing logic employs parallel processing to rapidly iterate through sparse satellite observations.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryTextColor': '#000000', 'textColor': '#000000', 'nodeTextColor': '#000000'}}}%%

flowchart TD
    %% Styling
    classDef io fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef process fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef math fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px;
    classDef parallel fill:#fff3e0,stroke:#f57c00,stroke-width:2px,stroke-dasharray: 5 5;

    %% Data Inputs
    ERA5[(ERA5 Reference\nlat, lon, z)]:::io
    CS[(CloudSat HDF4\nSwath Directory)]:::io
    
    %% Setup
    Start([Execute: QR_Itp.py]) --> Setup[Parse Args & Load ERA5 z-levels]:::process
    ERA5 -.-> Setup
    Setup --> Pool{ProcessPoolExecutor\n8 Workers}:::process
    CS -.-> Pool

    %% Worker Box
    subgraph Parallel Swath Processing [Executed per .hdf file]
        direction TB
        Extract[Extract Swath Arrays:\nlon, lat, height, QR]:::io
        Assign[Horizontal Binning:\nMap Swath to ERA5 2D Grid]:::math
        Interp[Vertical Interpolation:\nAlign Swath QR to ERA5 z-levels]:::math
        Accum[Local Accumulation:\nSum & Count Valid Bins]:::process

        Extract --> Assign --> Interp --> Accum
    end

    %% Flow
    Pool ==>|Dispatch| Parallel Swath Processing
    Parallel Swath Processing ==>|Yield local_qr| Agg[Master Array Aggregation]:::process
    
    %% Finalization
    Agg --> Mean[Calculate Domain Mean:\nSum / Count]:::math
    Mean --> Export[(Export NetCDF4\nQSW, QLW)]:::io
```

### Radiative Heating Rate ($Q_r$)

The radiative heating rate ($Q_r$, variable qr) is stored in the native CloudSat files as 2-byte integers. To preserve numerical precision, the native values are scaled by a factor of 100. The script unpacks this by dividing the array by 100. Valid $Q_r$ values are bounded between -200 and 200 K/day. Any data points outside this physical range (including the native -999 fill value) are replaced with np.nan prior to interpolation.

### Spatial Binning & Interpolation

Horizontal Binning: Swath longitudes and latitudes are mapped to the nearest ERA5 grid boundaries using a vectorized search algorithm (np.searchsorted).
Vertical Interpolation: Because CloudSat radiation fluxes are vertically staggered, the script extracts the specific ERA5 column geopotential height ($Z$) for each valid bin and performs a linear interpolation (np.interp) to project the native CloudSat height levels onto the ERA5 vertical grid.

## Usage / Execution

1. Automated Multi-Year Processing (Recommended)
The provided bash script loops through the calendar (accounting for leap years), zero-pads the Julian dates, checks for missing directories, and queues the Python script using nice -n 19 to remain a polite background process on shared servers.
Make the script executable and run it in the background:

```bash
chmod +x run_processor.sh
nohup ./run_processor.sh > process_all_years.log 2>&1 &
```

2. Single-Day Execution
To run the script manually for a specific year and Julian date:

```bash
nice -n 19 python QR_Itp.py --year 2006 --date 170
```

## Output Structure

The final processed data is saved as a CF-compliant NetCDF4 file (.nc) using zlib compression (compression level 5) to minimize storage footprint.
Coordinates:
 - `time`: Standard YYYY-MM-DD timestamp derived from the Julian day.
 - `lev`: ERA5 pressure levels (hPa).
 - `lat`: ERA5 latitude grid (degrees North).
 - `lon`: ERA5 longitude grid (degrees East).
Data Variables:
 - `QSW`: Shortwave Radiative Heating Rate (K/day).
 - `QLW`: Longwave Radiative Heating Rate (K/day).