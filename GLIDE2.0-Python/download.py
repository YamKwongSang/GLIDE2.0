import numpy as np
import ee
import tkinter as tk
from tkinter import filedialog

def initialize_gee(project=None):
    """
    Initialize Google Earth Engine.
    """
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()

    except Exception:
        print("Earth Engine authentication required...")
        ee.Authenticate()

        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()


def choose_output_file():
    """
    Open Save-As dialog.
    """
    root = tk.Tk()
    root.withdraw()

    filename = filedialog.asksaveasfilename(
        title="Save DEM Output",
        defaultextension=".xyz",
        filetypes=[
            ("xyz files", "*.xyz"),
            ("All files", "*.*")
        ]
    )

    root.destroy()

    return filename


def get_dem_source(flag):
    """
    Select DEM source.
    """
    flag = flag.strip().upper()

    if flag == "N":
        print("Using NASADEM")
        dem = ee.Image(
            "NASA/NASADEM_HGT/001"
        ).select("elevation")
        band_name = "elevation"

    elif flag == "C":
        print("Using Copernicus GLO-30")
        dem = (
            ee.ImageCollection("COPERNICUS/DEM/GLO30")
            .mosaic().select("DEM")
        )
        band_name = "DEM"

    elif flag == "S":
        print("Using SRTM")
        dem = ee.Image("USGS/SRTMGL1_003").select("elevation")
        band_name = "elevation"

    else:
        raise ValueError("DEM type must be N, C, or S.")
    return dem, band_name

def extract_dem_data(lon_min, lon_max,
        lat_min, lat_max, step,
        dem_flag, save_path, project=None):
    initialize_gee(project)

    try:
        print("Preparing DEM...")
        dem, band_name = get_dem_source(dem_flag)
        region = ee.Geometry.Rectangle(
            [lon_min, lat_min, lon_max, lat_max]
        )
        scale_m = step * 111000.0
        dem_resampled = (
            dem
            .resample("bilinear")
            .reproject(
                crs="EPSG:4326",
                scale=scale_m
            )
        )
        print("Downloading grid from GEE...")
        result = (
            dem_resampled
            .sampleRectangle(region=region)
            .getInfo()
        )
        arr = np.array(
            result["properties"][band_name],
            dtype=np.float32
        )
        nrows, ncols = arr.shape

        print(
            f"Grid received: {nrows} rows × {ncols} cols"
        )
        lons = np.linspace(lon_min, lon_max, ncols)
        lats = np.linspace(lat_max, lat_min, nrows)
        print("Writing output...")

        with open(
            save_path,
            "w",
            encoding="utf-8"
        ) as f:

            for i, lat in enumerate(lats):
                for j, lon in enumerate(lons):
                    elevation = arr[i, j]
                    if np.isnan(elevation):
                        elevation = -9999
                    f.write(
                        f"{lon:.6f}\t"
                        f"{lat:.6f}\t"
                        f"{elevation:.0f}\n"
                    )

        print(
            f"Finished. "
            f"{nrows*ncols:,} points saved."
        )

        print(f"Output saved to:\n{save_path}")

    except Exception as e:
        print(f"\nERROR: {e}")


def main():
    try:
        print("=" * 60)
        print("Google Earth Engine: download DEM as .xyz")
        print("=" * 60)

        project = input(
            "GEE Project ID "
            "(press Enter if not needed): "
        ).strip()

        if project == "":
            project = None

        lon_min = float(input("Minimum longitude: "))
        lon_max = float(input("Maximum longitude: "))
        lat_min = float(input("Minimum latitude : "))
        lat_max = float(input("Maximum latitude : "))
        step = float(input("Grid spacing (degree): "))

        print("\nDEM Source:")
        print("N = NASADEM")
        print("C = Copernicus GLO-30")
        print("S = SRTM")

        dem_flag = input("Select DEM source: ")

        print("Choose the saving path:")
        save_path = choose_output_file()

        if not save_path:
            print("\nNo output file selected.")
            return

        extract_dem_data(
            lon_min, lon_max,
            lat_min, lat_max,
            step,
            dem_flag,
            save_path,
            project
        )

    finally:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()