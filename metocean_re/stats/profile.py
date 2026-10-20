"""
Vertical wind profile: wind speed and direction over the height of the rotor.

NORA3 has wind at 10, 20, 50, 100, 250, 500 and 750 m, which covers the
whole rotor of the turbines in this project. Between two NORA3 heights the
wind speed is interpolated with the power law

    u(z) = u_1 * (z / z_1) ** alpha,   alpha = ln(u_2 / u_1) / ln(z_2 / z_1)

i.e. a straight line between the two heights in a log-log plot. Outside the
NORA3 heights the power law of the nearest pair of heights is extended.

Three different things are computed from the profile:

    rotor_wind_speeds()            wind at the bottom, hub and top of the rotor,
                                   the difference top - bottom and the shear
                                   exponent across the rotor (descriptive)
    rotor_equivalent_wind_speed()  one wind speed that represents the whole
                                   rotor (used for the wind shear and veer losses)
    wind_veer()                    change in wind direction from bottom to top
"""

import re

import numpy as np
import pandas as pd

from . import turbines


def measured_heights(data, var="wind_speed"):
    """
    Heights available for a variable, as {height [m]: column name}.

    E.g. measured_heights(df) -> {10: 'wind_speed_10m', 20: 'wind_speed_20m', ...}
    """
    pattern = re.compile(rf"^{var}_(\d+)m$")
    heights = {int(m.group(1)): col for col in data.columns if (m := pattern.match(col))}
    if not heights:
        raise ValueError(f"No columns named like '{var}_100m' found in the data.")
    return dict(sorted(heights.items()))


def _interpolate(values, heights, z, log=False):
    """
    Interpolate between heights, for one target height z.

    values  : array (time, heights)
    log     : interpolate in log(value) vs log(height), i.e. the power law
              (for wind speed); otherwise linearly in value vs height.
    Outside the given heights the nearest two heights are extrapolated.
    """
    heights = np.asarray(heights, dtype=float)
    j = int(np.clip(np.searchsorted(heights, z) - 1, 0, len(heights) - 2))
    z1, z2 = heights[j], heights[j + 1]
    v1, v2 = values[:, j], values[:, j + 1]

    if log:
        v1, v2 = np.log(np.maximum(v1, 0.01)), np.log(np.maximum(v2, 0.01))
        weight = np.log(z / z1) / np.log(z2 / z1)
        return np.exp(v1 + weight * (v2 - v1))
    weight = (z - z1) / (z2 - z1)
    return v1 + weight * (v2 - v1)


def value_at_height(data, z, var="wind_speed"):
    """
    Any profile variable at height z [m], e.g. 'wind_speed', 'tke', 'density'.

    Wind speed is interpolated with the power law, other variables linearly.
    """
    heights = measured_heights(data, var)
    if z in heights:
        return data[heights[z]].rename(var)

    values = data[list(heights.values())].to_numpy(dtype=float)
    if var == "wind_direction":
        # Unwrap so that e.g. 350 deg -> 10 deg is a change of +20 deg, not -340 deg
        values = np.degrees(np.unwrap(np.radians(values), axis=1))
        result = _interpolate(values, list(heights), z) % 360
    else:
        result = _interpolate(values, list(heights), z, log=(var == "wind_speed"))
    return pd.Series(result, index=data.index, name=var)


def wind_speed_at_height(data, z):
    """Wind speed [m/s] at height z [m]."""
    return value_at_height(data, z, "wind_speed")


def hub_height_wind_speed(data, turbine=None):
    """Wind speed [m/s] at the hub height of the turbine."""
    return wind_speed_at_height(data, turbines.get(turbine).hub_height)


def power_law(u_ref, z_ref, z, alpha):
    """Wind speed at height z [m], from wind speed u_ref at height z_ref."""
    return u_ref * (z / z_ref) ** alpha


