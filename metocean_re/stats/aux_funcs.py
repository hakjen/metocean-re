"""
Helper functions: reading metocean data.

The functions in metocean-re use NORA3 column names, as written by
metocean-api (heights z in m):

    wind_speed_{z}m          wind speed [m/s]
    wind_direction_{z}m      wind direction [deg, from]
    air_temperature_{z}m     air temperature [K]
    relative_humidity_{z}m   relative humidity [0-1]
    density_{z}m             air density [kg/m3]
    tke_{z}m                 turbulent kinetic energy [m2/s2]
    sea_surface_temperature  [K]
    hs, tp                   significant wave height [m], peak period [s]

See examples/download_nora3.py and examples/build_dataset.py for how the
test dataset in tests/data was made.
"""

import pandas as pd


def read_metocean_csv(file):
    """
    Read a CSV file written by metocean-api (or by examples/build_dataset.py).

    The first column is the time: ISO 8601 (2021-07-27 07:00), dd.mm.yyyy
    (27.07.2021 07:00), or dd/mm/yyyy or mm/dd/yyyy when some day is above 12
    so the order is clear. The rows are sorted by time.
    """
    df = pd.read_csv(file, comment="#", index_col=0)
    df.index = parse_time(df.index)
    df.index.name = "time"
    return df.sort_index()


def parse_time(values):
    """
    Times as a DatetimeIndex, from ISO 8601, dd.mm.yyyy, dd/mm/yyyy or mm/dd/yyyy.

    Dots mean day first (27.07.2021). With slashes both orders are used, so
    the order is taken from the data: a first number above 12 must be the day
    (27/07/2021), a second number above 12 must be the day (07/27/2021). If
    all days are 12 or less the order cannot be known, and this gives an error.
    """
    text = pd.Index(values).astype(str).str.strip()
    try:
        return pd.DatetimeIndex(pd.to_datetime(text, format="ISO8601"))
    except ValueError:
        pass

    date = text.str.split(" ").str[0]
    if date.str.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}").all():
        day_first = True
    elif date.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}").all():
        first, second = (date.str.split("/").str[i].astype(int) for i in (0, 1))
        if (first > 12).any():
            day_first = True
        elif (second > 12).any():
            day_first = False
        else:
            raise ValueError(f"Cannot tell if the dates are dd/mm/yyyy or mm/dd/yyyy (e.g. '{text[0]}'), "
                             "since no day is above 12. Use ISO 8601 (yyyy-mm-dd) or dd.mm.yyyy.")
    else:
        raise ValueError(f"Unknown time format (e.g. '{text[0]}'). "
                         "Use ISO 8601 (yyyy-mm-dd hh:mm) or dd.mm.yyyy hh:mm.")
    return pd.DatetimeIndex(pd.to_datetime(text, format="mixed", dayfirst=day_first))
