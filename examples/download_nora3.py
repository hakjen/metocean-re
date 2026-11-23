"""
Download NORA3 data for one location with metocean-api and save the raw CSV files.

Fast products (monthly files on thredds.met.no):
    NORA3_wind_sub     wind speed and direction, 10-750 m, hourly
    NORA3_wave_sub     significant wave height, peak period etc., hourly
    NORA3_atm3hr_sub   temperature, humidity, density and TKE at 50-300 m, sea surface temperature, 3-hourly

Slow product (one file per hour, ~10 s each - only for short periods):
    NORA3_offshore_wind   includes the Obukhov length calculated from the surface fluxes

Usage (from the project root, with metocean-api installed):
    python examples/download_nora3.py                      # fast products, Utsira Nord 2020-2022
    python examples/download_nora3.py --offshore-wind 2020-01-01 2020-01-10

Afterwards, run examples/build_dataset.py to merge the files into one dataset.
Note: metocean-api does not allow parallel downloads from NORA3.
"""

import argparse
import os
from pathlib import Path

from metocean_api import ts

RAW_DIR = Path(__file__).resolve().parent.parent / "data_raw"

# Utsira Nord, planned floating offshore wind area
LON, LAT = 4.54, 59.27

FAST_PRODUCTS = ["NORA3_wind_sub", "NORA3_wave_sub", "NORA3_atm3hr_sub"]


def download(product, start, end, lon=LON, lat=LAT):
    """Download one product to RAW_DIR as CSV. Returns the file path."""
    RAW_DIR.mkdir(exist_ok=True)
    os.chdir(RAW_DIR)  # metocean-api writes to the current directory
    series = ts.TimeSeries(lon=lon, lat=lat, start_time=start, end_time=end, product=product)
    series.import_data(save_csv=True, save_nc=False, use_cache=True)
    return RAW_DIR / series.datafile


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2022-12-31")
    parser.add_argument("--offshore-wind", nargs=2, metavar=("START", "END"),
                        help="download NORA3_offshore_wind (slow) for this period instead")
    args = parser.parse_args()

    if args.offshore_wind:
        print(download("NORA3_offshore_wind", *args.offshore_wind))
    else:
        for product in FAST_PRODUCTS:
            print(download(product, args.start, args.end))
