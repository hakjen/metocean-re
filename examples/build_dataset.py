"""
Merge the raw NORA3 files from download_nora3.py into the one dataset used
by the tests and examples (tests/data/NORA3_utsira_nord_2020_2022.csv).

    - wind and waves are hourly and used as they are
    - the 3-hourly atmosphere variables (temperature, humidity, density, TKE,
      sea surface temperature) are interpolated linearly in time to every hour
    - relative humidity is converted from percent to a fraction (0-1) where needed

Usage (from the project root):
    python examples/build_dataset.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data_raw"
OUTPUT = ROOT / "tests" / "data" / "NORA3_utsira_nord_2020_2022.csv"

WAVE_COLUMNS = ["hs", "tp", "hs_sea", "tp_sea", "hs_swell", "tp_swell"]
ATM3HR_PREFIXES = ("air_temperature_", "relative_humidity_", "density_", "tke_")


def read_raw(product):
    """Read the (single) raw CSV file of a metocean-api product."""
    files = sorted(RAW_DIR.glob(f"{product}_lon*.csv"))
    if not files:
        raise FileNotFoundError(f"No file for {product} in {RAW_DIR}. Run download_nora3.py first.")
    return pd.read_csv(files[-1], comment="#", index_col=0, parse_dates=True)


def to_fraction(humidity):
    """Relative humidity as a fraction, whether it is given in percent or not."""
    return humidity / 100 if humidity.max() > 1.5 else humidity


if __name__ == "__main__":
    wind = read_raw("NORA3_wind_sub")
    wave = read_raw("NORA3_wave_sub")[WAVE_COLUMNS]
    atm3hr = read_raw("NORA3_atm3hr_sub")

    # Keep temperature, humidity, density, TKE and SST (the wind comes from NORA3_wind_sub)
    atm3hr = atm3hr[[c for c in atm3hr.columns if c.startswith(ATM3HR_PREFIXES) or c == "sea_surface_temperature"]]
    atm3hr = atm3hr.reindex(wind.index.union(atm3hr.index)).interpolate(method="time", limit=2).reindex(wind.index)

    df = pd.concat([wind, wave.reindex(wind.index), atm3hr], axis=1)
    for column in [c for c in df.columns if c.startswith("relative_humidity_")]:
        df[column] = to_fraction(df[column])

    header = (
        "# NORA3 hindcast (MET Norway), Utsira Nord, nearest grid point to 59.27 N 4.54 E, 2020-2022\n"
        "# Made with examples/download_nora3.py and examples/build_dataset.py from the metocean-api products\n"
        "# NORA3_wind_sub, NORA3_wave_sub and NORA3_atm3hr_sub (interpolated to hourly)\n"
    )
    with open(OUTPUT, "w", newline="") as f:
        f.write(header)
        df.round(4).to_csv(f)
    print(f"{OUTPUT}: {len(df)} rows, {len(df.columns)} columns, {df.isna().sum().sum()} missing values")
