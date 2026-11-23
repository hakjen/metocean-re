"""
Figures that compare sites: the same turbine at two or more places.

Each function takes `datasets`, a dict {site name: data}, e.g.
{"Utsira Nord": df_utsira, "Sorlige Nordsjo II": df_snii}. The sites keep
the same colour in every figure (first site blue, second orange, ...).
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.profile import hub_height_wind_speed
from ..stats.stability import CLASS_NAMES, obukhov_length, stability_class
from ..stats.wind_losses import annual_energy_losses
from ..stats.wind_power import power_output
from ._style import (
    BASELINE, CATEGORICAL, DASHED, INK_MUTED, MONTHS, SHADE,
    finish, line_with_markers, stability_axis, style_axes, titles,
)


def _site_colors(datasets):
    return dict(zip(datasets, CATEGORICAL))


def _period(data):
    return f"{data.index[0].year}" if data.index[0].year == data.index[-1].year else (
        f"{data.index[0].year}-{data.index[-1].year}")


def _periods(datasets):
    """The period in the title, or the period of each site if they differ."""
    periods = {name: _period(data) for name, data in datasets.items()}
    if len(set(periods.values())) == 1:
        return next(iter(periods.values()))
    return "; ".join(f"{name}: {period}" for name, period in periods.items())


def plot_monthly_energy_sites(datasets, turbine=None, output_file="monthly_energy_sites.png"):
    """Mean energy production per calendar month at each site."""
    t = turbines.get(turbine)
    colors = _site_colors(datasets)
    x = np.arange(12)

    fig, ax = plt.subplots(figsize=(9, 5))
    yearly = {}
    for name, data in datasets.items():
        mean_power = power_output(data, t).resample("MS").mean()
        monthly = mean_power * mean_power.index.days_in_month * 24 / 1000  # GWh per month
        mean = monthly.groupby(monthly.index.month).mean().reindex(range(1, 13))
        yearly[name] = mean.sum()
        line_with_markers(ax, x, mean, colors[name], label=name)
    ax.set_xticks(x, MONTHS)
    ax.set_ylabel("Energy [GWh per month]")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    style_axes(ax)

    titles(
        fig,
        f"Gross energy production through the year ({t.name}, {_periods(datasets)})",
        "Before losses, per year: " + ", ".join(f"{name} {value:.0f} GWh" for name, value in yearly.items()) + ".",
    )
    return finish(fig, output_file)


def plot_wind_distribution_sites(datasets, turbine=None, output_file="wind_distribution_sites.png"):
    """How often each hub-height wind speed occurs at each site."""
    t = turbines.get(turbine)
    colors = _site_colors(datasets)
    speeds = {name: hub_height_wind_speed(data, t).dropna() for name, data in datasets.items()}
    bins = np.arange(0, np.ceil(max(u.max() for u in speeds.values())) + 1, 1.0)
    centres = (bins[:-1] + bins[1:]) / 2

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axvspan(0, t.cut_in, color=SHADE, zorder=1)
    ax.axvspan(t.cut_out, bins[-1], color=SHADE, zorder=1)
    ax.axvline(t.rated_speed, color=INK_MUTED, linewidth=1, linestyle=DASHED, zorder=2)
    for name, u in speeds.items():
        share = np.histogram(u, bins)[0] / len(u) * 100
        ax.plot(centres, share, color=colors[name], linewidth=2, zorder=3,
                label=f"{name} (mean {u.mean():.1f} m/s)")
    ax.set_xlabel("Wind speed at hub height [m/s]")
    ax.set_ylabel("Share of time [%]")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    style_axes(ax)

    above_rated = {name: (u >= t.rated_speed).mean() for name, u in speeds.items()}
    titles(
        fig,
        f"Wind speed at hub height {t.hub_height:.0f} m ({_periods(datasets)})",
        "Share of time at or above rated speed (full power): "
        + ", ".join(f"{name} {share:.0%}" for name, share in above_rated.items())
        + ". Grey: below cut-in and above cut-out.",
    )
    return finish(fig, output_file)


def plot_losses_sites(datasets, turbine=None, output_file="losses_sites.png", **loss_options):
    """Each loss [% of energy] at each site. loss_options are passed on to annual_energy_losses()."""
    t = turbines.get(turbine)
    colors = _site_colors(datasets)
    losses = {name: annual_energy_losses(data, t, **loss_options) for name, data in datasets.items()}
    percent = pd.DataFrame({name: table["loss_fraction"] * 100 for name, table in losses.items()})
    total = {name: 1 - table.attrs["net_MWh"] / table.attrs["gross_MWh"] for name, table in losses.items()}

    n_sites = len(datasets)
    height = 0.8 / n_sites
    y = np.arange(len(percent))[::-1]
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(percent) * max(n_sites, 2) / 2 + 2.6))
    for k, name in enumerate(datasets):
        ax.barh(y + (n_sites - 1 - 2 * k) * height / 2, percent[name], height=height * 0.9,
                color=colors[name], zorder=3, label=f"{name} (total {total[name]:.1%})")
    ax.axvline(0, color=BASELINE, linewidth=0.9)
    ax.set_yticks(y, percent.index)
    ax.set_xlabel("Loss [% of energy]  (negative = gain)")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style_axes(ax, grid_axis="x")

    difference = (percent.max(axis=1) - percent.min(axis=1)).idxmax()
    titles(
        fig,
        f"Energy losses ({t.name}, {_periods(datasets)})",
        f"The largest difference between the sites is in '{difference}'. "
        "Losses are applied one after another.",
    )
    return finish(fig, output_file)


def plot_stability_sites(datasets, z=50, output_file="stability_sites.png"):
    """Share of time in each atmospheric stability class at each site."""
    colors = _site_colors(datasets)
    shares = pd.DataFrame({
        name: stability_class(obukhov_length(data, z)).value_counts(normalize=True).reindex(CLASS_NAMES).fillna(0)
        * 100 for name, data in datasets.items()})

    n_sites = len(datasets)
    width = 0.8 / n_sites
    x = np.arange(len(CLASS_NAMES))
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for k, name in enumerate(datasets):
        ax.bar(x + (2 * k - (n_sites - 1)) * width / 2, shares[name], width=width * 0.9, color=colors[name],
               zorder=3, label=name)
    stability_axis(ax)
    ax.set_ylabel("Share of time [%]")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    style_axes(ax)

    stable = shares.loc[[c for c in CLASS_NAMES if "stable" in c and "unstable" not in c]].sum()
    titles(
        fig,
        f"Atmospheric stability at {z} m ({_periods(datasets)})",
        "Share of time from near-neutral stable to very stable (more wind shear, less turbulence): "
        + ", ".join(f"{name} {share:.0f} %" for name, share in stable.items()) + ".",
    )
    return finish(fig, output_file)
