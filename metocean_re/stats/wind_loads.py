"""
Simple turbine loads - for exploring how the site conditions affect the
loads, not for design.

    thrust()                 force of the wind on the rotor
    tower_base_moment()      bending moment at the tower base from the thrust
    rotor_load_asymmetry()   difference in load between the top and bottom
                             of the rotor, caused by wind shear
    relative_fatigue_damage()  how much each time step contributes to fatigue,
                               from the thrust fluctuations caused by turbulence

Simplifications: quasi-steady aerodynamics (the load follows the wind
directly), ideal actuator-disc theory for the thrust coefficient, no
dynamics of the structure, no wave loads.
"""

from math import gamma, sqrt

import numpy as np
import pandas as pd

from . import turbines
from .turbulence import hub_height_sigma_u
from .profile import hub_height_wind_speed, rotor_wind_speeds, value_at_height

# Wohler (S-N curve) exponents for steel (tower) and glass-fibre composites
# (blades), as in Bak et al. (2013), DTU Wind Energy Report-I-0092,
# sec. 6.4.4, p. 74: m = 3 for steel and m = 10 for the blades.
WOHLER_STEEL = 3
WOHLER_COMPOSITE = 10


def _rotor_area(turbine):
    return np.pi * turbine.rotor_radius**2


def thrust_coefficient(turbine, wind_speed, air_density=1.225):
    """
    Thrust coefficient C_T from actuator-disc (momentum) theory.

    The power coefficient follows from the power curve, C_P = P / (1/2 rho A u^3).
    With the axial induction factor a:

        C_P = 4 a (1 - a)^2,   C_T = 4 a (1 - a)

    so a is found from C_P, and C_T from a. Outside cut-in - cut-out the
    rotor is idling and C_T = 0.

    Source: Burton et al. (2021), Wind Energy Handbook, 3rd ed., Wiley,
    sec. 3.2, eqs. (3.12), (3.13) and (3.16). Momentum theory does not apply
    for a >= 1/2 (p. 44); here a <= 1/3.
    Note: ideal theory gives a lower C_T below rated speed than real
    turbines (which lose some power to drag and the drivetrain).
    """
    t = turbines.get(turbine)
    u = np.asarray(wind_speed, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        cp = t.power(u) * 1e6 / (0.5 * air_density * _rotor_area(t) * u**3)
    cp = np.nan_to_num(np.clip(cp, 0, 16 / 27))  # Betz limit

    # Invert C_P(a) on 0 <= a <= 1/3, where it increases steadily
    a_table = np.linspace(0, 1 / 3, 500)
    a = np.interp(cp, 4 * a_table * (1 - a_table) ** 2, a_table)
    return 4 * a * (1 - a)


def thrust(data, turbine=None):
    """Thrust force on the rotor [MN]: F = 1/2 rho A C_T u^2."""
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t)
    rho = value_at_height(data, t.hub_height, "density")
    ct = thrust_coefficient(t, u, rho)
    return (0.5 * rho * _rotor_area(t) * ct * u**2 / 1e6).rename("thrust_MN")


def tower_base_moment(data, turbine=None):
    """Bending moment at the tower base [MNm] from the rotor thrust (thrust * hub height)."""
    t = turbines.get(turbine)
    return (thrust(data, t) * t.hub_height).rename("tower_base_moment_MNm")


def rotor_load_asymmetry(data, turbine=None):
    """
    Difference in aerodynamic load between the top and bottom of the rotor,
    relative to the load at the hub (load ~ u^2):

        (u_top^2 - u_bottom^2) / u_hub^2

    Each blade goes through this difference once per revolution, so it is a
    cyclic (fatigue) load on the blades caused by wind shear.
    """
    rotor = rotor_wind_speeds(data, turbine)
    return ((rotor["top"] ** 2 - rotor["bottom"] ** 2) / rotor["hub"] ** 2).rename("load_asymmetry")


def thrust_std(data, turbine=None):
    """
    Standard deviation of the thrust [MN] caused by turbulence.

    Quasi-steady and linearised around the mean wind speed U:

        sigma_F = dF/du * sigma_u = rho A C_T U sigma_u
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t)
    rho = value_at_height(data, t.hub_height, "density")
    ct = thrust_coefficient(t, u, rho)
    return (rho * _rotor_area(t) * ct * u * hub_height_sigma_u(data, t) / 1e6).rename("thrust_std_MN")


def relative_fatigue_damage(data, turbine=None, wohler_exponent=WOHLER_STEEL):
    """
    Each time step's share of the total fatigue damage (sums to 1).

    For a narrow-band Gaussian load the stress ranges S are Rayleigh
    distributed, and E[S^m] = (2 sqrt(2) sigma)^m Gamma(1 + m/2). With the
    same number of load cycles in every time step, the damage of a time
    step is proportional to E[S^m] (Palmgren-Miner rule).

    Source: Bendat (1964), Probability functions for random responses,
    NASA CR-33 (narrow-band approximation): Rayleigh peaks, eq. (28);
    expected damage, eqs. (80)-(82). Bendat uses peak amplitudes instead of
    ranges, which only changes the result by the constant 2^m.
    """
    sigma = thrust_std(data, turbine).fillna(0)
    m = wohler_exponent
    damage = (2 * sqrt(2) * sigma) ** m * gamma(1 + m / 2)
    return (damage / damage.sum()).rename("damage_share")
