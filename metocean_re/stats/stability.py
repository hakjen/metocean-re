"""
Atmospheric stability: the Obukhov length L.

    L < 0, small |L|   unstable  - air warmer at the surface, strong mixing:
                                   little wind shear, more turbulence
    |L| large          neutral
    L > 0, small L     stable    - warm air over a colder sea, weak mixing:
                                   strong wind shear and veer, little turbulence

NORA3's monthly subset files do not contain the surface fluxes needed to
compute L directly, so it is estimated from the temperature difference
between the sea surface and the air at 50 m, via the bulk Richardson number:

    1. Ri_b = g / theta_v * (theta_v(z) - theta_v(0)) * z / u(z)^2
    2. Ri_b is converted to z/L with Monin-Obukhov similarity theory.

The estimate can be compared with L calculated from the fluxes (metocean-api
product NORA3_offshore_wind), see plots.plot_obukhov_validation().
"""

import numpy as np
import pandas as pd

from .profile import value_at_height

GRAVITY = 9.81  # m/s^2
CP_AIR = 1004.7  # specific heat of dry air [J/(kg K)]
R_AIR = 287.05  # gas constant of dry air [J/(kg K)]
VON_KARMAN = 0.4

# Roughness length of the sea surface [m]. A typical open-sea value; in
# reality it grows with the waves (Charnock 1955), which is ignored here.
SEA_ROUGHNESS = 2e-4

# Stability classes from the Obukhov length L [m], after Gryning et al.
# (2007), Boundary-Layer Meteorology 124, 251-268 (Table 1). The outermost
# classes are extended to L = 0.
#
#   very unstable          -100 < L < 0
#   unstable               -200 < L <= -100
#   near-neutral unstable  -500 < L <= -200
#   neutral                |L| >= 500
#   near-neutral stable     200 <= L < 500
#   stable                   50 <= L < 200
#   very stable               0 < L < 50
#
# 1/L increases steadily from very unstable to very stable, so the classes
# are found by cutting 1/L at these edges.
CLASS_NAMES = [
    "very unstable", "unstable", "near-neutral unstable", "neutral",
    "near-neutral stable", "stable", "very stable",
]
_INVERSE_L_EDGES = [-np.inf, -1 / 100, -1 / 200, -1 / 500, 1 / 500, 1 / 200, 1 / 50, np.inf]


# --- Humidity and temperature ---------------------------------------------------


def saturation_vapour_pressure(temperature):
    """
    Saturation vapour pressure [Pa] over water at temperature [K].

    Source: Bolton (1980), Monthly Weather Review 108, 1046-1053, eq. (10).
    """
    t_celsius = temperature - 273.15
    return 611.2 * np.exp(17.67 * t_celsius / (t_celsius + 243.5))


def specific_humidity(temperature, relative_humidity, pressure):
    """Specific humidity [kg/kg] from temperature [K], relative humidity [0-1] and pressure [Pa]."""
    e = relative_humidity * saturation_vapour_pressure(temperature)
    return 0.622 * e / (pressure - 0.378 * e)


def pressure_from_density(density, temperature, relative_humidity):
    """
    Air pressure [Pa] from density [kg/m3], temperature [K] and relative
    humidity, with the ideal gas law for moist air: p = rho * R * T * (1 + 0.61 q).
    The humidity term is small, so q is computed with a first guess of the pressure.
    """
    first_guess = density * R_AIR * temperature
    q = specific_humidity(temperature, relative_humidity, first_guess)
    return density * R_AIR * temperature * (1 + 0.61 * q)


def surface_pressure(pressure, temperature, z):
    """Pressure [Pa] at the surface from pressure at height z [m] (hypsometric equation)."""
    return pressure * np.exp(GRAVITY * z / (R_AIR * temperature))


def virtual_potential_temperature(temperature, humidity, z):
    """
    Virtual potential temperature [K] at height z [m]: the temperature that
    dry air at the surface would need to have the same density.

    theta_v = T * (1 + 0.61 q) + g / cp * z

    Source: Stull (1988), An Introduction to Boundary Layer Meteorology,
    sec. 1.5.1, eq. (1.5.1b): theta_v = theta * (1 + 0.61 r). Approximations:
    theta = T + g / cp * z (dry adiabatic), specific humidity q instead of
    mixing ratio r, and the humidity term applied to T instead of theta
    (less than 0.01 K at 50 m).
    """
    return temperature * (1 + 0.61 * humidity) + GRAVITY / CP_AIR * z


