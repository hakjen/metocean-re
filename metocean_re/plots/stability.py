"""Figures: atmospheric stability (Obukhov length)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.stability import CLASS_NAMES, obukhov_length, stability_class, stability_parameter
from ..stats.turbulence import turbulence_intensity
from ..stats.profile import rotor_wind_speeds, value_at_height, wind_veer
from ._style import (
    BLUE, INK, INK_MUTED, INK_SECONDARY, MONTHS, ORANGE, STABILITY_COLORS, SURFACE,
    finish, stability_axis, style_axes, titles,
)

# z/L is plotted between these limits (it goes to +/- infinity in calm, very stable/unstable air)
ZETA_LIMIT = 2.0


def _class_bands(ax, z):
    """Shade the stability classes as horizontal bands in a z/L plot."""
    edges_inverse_L = [-np.inf, -1 / 100, -1 / 200, -1 / 500, 1 / 500, 1 / 200, 1 / 50, np.inf]
    edges = np.clip(np.array(edges_inverse_L) * z, -ZETA_LIMIT, ZETA_LIMIT)
    for name, low, high in zip(CLASS_NAMES, edges[:-1], edges[1:]):
        ax.axhspan(low, high, color=STABILITY_COLORS[name], alpha=0.12, zorder=1, linewidth=0)


def plot_stability_timeseries(data, start_time=None, end_time=None, z=50, output_file="stability_timeseries.png"):
    """
    Top: stability parameter z/L over a period, with the stability classes
    as coloured bands. Bottom: the temperature difference between the air at
    height z and the sea surface, which drives the stability.
    Default period: the first month of the data.
    """
    if start_time is None and end_time is None:
        start_time = data.index[0]
        end_time = start_time + pd.DateOffset(months=1)
    period = data.loc[start_time:end_time]

    zeta = stability_parameter(period, z).clip(-ZETA_LIMIT, ZETA_LIMIT)
    delta_t = value_at_height(period, z, "air_temperature") - period["sea_surface_temperature"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.4, 1]})
    _class_bands(ax1, z)
    ax1.plot(zeta.index, zeta, color=INK, linewidth=1.2, zorder=3)
    ax1.axhline(0, color=INK_MUTED, linewidth=0.8, zorder=2)
    ax1.text(1.01, 0.97, "stable", transform=ax1.transAxes, va="top", fontsize=8.5, color=INK_SECONDARY)
    ax1.text(1.01, 0.03, "unstable", transform=ax1.transAxes, va="bottom", fontsize=8.5, color=INK_SECONDARY)
    ax1.set_ylim(-ZETA_LIMIT, ZETA_LIMIT)
    ax1.set_ylabel(f"Stability z/L at {z} m")

    ax2.plot(delta_t.index, delta_t, color=BLUE, linewidth=1.3, zorder=3)
    ax2.axhline(0, color=INK_MUTED, linewidth=0.8, zorder=2)
    ax2.set_ylabel(f"T(air, {z} m) - T(sea) [K]")
    for ax in (ax1, ax2):
        style_axes(ax)

    classes = stability_class(obukhov_length(period, z))
    stable_share = classes.isin(CLASS_NAMES[4:]).mean()
    titles(
        fig,
        f"Atmospheric stability, {period.index[0]:%d %b %Y} - {period.index[-1]:%d %b %Y}",
        f"Stable {stable_share:.0%} of the time in this period. The air becomes stable when it is warmer than "
        "the sea (bottom panel above zero).",
    )
    return finish(fig, output_file)


def plot_stability_by_month(data, z=50, output_file="stability_by_month.png"):
    """Share of time in each stability class, for each calendar month."""
    classes = stability_class(obukhov_length(data, z))
    # Months without data are left empty
    shares = pd.crosstab(classes.index.month, classes, normalize="index").reindex(
        index=range(1, 13), columns=CLASS_NAMES, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 5.4))
    bottom = np.zeros(12)
    for name in CLASS_NAMES:
        ax.bar(np.arange(12), shares[name] * 100, bottom=bottom, width=0.75, color=STABILITY_COLORS[name],
               edgecolor=SURFACE, linewidth=1, label=name, zorder=3)
        bottom += shares[name].to_numpy() * 100
    ax.set_xticks(np.arange(12), MONTHS)
    ax.set_ylabel("Share of time [%]")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.0, 1.0), reverse=True)
    style_axes(ax)

    stable = shares[CLASS_NAMES[4:]].sum(axis=1)
    titles(
        fig,
        f"Atmospheric stability through the year ({data.index[0].year}-{data.index[-1].year})",
        f"Stable air is most common in {MONTHS[stable.idxmax() - 1]} ({stable.max():.0%}) - warm air over a cold sea - "
        f"and least common in {MONTHS[stable.idxmin() - 1]} ({stable.min():.0%}).",
    )
    return finish(fig, output_file)


def plot_stability_effects(data, turbine=None, output_file="stability_effects.png"):
    """
    How the wind over the rotor changes with stability: shear exponent,
    turbulence intensity and wind veer per stability class (median, with
    the 25-75 % range as a line).
    """
    t = turbines.get(turbine)
    classes = stability_class(obukhov_length(data))
    measures = [
        ("Shear exponent across rotor", rotor_wind_speeds(data, t)["alpha"]),
        ("Turbulence intensity [%]", turbulence_intensity(data, t) * 100),
        ("Wind veer bottom to top [deg]", wind_veer(data, t)),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    x = np.arange(len(CLASS_NAMES))
    colors = [STABILITY_COLORS[name] for name in CLASS_NAMES]
    for ax, (label, values) in zip(axes, measures):
        grouped = values.groupby(classes, observed=False)
        median, q25, q75 = grouped.median(), grouped.quantile(0.25), grouped.quantile(0.75)
        ax.bar(x, median, width=0.65, color=colors, zorder=3)
        ax.vlines(x, q25, q75, color=INK, linewidth=1.2, zorder=4)
        ax.axhline(0, color=INK_MUTED, linewidth=0.8)
        ax.set_title(label, loc="left", fontsize=10)
        stability_axis(ax)
        style_axes(ax)

    alpha = measures[0][1].groupby(classes, observed=False).median()
    ti = measures[1][1].groupby(classes, observed=False).median()
    titles(
        fig,
        f"Wind over the rotor by stability class ({t.name})",
        f"Very stable air: shear {alpha['very stable']:.2f}, TI {ti['very stable']:.1f} %. "
        f"Very unstable air: shear {alpha['very unstable']:.2f}, TI {ti['very unstable']:.1f} %. "
        "Bars: median, lines: 25-75 %.",
    )
    return finish(fig, output_file)


def plot_obukhov_validation(data, reference, z=50, output_file="obukhov_validation.png"):
    """
    Compare the Obukhov length estimated from the bulk Richardson number
    with L calculated from the surface fluxes (metocean-api product
    NORA3_offshore_wind, column 'atmosphere_obukhov_length').

    Left: z/L from both methods for each hour. Right: share of time in each
    stability class.
    """
    common = data.index.intersection(reference.index)
    if common.empty:
        raise ValueError("The data and the reference have no time steps in common.")
    estimate = obukhov_length(data.loc[common], z)
    fluxes = reference.loc[common, "atmosphere_obukhov_length"]

    zeta_estimate = (z / estimate).clip(-ZETA_LIMIT, ZETA_LIMIT)
    zeta_fluxes = (z / fluxes).clip(-ZETA_LIMIT, ZETA_LIMIT)
    class_estimate, class_fluxes = stability_class(estimate), stability_class(fluxes)
    same = (class_estimate == class_fluxes).mean()
    within_one = (np.abs(class_estimate.cat.codes - class_fluxes.cat.codes) <= 1).mean()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1, 1.3]})
    ax1.plot([-ZETA_LIMIT, ZETA_LIMIT], [-ZETA_LIMIT, ZETA_LIMIT], color=INK_MUTED, linewidth=1, zorder=2)
    ax1.scatter(zeta_fluxes, zeta_estimate, s=10, color=BLUE, alpha=0.4, linewidths=0, zorder=3)
    ax1.set_xlabel(f"z/L from surface fluxes (NORA3_offshore_wind), z = {z} m")
    ax1.set_ylabel("z/L from bulk Richardson number")
    ax1.set_xlim(-ZETA_LIMIT, ZETA_LIMIT)
    ax1.set_ylim(-ZETA_LIMIT, ZETA_LIMIT)
    ax1.set_aspect("equal")
    style_axes(ax1, grid_axis="both")

    x = np.arange(len(CLASS_NAMES))
    width = 0.38
    for offset, classes, color, label in [(-width / 2, class_fluxes, ORANGE, "surface fluxes"),
                                          (width / 2, class_estimate, BLUE, "bulk Richardson estimate")]:
        share = classes.value_counts(normalize=True).reindex(CLASS_NAMES) * 100
        ax2.bar(x + offset, share, width=width - 0.04, color=color, zorder=3, label=label)
    ax2.set_ylabel("Share of time [%]")
    ax2.legend(frameon=False, fontsize=9)
    stability_axis(ax2)
    style_axes(ax2)

    titles(
        fig,
        f"Obukhov length: estimate vs. surface fluxes ({len(common)} hours)",
        f"Same stability class {same:.0%} of the time, at most one class apart {within_one:.0%} of the time.",
    )
    return finish(fig, output_file)
