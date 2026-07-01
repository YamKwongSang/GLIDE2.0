import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.tri import Triangulation, LinearTriInterpolator
import tkinter as tk
from tkinter import filedialog

def mapper(lon1, lon2, lat1, lat2, er1, er2,
        res, minres, input_dir):
    region = [lon1, lon2, lat1, lat2]
    h = ((lat2 - lat1) /
         (lon2 - lon1) /
         np.cos(np.deg2rad(lat2)) * 7 + 2)

    color_nodes = [
        (0.00, '#5a1cb3'),
        (0.12, '#1b56ed'),
        (0.25, '#00b0d4'),
        (0.40, '#10c476'),
        (0.55, '#f7cb2d'),
        (0.70, '#f26d22'),
        (0.85, '#e32424'),
        (1.00, '#990b0b')
    ]

    cmap2 = mcolors.LinearSegmentedColormap.from_list(
        "scientific_geo_flux",
        color_nodes
    )

    x_router = np.arange(lon1, lon2, res)
    y_router = np.arange(lat1, lat2, res)

    grid_x, grid_y = np.meshgrid(x_router, y_router)

    # Automatically create maps directory
    output_dir = os.path.join(input_dir, "maps")
    os.makedirs(output_dir, exist_ok=True)

    target_files = sorted(
        f for f in glob.glob(os.path.join(input_dir, "*.csv"))
        if os.path.basename(f)[0].isdigit()
    )

    if len(target_files) == 0:
        return False, "No valid CSV files found."

    for file_path in target_files:

        file_name = os.path.basename(file_path)

        try:
            data = np.genfromtxt(
                file_path,
                delimiter=",",
                names=True,
                dtype=None,
                encoding="utf-8"
            )

            lon = data["longitude"]
            lat = data["latitude"]
            exhumation = data["exhumation_rate"]
            rv = data["reduced_variance"]
            resolution = data["time_resolution"]

        except Exception as e:
            print(f"\nFailed to read file: {file_name}")
            print(e)
            continue

        try:
            valid = (
                np.isfinite(lon)
                & np.isfinite(lat)
                & np.isfinite(exhumation)
                & np.isfinite(rv)
                & np.isfinite(resolution)
            )

            lon_valid = lon[valid]
            lat_valid = lat[valid]
            exhumation_valid = exhumation[valid]
            rv_valid = rv[valid]
            resolution_valid = resolution[valid]

            if len(lon_valid) < 3:
                raise ValueError("Less than 3 valid points.")

            tri = Triangulation(
                lon_valid,
                lat_valid
            )

            exhumation_interp = LinearTriInterpolator(
                tri,
                exhumation_valid
            )

            rv_interp = LinearTriInterpolator(
                tri,
                rv_valid
            )

            resolution_interp = LinearTriInterpolator(
                tri,
                resolution_valid
            )

            grid_exhumation = np.asarray(
                exhumation_interp(grid_x, grid_y)
            )

            grid_rv = np.asarray(
                rv_interp(grid_x, grid_y)
            )

            grid_resolution = np.asarray(
                resolution_interp(grid_x, grid_y)
            )

            if np.ma.isMaskedArray(grid_exhumation):
                grid_exhumation = grid_exhumation.filled(np.nan)

            if np.ma.isMaskedArray(grid_rv):
                grid_rv = grid_rv.filled(np.nan)

            if np.ma.isMaskedArray(grid_resolution):
                grid_resolution = grid_resolution.filled(np.nan)

        except Exception as e:
            print(f"\nInterpolation failed: {file_name}")
            print(e)
            continue

        mask = grid_resolution < minres

        grid_exhumation[mask] = np.nan
        grid_rv[mask] = np.nan
        grid_resolution[mask] = np.nan

        current_cmap = cmap2.copy()

        lat_mid = (lat1 + lat2) / 2.0
        aspect_ratio = 1.0 / np.cos(np.radians(lat_mid))

        fig, (ax1, ax2, ax3) = plt.subplots(
            1,
            3,
            figsize=(20, h),
            dpi=300
        )

        for ax in (ax1, ax2, ax3):
            ax.tick_params(
                axis='both',
                which='both',
                direction='in'
            )

        # Exhumation Rate
        im1 = ax1.imshow(
            grid_exhumation,
            extent=region,
            origin='lower',
            cmap=current_cmap,
            aspect=aspect_ratio,
            vmin=er1,
            vmax=er2
        )

        ax1.set_title("Exhumation Rate")

        extend_mode = "max" if er1 <= 0 else "both"

        fig.colorbar(
            im1,
            ax=ax1,
            label="ER (km/Myr)",
            orientation='horizontal',
            pad=0.05,
            shrink=0.7,
            aspect=30,
            extend=extend_mode
        )

        # RV
        im2 = ax2.imshow(
            grid_rv,
            extent=region,
            origin='lower',
            cmap=current_cmap.reversed(),
            aspect=aspect_ratio,
            vmin=0,
            vmax=1
        )

        ax2.set_title("Reduced Variance")

        fig.colorbar(
            im2,
            ax=ax2,
            label="RV",
            orientation='horizontal',
            pad=0.05,
            shrink=0.7,
            aspect=30
        )

        # Resolution
        im3 = ax3.imshow(
            grid_resolution,
            extent=region,
            origin='lower',
            cmap=current_cmap,
            aspect=aspect_ratio,
            vmin=0,
            vmax=1
        )

        ax3.set_title("Time Resolution")

        fig.colorbar(
            im3,
            ax=ax3,
            label="Resolution",
            orientation='horizontal',
            pad=0.05,
            shrink=0.7,
            aspect=30
        )

        txt_file_path = os.path.splitext(file_path)[0] + ".txt"

        if os.path.exists(txt_file_path):
            try:
                with open(
                    txt_file_path,
                    "r",
                    encoding="utf-8"
                ) as tf:

                    text_content = tf.read().strip()

                words = text_content.split()

                if len(words) >= 4:
                    title_text = " ".join(words[-4:])
                else:
                    title_text = text_content

                fig.suptitle(
                    title_text,
                    fontsize=16,
                    y=0.98,
                    fontweight='bold'
                )

            except Exception as e:
                print(f"\nFailed to read title file: {file_name}")
                print(e)

        plt.tight_layout()

        basename = os.path.splitext(
            os.path.basename(file_path)
        )[0]

        output_pdf = os.path.join(
            output_dir,
            f"{basename}.pdf"
        )
        plt.savefig(output_pdf, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Completed: {basename}.pdf")

    return True, output_dir

def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        title="Select CSV Folder"
    )
    root.destroy()
    return folder

def main():
    print("=" * 60)
    print("Exhumation Maps Generator")
    print("=" * 60)
    lon1 = float(input("Minimum Longitude: "))
    lon2 = float(input("Maximum Longitude: "))

    lat1 = float(input("Minimum Latitude: "))
    lat2 = float(input("Maximum Latitude: "))

    er1 = float(input("Rates Minimum (km/Myr): "))
    er2 = float(input("Rates Maximum (km/Myr): "))

    res = float(input("Grid Resolution (degree): "))
    minres = float(input("Minimum Time Resolution: "))

    print("\nSelect input folder...")
    input_dir = select_folder()
    print("\nStart to mapping")

    if not input_dir:
        print("No folder selected.")
        return

    success, message = mapper(lon1, lon2, lat1, lat2,
        er1, er2, res, minres, input_dir)

    if success:
        print("\nMaps generated successfully.")
        print(f"Output folder:\n{message}")
    else:
        print(f"\nError: {message}")
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()