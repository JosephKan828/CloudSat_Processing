import numpy as np
import sys
sys.path.append("/data92/b11209013/CloudSat/Code/utils")
import grid

# Mock CloudSat Data
hgt_cs = np.array([0, 1000, 2000, 3000, 4000, 5000])
qr_cs = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])

print("CloudSat Heights:", hgt_cs)
print("CloudSat QR     :", qr_cs)
print("-" * 50)

# Scenario 1: ERA5 geopotential height is ascending (e.g. pressure 1000 to 100 hPa)
# Because pressure decreases with altitude, an ascending z_era5 means pressure goes from High to Low
z_era5_asc = np.array([500, 1500, 2500, 3500, 4500])
qr_asc = grid.interp_profile_to_era5_levels(hgt_cs, qr_cs, z_era5_asc)
print("Scenario 1: Ascending z_era5 (Pressure 1000 -> 100 hPa)")
print("z_era5 :", z_era5_asc)
print("Result :", qr_asc)
print("Expected:", np.array([0.5, 1.5, 2.5, 3.5, 4.5]))
print("Match? :", np.allclose(qr_asc, np.array([0.5, 1.5, 2.5, 3.5, 4.5])))
print("-" * 50)

# Scenario 2: ERA5 geopotential height is descending (e.g. pressure 100 to 1000 hPa)
# Because pressure increases with depth, a descending z_era5 means pressure goes from Low to High
z_era5_desc = np.array([4500, 3500, 2500, 1500, 500])
qr_desc = grid.interp_profile_to_era5_levels(hgt_cs, qr_cs, z_era5_desc)
print("Scenario 2: Descending z_era5 (Pressure 100 -> 1000 hPa)")
print("z_era5 :", z_era5_desc)
print("Result :", qr_desc)
print("Expected:", np.array([4.5, 3.5, 2.5, 1.5, 0.5]))
print("Match? :", np.allclose(qr_desc, np.array([4.5, 3.5, 2.5, 1.5, 0.5])))