# --- Bulk Richardson number and Obukhov length -----------------------------------


def bulk_richardson(data, z=50):
    """
    Bulk Richardson number between the sea surface and height z [m].

    Ri_b = g / theta_v * (theta_v(z) - theta_v(0)) * z / u(z)^2

    The air at the sea surface is assumed saturated (98 % relative humidity
    over salt water) at the sea surface temperature. The pressure is found
    from the air density at height z.

    Source: Stull (1988), An Introduction to Boundary Layer Meteorology,
    sec. 5.6.3, eq. (5.6.3), with the wind at the surface set to zero.
    """
    sst = data["sea_surface_temperature"]
    t_z = value_at_height(data, z, "air_temperature")
    rh_z = value_at_height(data, z, "relative_humidity")
    u_z = value_at_height(data, z, "wind_speed").clip(lower=1.0)  # avoid dividing by ~0 in calm conditions
    p_z = pressure_from_density(value_at_height(data, z, "density"), t_z, rh_z)
    p_0 = surface_pressure(p_z, t_z, z)

    theta_v_z = virtual_potential_temperature(t_z, specific_humidity(t_z, rh_z, p_z), z)
    theta_v_0 = virtual_potential_temperature(sst, specific_humidity(sst, 0.98, p_0), 0)

    ri_b = GRAVITY / theta_v_0 * (theta_v_z - theta_v_0) * z / u_z**2
    return ri_b.rename("bulk_richardson")


def psi_momentum(zeta):
    """
    Stability correction of the wind profile, psi_m(z/L).

    Unstable: Paulson (1970), J. Applied Meteorology 9, 857-861, with the
    Businger-Dyer form x = (1 - 16 z/L)^(1/4) (Dyer 1974, Boundary-Layer
    Meteorology 7, 363-372). Stable: psi_m = -5 z/L (Dyer 1974).
    """
    zeta = np.asarray(zeta, dtype=float)
    x = np.power(1 - 16 * np.minimum(zeta, 0), 0.25)
    unstable = 2 * np.log((1 + x) / 2) + np.log((1 + x**2) / 2) - 2 * np.arctan(x) + np.pi / 2
    return np.where(zeta < 0, unstable, -5 * zeta)


def psi_heat(zeta):
    """Stability correction of the temperature profile, psi_h(z/L). Sources as psi_momentum()."""
    zeta = np.asarray(zeta, dtype=float)
    x = np.power(1 - 16 * np.minimum(zeta, 0), 0.25)
    return np.where(zeta < 0, 2 * np.log((1 + x**2) / 2), -5 * zeta)


def _richardson_from_zeta(zeta, z, z0=SEA_ROUGHNESS):
    """
    Bulk Richardson number for a given z/L (Monin-Obukhov similarity):

        Ri_b = z/L * (ln(z/z0) - psi_h) / (ln(z/z0) - psi_m)^2

    Source: Launiainen (1995), Boundary-Layer Meteorology 76, 165-179.
    The same roughness length is used for momentum and heat (simplification).
    """
    log_z = np.log(z / z0)
    return zeta * (log_z - psi_heat(zeta)) / (log_z - psi_momentum(zeta)) ** 2


def stability_parameter(data, z=50):
    """
    Stability parameter z/L at height z [m], estimated from the bulk Richardson number.

    _richardson_from_zeta() increases steadily with z/L, so it is inverted
    by interpolation in a table. In very stable conditions Ri_b approaches
    0.2 and z/L is capped at 10.
    """
    zeta_table = np.concatenate([-np.logspace(2, -4, 300), [0], np.logspace(-4, 1, 300)])
    ri_table = _richardson_from_zeta(zeta_table, z)
    zeta = np.interp(bulk_richardson(data, z), ri_table, zeta_table)
    return pd.Series(zeta, index=data.index, name="z_over_L")


def obukhov_length(data, z=50):
    """Obukhov length L [m], estimated from the bulk Richardson number at height z."""
    zeta = stability_parameter(data, z)
    with np.errstate(divide="ignore"):
        return (z / zeta).rename("obukhov_length")


def stability_class(obukhov_length):
    """Stability class for each value of the Obukhov length L [m] (Series of ordered categories)."""
    L = pd.Series(obukhov_length, dtype=float)
    with np.errstate(divide="ignore"):
        inverse_L = 1 / L
    return pd.cut(inverse_L, _INVERSE_L_EDGES, labels=CLASS_NAMES).rename("stability")
