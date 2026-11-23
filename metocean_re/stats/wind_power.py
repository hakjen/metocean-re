"""
Power output and energy production.

All functions take a metocean DataFrame (e.g. NORA3 from metocean-api) and
a turbine (rated power in MW, a name, or a Turbine - see stats/turbines.py).
By default the wind speed at the turbine's hub height is used; pass
`var='wind_speed_100m'` (or any other column) to use a specific column instead.

Units: power in MW, energy in MWh (per year where noted).
"""

from math import gamma

import numpy as np
import pandas as pd

from . import turbines
from .profile import hub_height_wind_speed

HOURS_PER_YEAR = 365.25 * 24


def wind_speed(data, turbine=None, var=None):
    """Wind speed [m/s] seen by the turbine: column `var`, or hub-height wind speed."""
    if var is not None:
        return data[var]
    return hub_height_wind_speed(data, turbine)


def power_output(data, turbine=None, var=None):
    """Power output time series [MW]."""
    t = turbines.get(turbine)
    u = wind_speed(data, t, var)
    return pd.Series(t.power(u), index=data.index, name="power_MW")


def capacity_factor(power, turbine=None):
    """Mean power divided by rated power (0-1)."""
    return power.mean() / turbines.get(turbine).rated_power


def annual_energy_production(data, turbine=None, var=None):
    """
    Gross annual energy production (AEP) [MWh/year], before any losses.

    Computed as mean power over the whole time series times the number of
    hours in a year, so it works for any time step.
    """
    return power_output(data, turbine, var).mean() * HOURS_PER_YEAR


def energy_per_year(data, turbine=None, var=None):
    """Gross energy production [MWh] for each calendar year, to see the year-to-year variation."""
    power = power_output(data, turbine, var)
    return (power.groupby(power.index.year).mean() * HOURS_PER_YEAR).rename("energy_MWh")


def fit_weibull(wind_speed):
    """
    Fit a 2-parameter Weibull distribution to wind speeds, using the
    empirical moment approximation k = (std / mean)^-1.086.

    Source: Justus et al. (1978), J. Applied Meteorology 17, 350-353,
    method 3, eqs. (15)-(16), p. 351.

    Returns (shape k, scale c [m/s]).
    """
    u = np.asarray(wind_speed, dtype=float)
    u = u[~np.isnan(u)]
    shape = (u.std() / u.mean()) ** -1.086
    scale = u.mean() / gamma(1 + 1 / shape)
    return shape, scale


def weibull_pdf(u, shape, scale):
    """Weibull probability density at wind speed(s) u."""
    u = np.asarray(u, dtype=float)
    return (shape / scale) * (u / scale) ** (shape - 1) * np.exp(-((u / scale) ** shape))
