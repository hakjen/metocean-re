"""Figures: simple turbine loads."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.wind_loads import (
    WOHLER_COMPOSITE,
    WOHLER_STEEL,
    relative_fatigue_damage,
    rotor_load_asymmetry,
    thrust,
    thrust_coefficient,
    tower_base_moment,
)
from ..stats.stability import CLASS_NAMES, obukhov_length, stability_class
from ..stats.profile import hub_height_wind_speed
from ._style import (
    AQUA, BLUE, INK, INK_MUTED, ORANGE, STABILITY_COLORS,
    finish, label_line, line_with_markers, stability_axis, style_axes, titles,
)


def plot_thrust(data, turbine=None, output_file="thrust.png"):
    """
    Left: thrust coefficient against wind speed (actuator-disc theory).
    Right: thrust on the rotor against wind speed at the site (mean, and the
    range from the varying air density).
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t)
    force = thrust(data, t)
    moment = tower_base_moment(data, t)

    edges = np.arange(0, 27, 1.0)
    grouped = force.groupby(pd.cut(u, edges), observed=False)
    x = (edges[:-1] + edges[1:]) / 2
    u_fine = np.linspace(0, 27, 541)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.plot(u_fine, thrust_coefficient(t, u_fine), color=BLUE, linewidth=2, zorder=3)
    ax1.set_ylabel("Thrust coefficient C_T")
    ax1.set_title("Thrust coefficient", loc="left", fontsize=10)

    ax2.fill_between(x, grouped.min(), grouped.max(), color=BLUE, alpha=0.15, zorder=2, label="range")
    line_with_markers(ax2, x, grouped.mean(), BLUE, label="mean")
    ax2.set_ylabel("Thrust [MN]")
    ax2.set_title("Thrust on the rotor at the site", loc="left", fontsize=10)
    ax2.legend(frameon=False, fontsize=9)
    for ax in (ax1, ax2):
        ax.axvline(t.rated_speed, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
        ax.set_xlabel("Wind speed at hub height [m/s]")
        style_axes(ax)

    titles(
        fig,
        f"Rotor thrust ({t.name})",
        f"Thrust peaks at rated speed ({t.rated_speed:g} m/s, dashed), then drops as the blades pitch. "
        f"Max tower base moment from thrust: {moment.max():.0f} MNm.",
    )
    return finish(fig, output_file)


def plot_loads_by_stability(data, turbine=None, output_file="loads_by_stability.png"):
    """
    Left: share of time and share of fatigue damage (from turbulence) in each
    stability class, for steel (tower) and composite (blades).
    Right: load difference between the top and bottom of the rotor (wind shear).
    """
    t = turbines.get(turbine)
    classes = stability_class(obukhov_length(data))
    time_share = classes.value_counts(normalize=True).reindex(CLASS_NAMES) * 100
    steel = relative_fatigue_damage(data, t, WOHLER_STEEL).groupby(classes, observed=False).sum() * 100
    composite = relative_fatigue_damage(data, t, WOHLER_COMPOSITE).groupby(classes, observed=False).sum() * 100
    asymmetry = rotor_load_asymmetry(data, t).groupby(classes, observed=False).median() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1.5, 1]})
    x = np.arange(len(CLASS_NAMES))
    width = 0.27
    for offset, values, color, label in [(-width, time_share, BLUE, "share of time"),
                                         (0, steel, ORANGE, f"fatigue damage, steel (m = {WOHLER_STEEL})"),
                                         (width, composite, AQUA, f"fatigue damage, blades (m = {WOHLER_COMPOSITE})")]:
        ax1.bar(x + offset, values, width=width - 0.03, color=color, zorder=3, label=label)
    ax1.set_ylabel("Share [%]")
    ax1.set_title("Fatigue damage from turbulence", loc="left", fontsize=10)
    ax1.legend(frameon=False, fontsize=9)
    stability_axis(ax1)
    style_axes(ax1)

    ax2.bar(x, asymmetry, width=0.65, color=[STABILITY_COLORS[n] for n in CLASS_NAMES], zorder=3)
    ax2.axhline(0, color=INK_MUTED, linewidth=0.8)
    ax2.set_ylabel("Load top vs. bottom of rotor [% of hub load]")
    ax2.set_title("Load difference over the rotor (median)", loc="left", fontsize=10)
    stability_axis(ax2)
    style_axes(ax2)

    unstable = CLASS_NAMES[:3]
    titles(
        fig,
        f"Loads by stability class ({t.name})",
        f"Unstable air: {time_share[unstable].sum():.0f} % of the time, {steel[unstable].sum():.0f} % of the "
        f"tower fatigue. Stable air loads the top of the rotor {asymmetry['very stable']:.0f} % more than the bottom.",
    )
    return finish(fig, output_file)