def shear_exponent(data, z_low, z_high):
    """Shear exponent alpha between two heights, for each time step."""
    u_low = wind_speed_at_height(data, z_low)
    u_high = wind_speed_at_height(data, z_high)
    alpha = np.log(u_high / u_low) / np.log(z_high / z_low)
    return alpha.rename("shear_exponent")


def mean_wind_profile(data):
    """Mean wind speed [m/s] at each NORA3 height, as a Series indexed by height."""
    return pd.Series({z: data[col].mean() for z, col in measured_heights(data).items()}, name="wind_speed")


def rotor_wind_speeds(data, turbine=None):
    """
    Wind over the rotor for each time step.

    Returns a DataFrame with the columns
        bottom, hub, top     wind speed [m/s] at the lowest blade tip, the hub and the highest blade tip
        difference           top - bottom [m/s]
        alpha                shear exponent between bottom and top
    """
    t = turbines.get(turbine)
    rotor = pd.DataFrame({
        "bottom": wind_speed_at_height(data, t.rotor_bottom),
        "hub": wind_speed_at_height(data, t.hub_height),
        "top": wind_speed_at_height(data, t.rotor_top),
    })
    rotor["difference"] = rotor["top"] - rotor["bottom"]
    rotor["alpha"] = np.log(rotor["top"] / rotor["bottom"]) / np.log(t.rotor_top / t.rotor_bottom)
    return rotor


def _direction_difference(a, b):
    """a - b in degrees, wrapped to -180..180."""
    return (a - b + 180) % 360 - 180


def wind_veer(data, turbine=None):
    """Change in wind direction [deg] from the bottom to the top of the rotor (positive = clockwise)."""
    t = turbines.get(turbine)
    top = value_at_height(data, t.rotor_top, "wind_direction")
    bottom = value_at_height(data, t.rotor_bottom, "wind_direction")
    return _direction_difference(top, bottom).rename("veer_deg")


def _rotor_strips(n_strips):
    """
    Split the rotor disc into horizontal strips of equal height.

    Returns (strip centre heights relative to the hub, as a fraction of the
    radius, and each strip's share of the rotor area).
    """
    edges = np.linspace(-1, 1, n_strips + 1)
    # Area of a unit circle below height y
    area_below = np.arcsin(edges) + edges * np.sqrt(1 - edges**2) + np.pi / 2
    return (edges[:-1] + edges[1:]) / 2, np.diff(area_below) / np.pi


def rotor_equivalent_wind_speed(data, turbine=None, include_veer=False, n_strips=20):
    """
    Rotor-equivalent wind speed (REWS) [m/s].

    The rotor is split into horizontal strips; each strip gets the wind at
    its own height, weighted by its share of the rotor area A_i / A, so that
    the kinetic energy flux (u^3) is kept:

        REWS = ( sum_i  A_i / A * (u_i * cos(dphi_i))^3 ) ^ (1/3)

    dphi_i is the difference between the wind direction in the strip and at
    the hub (wind veer); it is only used with include_veer=True.

    Source: IEC 61400-12-1:2017, Power performance measurements of
    electricity producing wind turbines (REWS definition, incl. veer).
    The idea and the form without veer: Wagner et al. (2009), Wind Energy
    12(4), 348-362, eq. (6), which assumes no tilt or yaw error.
    """
    t = turbines.get(turbine)
    centres, weights = _rotor_strips(n_strips)
    hub_direction = value_at_height(data, t.hub_height, "wind_direction") if include_veer else None

    cubed = np.zeros(len(data))
    for centre, weight in zip(centres, weights):
        z = t.hub_height + centre * t.rotor_radius
        u = wind_speed_at_height(data, z).to_numpy()
        if include_veer:
            dphi = _direction_difference(value_at_height(data, z, "wind_direction"), hub_direction)
            u = u * np.cos(np.radians(dphi.to_numpy()))
        cubed += weight * u**3

    return pd.Series(np.cbrt(cubed), index=data.index, name="rews")
