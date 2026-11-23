"""
This is the Stats-module that contains functions for wind energy from metocean data.

Turbines are kept in their own namespace (stats.turbines.get(15), stats.turbines.add(...)).
"""

from .aux_funcs import *
from . import turbines
from .profile import *
from .stability import *
from .turbulence import *
from .wind_power import *
from .wind_losses import *
from .wind_loads import *
