"""Figures: turbines and energy production."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.wind_losses import annual_energy_losses
from ..stats.wind_power import HOURS_PER_YEAR, capacity_factor, energy_per_year, fit_weibull, power_output, weibull_pdf
from ..stats.profile import hub_height_wind_speed
from ._style import (
    BLUE, DASHED, INK, INK_MUTED, INK_SECONDARY, MONTHS, ORANGE, SHADE, SURFACE,
    finish, label_line, line_with_markers, style_axes, titles, turbine_color,
)


def plot_power_curves(turbine_list=None, output_file="power_curves.png"):
    """
    Power curves of several turbines.

    turbine_list : list of turbine choices, e.g. [5, 10, 15]; default all turbines.
    """
    chosen = [turbines.get(t) for t in (turbine_list or turbines.names())]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    for t in chosen:
        curve = t.power_curve()
        ax.plot(curve.index, curve.values, color=turbine_color(t), linewidth=2, label=t.name, zorder=3)
        ax.text(t.cut_out + 0.3, t.rated_power, t.name, va="center", fontsize=9, color=INK_SECONDARY)

    ax.set_xlabel("Wind speed at hub height [m/s]")
    ax.set_ylabel("Power [MW]")
    ax.set_xlim(0, 31)
    ax.set_ylim(0, max(t.rated_power for t in chosen) * 1.1)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    style_axes(ax)

    rated = ", ".join(f"{t.name} {t.rated_speed:g} m/s" for t in chosen)
    titles(fig, "Power curves", f"Rated power is reached at: {rated}. All shut down at 25 m/s.")
    return finish(fig, output_file)


def plot_wind_and_energy_distribution(data, turbine=None, output_file="wind_and_energy_distribution.png"):
    """
    Top: how often each hub-height wind speed occurs. Bottom: how much of the
    energy is produced at each wind speed. The shapes differ because the
    power rises steeply with wind speed and flattens out at rated power.
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t).dropna()
    power = t.power(u)
    shape, scale = fit_weibull(u)

    bins = np.arange(0, np.ceil(u.max()) + 1, 1.0)
    centres = (bins[:-1] + bins[1:]) / 2
    time_share = np.histogram(u, bins)[0] / len(u) * 100
    energy_share = np.histogram(u, bins, weights=power)[0] / power.sum() * 100
    above_rated = power[u >= t.rated_speed].sum() / power.sum()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    u_fine = np.linspace(0, bins[-1], 300)
    ax1.bar(centres, time_share, width=0.85, color=BLUE, zorder=3, label="NORA3")
    ax1.plot(u_fine, weibull_pdf(u_fine, shape, scale) * 100, color=INK, linewidth=1.5, zorder=4,
             label=f"Weibull fit (k = {shape:.2f}, c = {scale:.1f} m/s)")
    ax1.set_ylabel("Share of time [%]")
    ax1.legend(frameon=False, fontsize=8.5, loc="upper right")

    ax2.bar(centres, energy_share, width=0.85, color=ORANGE, zorder=3)
    ax2.set_ylabel("Share of energy [%]")
    ax2.set_xlabel("Wind speed at hub height [m/s]")

    for ax in (ax1, ax2):
        ax.axvspan(0, t.cut_in, color=SHADE, zorder=1)
        ax.axvspan(t.cut_out, bins[-1], color=SHADE, zorder=1)
        ax.axvline(t.rated_speed, color=INK_MUTED, linewidth=1, linestyle=DASHED, zorder=2)
        style_axes(ax)
    for x, text in [(t.rated_speed, " rated speed"), (t.cut_out, " shut down")]:
        ax2.text(x, 0.97, text, transform=ax2.get_xaxis_transform(), va="top", fontsize=8.5,
                 color=INK_SECONDARY, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))

    titles(
        fig,
        f"Wind speed vs. energy production ({t.name}, hub height {t.hub_height:.0f} m)",
        f"{above_rated:.0%} of the energy is produced at or above rated wind speed "
        f"({t.rated_speed:g} m/s), where the turbine runs at full power.",
    )
    return finish(fig, output_file)


def plot_power_output(data, turbine=None, start_time=None, end_time=None, output_file="power_output.png"):
    """
    Power output (top) and hub-height wind speed (bottom) over a period.
    Default period: the first month of the last year in the data.
    """
    t = turbines.get(turbine)
    if start_time is None and end_time is None:
        start_time = pd.Timestamp(year=data.index[-1].year, month=1, day=1)
        end_time = start_time + pd.DateOffset(months=1)

    period = slice(start_time, end_time)
    power = power_output(data, t).loc[period]
    u = hub_height_wind_speed(data, t).loc[period]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})

    ax1.fill_between(power.index, 0, power, color=BLUE, alpha=0.2, zorder=2)
    ax1.plot(power.index, power, color=BLUE, linewidth=1.3, zorder=3)
    label_line(ax1, t.rated_power, "rated power")
    ax1.set_ylabel("Power [MW]")
    ax1.set_ylim(0, t.rated_power * 1.15)

    ax2.plot(u.index, u, color=ORANGE, linewidth=1.3, zorder=3)
    label_line(ax2, t.cut_in, "cut-in")
    label_line(ax2, t.rated_speed, "rated speed")
    label_line(ax2, t.cut_out, "shut down")
    ax2.set_ylabel("Wind speed at hub [m/s]")
    ax2.set_ylim(0, max(u.max(), t.cut_out) * 1.1)

    for ax in (ax1, ax2):
        style_axes(ax)

    cf = capacity_factor(power, t)
    full_power = (power >= t.rated_power).mean()
    titles(
        fig,
        f"Power output, {power.index[0]:%d %b %Y} - {power.index[-1]:%d %b %Y} ({t.name})",
        f"Capacity factor in this period: {cf:.0%}. The turbine ran at full power {full_power:.0%} of the time.",
    )
    return finish(fig, output_file)


