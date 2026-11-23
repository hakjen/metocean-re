"""
This is the Plots-module that contains functions for plotting wind energy results.

If output_file is given the figure is saved there and closed; with
output_file=None the figure is returned open. Each figure has a title saying
what is shown and a grey subtitle stating the main result.
"""

from .profile import *
from .stability import *
from .wind_loads import *
from .wind_losses import *
from .wind_power import *
