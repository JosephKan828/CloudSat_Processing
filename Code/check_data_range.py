import argparse
import numpy as np
import matplotlib.pyplot as plt
from pyhdf.SD import SD, SDC

def main():
    parser = argparse.ArgumentParser(description="Check the data range of raw CloudSat variables.")
    parser.add_argument(
        "--file", 
        type=str, 
        default="/work/DATA/Satellite/CloudSat/2006/256/2006256035706_02007_CS_2B-FLXHR-LIDAR_GRANULE_P2_R05_E02_F00.hdf",
        help="Path to the raw CloudSat HDF file"
    )
    parser.add_argument(
        "--var",
        type=str,
        default="QR",
        help="Variable to check the data range for (e.g., QR, Height)."
    )
    args = parser.parse_args()

    print(f"Loading raw CloudSat data from: {args.file}")
    
    file_sd = SD(args.file, SDC.READ)
    
    try:
        var_obj = file_sd.select(args.var)
        data = np.array(var_obj[:])
        
        print("-" * 50)
        print(f"Variable: {args.var}")
        print(f"Data type: {data.dtype}")
        print(f"Shape: {data.shape}")
        print(f"Raw Data Range - Min: {np.nanmin(data)}, Max: {np.nanmax(data)}")
        
        # Plot histogram of data before filtering
        plt.figure(figsize=(10, 6))
        # Flatten the data and drop NaNs for the histogram
        plot_data = data.flatten()
        plot_data = plot_data[~np.isnan(plot_data)]
        plt.hist(plot_data, bins=100, color='blue', alpha=0.7, edgecolor='black')
        plt.title(f"Histogram of raw '{args.var}' data (before filtering)")
        plt.xlabel("Value")
        plt.ylabel("Frequency")
        plt.yscale("log") # Use log scale because missing values or outliers might dominate
        plt.grid(axis='y', alpha=0.75)
        plot_filename = f"histogram_raw_{args.var}.png"
        plt.savefig(plot_filename)
        print(f"Saved histogram plot to: {plot_filename}")
        plt.close()
        
        # If the variable is QR, we can also show the shortwave/longwave ranges
        if args.var == "QR":
            qsw = np.array(var_obj[0][:])
            qlw = np.array(var_obj[1][:])
            
            # The official scale factor is 100.0, and -9999 is missing data
            # values outside [-20000, 20000] are out of bounds.
            valid_qsw = qsw[(qsw > -20000) & (qsw < 20000) & (qsw != -9999)]
            valid_qlw = qlw[(qlw > -20000) & (qlw < 20000) & (qlw != -9999)]
            
            print("-" * 50)
            print("Filtered Data Range (excluding -9999 and out-of-bounds):")
            if valid_qsw.size > 0:
                print(f"Valid QSW (Shortwave) - Min: {valid_qsw.min() / 100.0:.3f}, Max: {valid_qsw.max() / 100.0:.3f} (scaled by 1/100)")
            else:
                print("No valid QSW data found in this file.")
                
            if valid_qlw.size > 0:
                print(f"Valid QLW (Longwave)  - Min: {valid_qlw.min() / 100.0:.3f}, Max: {valid_qlw.max() / 100.0:.3f} (scaled by 1/100)")
            else:
                print("No valid QLW data found in this file.")

    except Exception as e:
        print(f"Error reading variable '{args.var}': {e}")
        
    finally:
        file_sd.end()

if __name__ == "__main__":
    main()
