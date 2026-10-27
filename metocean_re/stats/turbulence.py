"""
Turbulence intensity (TI) and its effect on power production.

    TI = sigma_u / U

where sigma_u is the standard deviation of the wind speed and U the mean
wind speed. NORA3 does not give sigma_u, but it gives the turbulent kinetic
energy (TKE) per unit mass,

    k = 1/2 * (sigma_u^2 + sigma_v^2 + sigma_w^2)

With the usual ratios sigma_v = 0.8 sigma_u and sigma_w = 0.5 sigma_u
(IEC 61400-1:2019, Annex C, Kaimal model):

    k = 1/2 * sigma_u^2 * (1 + 0.8^2 + 0.5^2)  ->  sigma_u = sqrt(k / 0.945)

Note: NORA3 TKE is model output (a 3 km weather model, 3-hourly), so it
gives the large-scale turbulence level, not 10-minute values from a mast.
"""

import numpy as np
import pandas as pd

from . import turbines
from .profile import hub_height_wind_speed, value_at_height

# Ratios sigma_v / sigma_u and sigma_w / sigma_u (IEC 61400-1:2019, Annex C)
SIGMA_V_RATIO = 0.8
SIGMA_W_RATIO = 0.5

# Reference turbulence intensity at 15 m/s for the IEC turbine classes
# A, B and C (IEC 61400-1:2019, Table 1)
IEC_TI_REF = {"A": 0.16, "B": 0.14, "C": 0.12}


def sigma_u_from_tke(tke):
    """Standard deviation of the along-wind speed [m/s] from TKE [m2/s2]."""
    return np.sqrt(2 * tke / (1 + SIGMA_V_RATIO**2 + SIGMA_W_RATIO**2))


def hub_height_sigma_u(data, turbine=None):
    """sigma_u [m/s] at hub height (TKE interpolated linearly between the NORA3 heights)."""
    tke = value_at_height(data, turbines.get(turbine).hub_height, "tke").clip(lower=0)
    return sigma_u_from_tke(tke).rename("sigma_u")


def turbulence_intensity(data, turbine=None, min_speed=3.0):
    """
    Turbulence intensity at hub height (0-1). Time steps with wind below
    min_speed [m/s] are set to NaN, since TI is not meaningful in weak wind.
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t)
    ti = hub_height_sigma_u(data, t) / u
    return ti.where(u >= min_speed).rename("turbulence_intensity")


def iec_normal_turbulence(wind_speed, turbine_class="A"):
    """
    Turbulence intensity of the IEC normal turbulence model (NTM), 90 % quantile:

        sigma_1 = I_ref * (0.75 * V + 5.6),   TI = sigma_1 / V

    Source: IEC 61400-1:2019, Wind energy generation systems - Part 1:
    Design requirements, section 6.3.2.3.
    """
    v = np.asarray(wind_speed, dtype=float)
    return IEC_TI_REF[turbine_class] * (0.75 * v + 5.6) / v


def turbulent_power(turbine, wind_speed, sigma_u, n_points=20):
    """
    Mean power [MW] when the wind varies around the mean wind_speed U with
    standard deviation sigma_u (normal distribution):

        P_turb(U) = integral P(u) * N(u; U, sigma_u) du

    This lowers the power near rated speed (the curve bends down there) and
    raises it near cut-in (the curve bends up).

    Source: Albers (2010), "Turbulence and shear normalisation of wind
    turbine power curve", Proc. EWEC 2010, sec. 3.1, eq. (1) (the "Normal
    Distribution Model"), applied to a theoretical power curve as in sec. 5.1.
    The turbine's power curve is used as the zero-turbulence power curve,
    without Albers' adjustment to measured data (sec. 3.2). The method is
    included in IEC 61400-12-1:2017, Annex M.

    The integral is computed with Gauss-Hermite quadrature (n_points points).
    """
    t = turbines.get(turbine)
    u = np.asarray(wind_speed, dtype=float)[:, np.newaxis]
    sigma = np.broadcast_to(np.asarray(sigma_u, dtype=float), u.shape[:1])[:, np.newaxis]

    # Gauss-Hermite nodes x and weights w: integral f(x) exp(-x^2) dx = sum w f(x)
    x, w = np.polynomial.hermite.hermgauss(n_points)
    # Single gusts above cut-out give rated power; the turbine only shuts
    # down when the mean wind is above cut-out
    samples = np.clip(u + np.sqrt(2) * sigma * x, 0, t.cut_out)
    power = t.power(samples)
    power[np.broadcast_to(u > t.cut_out, power.shape)] = 0.0
    return (power * w).sum(axis=1) / np.sqrt(np.pi)


def power_with_turbulence(data, turbine=None):
    """Power output [MW] taking the turbulence at hub height into account (see turbulent_power)."""
    t = turbines.get(turbine)
    power = turbulent_power(t, hub_height_wind_speed(data, t), hub_height_sigma_u(data, t))
    return pd.Series(power, index=data.index, name="power_MW")
