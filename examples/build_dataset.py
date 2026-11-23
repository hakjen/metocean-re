"""
Merge the raw NORA3 files from download_nora3.py into the one dataset used
by the tests and examples (tests/data/NORA3_<name>_<years>.csv, e.g. NORA3_utsira_nord_2020_2022.csv).

    - wind and waves are hourly and used as they are
    - the 3-hourly atmosphere variables (temperature, humidity, density, TKE,
      sea surface temperature) are interpolated linearly in time to every hour
    - relative humidity is converted from percent to a fraction (0-1) where needed

Usage (from the project root):
    python examples/build_dataset.py
    python examples/build_dataset.py --lon 4.94 --lat 56.75 --name "Sorlige Nordsjo II"   # another point
"""

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data_raw"
DATA_DIR = ROOT / "tests" / "data"

WAVE_COLUMNS = ["hs", "tp", "hs_sea", "tp_sea", "hs_swell", "tp_swell"]
ATM3HR_PREFIXES = ("air_temperature_", "relative_humidity_", "density_", "tke_")


def read_raw(product, lon, lat):
    """Read the raw CSV file of a metocean-api product for one point."""
    files = sorted(RAW_DIR.glob(f"{product}_lon{lon}*lat{lat}*.csv"))
    if not files:
        raise FileNotFoundError(f"No file for {product} at {lon} E {lat} N in {RAW_DIR}. "
                                "Run download_nora3.py first.")
    return pd.read_csv(files[-1], comment="#", index_col=0, parse_dates=True)


def to_fraction(humidity):
    """Relative humidity as a fraction, whether it is given in percent or not."""
    return humidity / 100 if humidity.max() > 1.5 else humidity


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lon", type=float, default=4.54)
    parser.add_argument("--lat", type=float, default=59.27)
    parser.add_argument("--name", default="Utsira Nord")
    args = parser.parse_args()

    wind = read_raw("NORA3_wind_sub", args.lon, args.lat)
    wave = read_raw("NORA3_wave_sub", args.lon, args.lat)[WAVE_COLUMNS]
    atm3hr = read_raw("NORA3_atm3hr_sub", args.lon, args.lat)

    # Keep temperature, humidity, density, TKE and SST (the wind comes from NORA3_wind_sub)
    atm3hr = atm3hr[[c for c in atm3hr.columns if c.startswith(ATM3HR_PREFIXES) or c == "sea_surface_temperature"]]
    atm3hr = atm3hr.reindex(wind.index.union(atm3hr.index)).interpolate(method="time", limit=2).reindex(wind.index)

    df = pd.concat([wind, wave.reindex(wind.index), atm3hr], axis=1)
    for column in [c for c in df.columns if c.startswith("relative_humidity_")]:
        df[column] = to_fraction(df[column])

    years = f"{df.index[0].year}_{df.index[-1].year}"
    slug = "".join(c if c.isalnum() else "_" for c in args.name.lower())
    output = DATA_DIR / f"NORA3_{slug}_{years}.csv"
    header = (
        f"# NORA3 hindcast (MET Norway), {args.name}, nearest grid point to {args.lat} N {args.lon} E, "
        f"{years.replace('_', '-')}\n"
        "# Made with examples/download_nora3.py and examples/build_dataset.py from the metocean-api products\n"
        "# NORA3_wind_sub, NORA3_wave_sub and NORA3_atm3hr_sub (interpolated to hourly)\n"
    )
    with open(output, "w", newline="") as f:
        f.write(header)
        df.round(4).to_csv(f)
    print(f"{output}: {len(df)} rows, {len(df.columns)} columns, {df.isna().sum().sum()} missing values")