def plot_monthly_energy(data, turbine=None, output_file="monthly_energy.png"):
    """
    Energy production per calendar month: the average over all years, and
    the lowest and highest year.
    """
    t = turbines.get(turbine)
    power = power_output(data, t)
    # Energy per month [GWh] = mean power [MW] * hours in that month / 1000
    mean_power = power.resample("MS").mean()
    monthly = mean_power * mean_power.index.days_in_month * 24 / 1000
    by_month = monthly.groupby(monthly.index.month)
    # All 12 months on the axis, also for data shorter than a year (missing months are left empty)
    mean, low, high = (s.reindex(range(1, 13)) for s in (by_month.mean(), by_month.min(), by_month.max()))
    x = np.arange(12)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(x, low, high, color=BLUE, alpha=0.15, zorder=2, label="lowest - highest year")
    line_with_markers(ax, x, mean, BLUE, label="mean")
    ax.set_xticks(x, MONTHS)
    ax.set_ylabel("Energy [GWh per month]")
    ax.set_ylim(0, high.max() * 1.1)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    style_axes(ax)

    best, worst = mean.idxmax(), mean.idxmin()
    titles(
        fig,
        f"Energy production through the year ({t.name}, {data.index[0].year}-{data.index[-1].year})",
        f"{MONTHS[best - 1]} gives {mean[best] / mean[worst]:.1f}x the energy of {MONTHS[worst - 1]} on average "
        f"({mean[best]:.1f} vs {mean[worst]:.1f} GWh).",
    )
    return finish(fig, output_file)


def plot_energy_per_year(data, turbine=None, output_file="energy_per_year.png"):
    """Gross energy production for each year, to show the year-to-year variation."""
    t = turbines.get(turbine)
    energy = energy_per_year(data, t) / 1000
    mean = energy.mean()

    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.bar(energy.index, energy.values, width=0.6, color=BLUE, zorder=3)
    label_line(ax, mean, f"mean {mean:.1f} GWh")
    for year, value in energy.items():
        ax.text(year, value, f"{value:.1f}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(energy.index)
    ax.set_ylabel("Gross energy [GWh per year]")
    ax.set_ylim(0, energy.max() * 1.15)
    ax.set_xlim(energy.index[0] - 0.6, energy.index[-1] + 1.4)  # room for the mean label
    style_axes(ax)

    spread = (energy.max() - energy.min()) / 2 / mean
    titles(
        fig,
        f"Energy production per year ({t.name})",
        f"From {energy.min():.1f} GWh ({energy.idxmin()}) to {energy.max():.1f} GWh ({energy.idxmax()}): "
        f"about +/- {spread:.0%} around the mean.",
    )
    return finish(fig, output_file)


def plot_turbine_comparison(data, turbine_list=None, output_file="turbine_comparison.png", **loss_options):
    """
    Net annual energy production (left) and capacity factor (right) for
    several turbines at the same site. loss_options are passed on to
    annual_energy_losses().
    """
    chosen = [turbines.get(t) for t in (turbine_list or turbines.names())]
    names, net, cf, colors = [], [], [], []
    for t in chosen:
        losses = annual_energy_losses(data, t, **loss_options)
        names.append(t.name)
        net.append(losses.attrs["net_MWh"] / 1000)
        cf.append(losses.attrs["net_MWh"] / (t.rated_power * HOURS_PER_YEAR))
        colors.append(turbine_color(t))

    y = np.arange(len(chosen))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 1.0 * len(chosen) + 2.2), sharey=True)

    ax1.barh(y, net, color=colors, height=0.6, zorder=3)
    for yi, value in zip(y, net):
        ax1.text(value, yi, f"  {value:.1f} GWh", va="center", fontsize=9, color=INK)
    ax1.set_xlim(0, max(net) * 1.25)
    ax1.set_xlabel("Net energy [GWh per year]")

    ax2.barh(y, np.array(cf) * 100, color=colors, height=0.6, zorder=3)
    for yi, value in zip(y, cf):
        ax2.text(value * 100, yi, f"  {value:.0%}", va="center", fontsize=9, color=INK)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Net capacity factor [%]")

    ax1.set_yticks(y, names)
    for ax in (ax1, ax2):
        style_axes(ax, grid_axis="x")

    best = int(np.argmax(cf))
    titles(fig, "Turbine comparison at this site",
           f"Highest capacity factor: {names[best]} ({cf[best]:.0%}). Energy scales mostly with rated power.")
    return finish(fig, output_file)
