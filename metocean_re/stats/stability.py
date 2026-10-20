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
# reality it grows with the friction velocity, z0 = alpha u*^2 / g
# (Charnock 1955, p. 639), which is ignored here. With alpha ~ 0.011 and
# u* ~ 0.4 m/s (moderate wind) this gives about 2e-4 m.
SEA_ROUGHNESS = 2e-4

# Stability classes from the Obukhov length L [m], after Gryning et al.
# (2007), Boundary-Layer Meteorology 124, 251-268 (Table 1, p. 260). The
# outermost classes are extended to L = 0 (Gryning: -100 < L < -50 and
# 10 < L < 50), so that every time step gets a class.
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

    Source: Bolton (1980), Monthly Weather Review 108, 1046-1053, eq. (10),
    p. 1047. Accurate to 0.1 % for -30 C <= T <= 35 C.
    """
    t_celsius = temperature - 273.15
    return 611.2 * np.exp(17.67 * t_celsius / (t_celsius + 243.5))


def specific_humidity(temperature, relative_humidity, pressure):
    """
    Specific humidity [kg/kg] from temperature [K], relative humidity [0-1] and pressure [Pa].

    0.622 = R_d / R_v (Bolton 1980, p. 1047) and 0.378 = 1 - 0.622.
    """
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

    The air at the sea surface is assumed saturated at the sea surface
    temperature, with the vapour pressure of sea water taken as 0.98 times
    that of pure water because of the salinity (Fairall et al. 2003, J.
    Climate 16, 571-591, sec. 2b, p. 573). The pressure is found from the
    air density at height z.

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

    Unstable: Paulson (1970), J. Applied Meteorology 9, 857-861, p. 858:
    the integrated Businger-Dyer form with x = (1 - 16 z/L)^(1/4), where
    16 gave the best fit (p. 859). Stable: psi_m = -5 z/L, integrated from
    phi_m = 1 + 5 z/L. Both are the forms recommended by Dyer (1974),
    Boundary-Layer Meteorology 7, 363-372 (p. 371), after Dyer and Hicks (1970).
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

    Source: Launiainen (1995), Boundary-Layer Meteorology 76, 165-179,
    eq. (2), with alpha_HN = 1 as in the paper. The same roughness length is
    used for momentum and heat, which Launiainen (sec. 2.2) notes is
    generally true over water in light to moderate winds.
    """
    log_z = np.log(z / z0)
    return zeta * (log_z - psi_heat(zeta)) / (log_z - psi_momentum(zeta)) ** 2


def stability_parameter(data, z=50):
    """
    Stability parameter z/L at height z [m], estimated from the bulk Richardson number.

    _richardson_from_zeta() increases steadily with z/L, so it is inverted
    by interpolation in a table (the "inverse mapping" in Launiainen 1995,
    p. 167). In very stable conditions Ri_b approaches 0.2 and z/L is
    capped at 10.

    The stable correction psi = -5 z/L gives too strong stability effects
    for z/L > 0.5 (Launiainen 1995, sec. 2.3), so L in the "very stable"
    class is uncertain.
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
