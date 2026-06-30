import numpy as np

def assign_rays_to_grid(
        lon_grid: np.ndarray,
        lat_grid: np.ndarray,
        lon_ray  : np.ndarray,
        lat_ray  : np.ndarray,
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Assign rays to grid

    Args:
        lon_grid: longitude grid
        lat_grid: latitude grid
        lon_ray: longitude of rays
        lat_ray: latitude of rays
    Returns:
        i_lat: latitude index
        i_lon: longitude index
        valid: valid index (boolean)
    """
    dx: float = lon_grid[1] - lon_grid[0]
    dy: float = lat_grid[1] - lat_grid[0]
    lon_edges: np.ndarray = np.linspace(lon_grid[0] - dx/2, lon_grid[-1] + dx/2, len(lon_grid) + 1)
    lat_edges: np.ndarray = np.linspace(lat_grid[0] - dy/2, lat_grid[-1] + dy/2, len(lat_grid) + 1)
    i_lon: np.ndarray = np.searchsorted(lon_edges, lon_ray, side="right") - 1
    i_lat: np.ndarray = np.searchsorted(lat_edges, lat_ray, side="right") - 1

    i_lon[i_lon == len(lon_grid)] = 0

    valid: np.ndarray = (
        (i_lon >= 0) & (i_lon < len(lon_grid)) &
        (i_lat >= 0) & (i_lat < len(lat_grid))
    )
    return i_lat, i_lon, valid

# Interpolate QR to ERA5 grid
def interp_profile_to_era5_levels(
        hgt_cs: np.ndarray,
        qr_cs: np.ndarray,
        z_era5: np.ndarray
        ) -> np.ndarray:
    """
    hgt_cs: (nbin,) CloudSat height [m]
    qr_cs:  (nbin,) QR at native bins
    z_era5:  (nlev,) ERA5 geopotential height at this grid column [m]
    """

    hgt = hgt_cs.astype(float)
    qr  = qr_cs.astype(float)
    # handle fill values, ensure monotonic height for np.interp
    good = np.isfinite(hgt) & np.isfinite(qr)
    hgt, qr = hgt[good], qr[good]
    if hgt.size < 2:
        return np.full(len(z_era5), np.nan)
    order = np.argsort(hgt)
    hgt, qr = hgt[order], qr[order]
    return np.interp(z_era5, hgt, qr, left=np.nan, right=np.nan)