from pyhdf.HC  import HC
from pyhdf.SD  import SD, SDC, HDF4Error
from pyhdf.VS  import VS
from pyhdf.HDF import HDF

import numpy as np
import pandas as pd
import xarray as xr

def load_data(fname) -> tuple[np.ndarray, ...]:
    from pyhdf.VS  import VS

    hdf = HDF(fname, SDC.READ)

    vs = hdf.vstart()
    lat = np.stack(vs.attach("Latitude")[:]).squeeze()
    lon = np.stack(vs.attach("Longitude")[:]).squeeze()
    vs.end()

    lon[lon <= 0] += 360
    lon = lon % 360
    
    file_sd = SD(fname, SDC.READ)
    # 100.0 is scale factor, check in official website of CloudSat
    hgt = np.array(file_sd.select("Height")[:])
    # 0 of QR stands for shortwave radiation
    qsw = np.array(file_sd.select("QR")[0][:])
    # 1 of QR stands for longwave radiation
    qlw = np.array(file_sd.select("QR")[1][:])
    file_sd.end()

    # filter false data
    qsw = np.where(
        (qsw<= -200) | (qsw>= 200),
        np.nan,
        qsw
    ) / 100.0
    qlw = np.where(
        (qlw<= -200) | (qlw>= 200),
        np.nan,
        qlw
    ) / 100.0

    return lon, lat, hgt, qlw, qsw

def save_data(
    year: int,
    date: int,
    data: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    lev: np.ndarray,
    data_dir: str,
) -> None:

    """
    Saves the interpolated 4D radiative heating array to a compressed NetCDF file.
    Converts Julian day to standard YYYY-MM-DD format for the filename.
    """

    # 1. Date Conversion: Julian Day to YYYY-MM-DD
    # %Y is 4-digit year, %j is 3-digit Julian day (1-365/366)
    time_coord = pd.to_datetime(f"{year}{date:03d}", format="%Y%j")
    date_str = time_coord.strftime("%Y-%m-%d") # e.g., "2006-06-19"

    # 2. Extract Data Variables
    qsw_mean = np.expand_dims(data[:, :, :, 0], axis=0)
    qlw_mean = np.expand_dims(data[:, :, :, 1], axis=0)

    # 3. Build xarray Dataset
    ds_out = xr.Dataset(
        data_vars=dict(
            QSW=(["time", "lev", "lat", "lon"], qsw_mean, {"units": "K/day", "long_name": "Shortwave Radiative Heating"}),
            QLW=(["time", "lev", "lat", "lon"], qlw_mean, {"units": "K/day", "long_name": "Longwave Radiative Heating"}),
        ),
        coords=dict(
            time=(["time"], [time_coord]),
            lat=(["lat"], lat, {"units": "degrees_north"}),
            lon=(["lon"], lon, {"units": "degrees_east"}),
            level=(["lev"], lev, {"units": "hectopascal"}),
        ),
        attrs=dict(
            description="CloudSat Radiative Heating interpolated to ERA5 spatial grid",
            history="Processed via multiprocessing interpolation",
            source_date=f"Year: {year}, Julian Day: {date}"
        )
    )

    # 4. Apply Compression Settings
    encoding_settings = {
        "QSW": {"zlib": True, "complevel": 5, "_FillValue": np.nan},
        "QLW": {"zlib": True, "complevel": 5, "_FillValue": np.nan},
        "time": {"units": "days since 1900-01-01 00:00:00"} # Standard CF compliance
    }

    # 5. Save to Disk
    ds_out.to_netcdf(data_dir, encoding=encoding_settings)
