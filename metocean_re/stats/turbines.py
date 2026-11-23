"""
Turbine types and how to choose between them.

The built-in turbines are read from turbines.cfg (next to this file). A
turbine can be chosen by its rated power in MW, by name, or by passing a
Turbine object directly:

    from metocean_re.stats import turbines

    turbines.get(15)            # the 15 MW turbine
    turbines.get("DTU-10MW")    # by name
    turbines.table()            # overview of all available turbines

New turbines can be added in code, or loaded from your own .cfg file:

    turbines.add("my_12MW", rated_power=12, cut_in=3, rated_speed=11,
                 cut_out=25, hub_height=140, rotor_diameter=220)
    turbines.load("my_turbines.cfg")

The power curve is a simplified model (P ~ u^3 between cut-in and rated
speed, constant rated power up to cut-out), not a manufacturer curve.
"""

import configparser
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

BUILTIN_CFG = Path(__file__).with_name("turbines.cfg")

# Used whenever a function is called without choosing a turbine [MW].
DEFAULT_TURBINE = 15


@dataclass(frozen=True)
class Turbine:
    name: str
    rated_power: float  # MW
    cut_in: float  # m/s
    rated_speed: float  # m/s
    cut_out: float  # m/s
    hub_height: float  # m
    rotor_diameter: float  # m
    description: str = ""

    @property
    def rotor_radius(self):
        return self.rotor_diameter / 2

    @property
    def rotor_bottom(self):
        """Height of the lowest blade tip [m]."""
        return self.hub_height - self.rotor_radius

    @property
    def rotor_top(self):
        """Height of the highest blade tip [m]."""
        return self.hub_height + self.rotor_radius

    def power(self, wind_speed):
        """Power output [MW] for the given wind speed(s) [m/s]."""
        u = np.asarray(wind_speed, dtype=float)
        power = np.zeros_like(u)

        below_rated = (u >= self.cut_in) & (u < self.rated_speed)
        at_rated = (u >= self.rated_speed) & (u <= self.cut_out)

        power[below_rated] = self.rated_power * (
            (u[below_rated] ** 3 - self.cut_in**3) / (self.rated_speed**3 - self.cut_in**3)
        )
        power[at_rated] = self.rated_power
        return power

    def power_curve(self, wind_speeds=None):
        """Power curve as a Series of power [MW] indexed by wind speed [m/s]."""
        if wind_speeds is None:
            wind_speeds = np.arange(0, 30.05, 0.1)
        u = np.asarray(wind_speeds, dtype=float)
        return pd.Series(self.power(u), index=u, name="power_MW")


_TURBINES = {}


def add(name, rated_power, cut_in, rated_speed, cut_out, hub_height, rotor_diameter, description=""):
    """
    Add a turbine type (or replace one with the same name).

    rated_power in MW, speeds in m/s, hub_height and rotor_diameter in m.
    Returns the new Turbine.
    """
    turbine = Turbine(
        name=name,
        rated_power=float(rated_power),
        cut_in=float(cut_in),
        rated_speed=float(rated_speed),
        cut_out=float(cut_out),
        hub_height=float(hub_height),
        rotor_diameter=float(rotor_diameter),
        description=description,
    )
    if not turbine.cut_in < turbine.rated_speed < turbine.cut_out:
        raise ValueError(f"{name}: need cut_in < rated_speed < cut_out.")
    if turbine.rotor_bottom <= 0:
        raise ValueError(f"{name}: the rotor reaches below the surface (hub_height < rotor_diameter / 2).")

    _TURBINES[name] = turbine
    return turbine


def load(cfg_file):
    """
    Add all turbines from a .cfg file (same format as turbines.cfg).

    Returns the list of turbine names that were loaded.
    """
    parser = configparser.ConfigParser()
    if not parser.read(cfg_file):
        raise FileNotFoundError(cfg_file)

    for name in parser.sections():
        section = parser[name]
        add(
            name,
            rated_power=section.getfloat("rated_power"),
            cut_in=section.getfloat("cut_in"),
            rated_speed=section.getfloat("rated_speed"),
            cut_out=section.getfloat("cut_out"),
            hub_height=section.getfloat("hub_height"),
            rotor_diameter=section.getfloat("rotor_diameter"),
            description=section.get("description", ""),
        )
    return parser.sections()


def get(turbine=None):
    """
    Look up a turbine.

    turbine : float, str, Turbine or None
        Rated power in MW (e.g. 15), a turbine name (e.g. 'IEA-15MW'), or a
        Turbine object. None gives DEFAULT_TURBINE.
    """
    if turbine is None:
        turbine = DEFAULT_TURBINE
    if isinstance(turbine, Turbine):
        return turbine

    if isinstance(turbine, str):
        for name, t in _TURBINES.items():
            if name.lower() == turbine.lower():
                return t
        raise ValueError(f"Unknown turbine '{turbine}'. Available: {names()}")

    matches = [t for t in _TURBINES.values() if np.isclose(t.rated_power, turbine)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        available = sorted({t.rated_power for t in _TURBINES.values()})
        raise ValueError(f"No turbine with rated power {turbine} MW. Available [MW]: {available}")
    raise ValueError(
        f"Several turbines are rated {turbine} MW: {[t.name for t in matches]}. Choose one by name."
    )


def names():
    """Names of all available turbines."""
    return list(_TURBINES)


def table():
    """Overview of all available turbines as a DataFrame."""
    rows = [
        {
            "name": t.name,
            "rated_power_MW": t.rated_power,
            "cut_in": t.cut_in,
            "rated_speed": t.rated_speed,
            "cut_out": t.cut_out,
            "hub_height": t.hub_height,
            "rotor_diameter": t.rotor_diameter,
            "description": t.description,
        }
        for t in _TURBINES.values()
    ]
    return pd.DataFrame(rows).set_index("name").sort_values("rated_power_MW")


load(BUILTIN_CFG)
