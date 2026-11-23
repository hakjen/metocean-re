"""Figures: energy losses."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.wind_losses import (
    annual_energy_losses,
    availability_loss,
    losses_by_stability,
    power_with_tilt,
    repair_downtime,
    wave_tilt_amplitude,
    weather_maintenance_loss,
)
from ..stats.wind_power import power_output
from ..stats.stability import CLASS_NAMES
from ._style import (
    AQUA, BASELINE, BLUE, INK, INK_MUTED, INK_SECONDARY, MONTHS, ORANGE, STABILITY_COLORS, VIOLET,
    finish, line_with_markers, stability_axis, style_axes, titles,
)


def plot_energy_losses(data, turbine=None, output_file="energy_losses.png", **loss_options):
    """
    Each loss as a share of the energy, from gross to net annual energy
    production (negative = gain). loss_options are passed on to annual_energy_losses().
    """
    t = turbines.get(turbine)
    losses = annual_energy_losses(data, t, **loss_options)
    gross, net = losses.attrs["gross_MWh"] / 1000, losses.attrs["net_MWh"] / 1000
    percent = losses["loss_fraction"] * 100
    y = np.arange(len(losses))[::-1]

    fig, ax = plt.subplots(figsize=(10, 0.55 * len(losses) + 2.4))
    ax.barh(y, percent, color=[ORANGE if p >= 0 else BLUE for p in percent], height=0.6, zorder=3)
    for yi, pct, mwh in zip(y, percent, losses["loss_MWh"]):
        ax.text(max(pct, 0), yi, f"  {pct:+.2f} %  ({mwh / 1000:+.2f} GWh)", va="center", fontsize=9, color=INK)
    ax.axvline(0, color=BASELINE, linewidth=0.9)
    ax.set_yticks(y, losses.index)
    ax.set_xlim(min(percent.min(), 0) * 1.3 - 0.2, percent.max() * 1.6)
    ax.set_xlabel("Loss [% of energy]  (orange = loss, blue = gain)")
    style_axes(ax, grid_axis="x")

    titles(
        fig,
        f"Energy losses ({t.name})",
        f"Gross {gross:.1f} GWh/year  ->  net {net:.1f} GWh/year  "
        f"(total loss {1 - net / gross:.1%}). Losses are applied one after another.",
    )
    return finish(fig, output_file)


def plot_losses_by_stability(data, turbine=None, output_file="losses_by_stability.png"):
    """The atmospheric losses for each stability class, plus how much energy each class produces."""
    t = turbines.get(turbine)
    table = losses_by_stability(data, t)
    panels = ["share_of_energy", "Air density", "Turbulence", "Wind shear", "Wind veer", "High-wind hysteresis"]

    fig, axes = plt.subplots(2, 3, figsize=(13, 7.6), sharex=True)
    x = np.arange(len(CLASS_NAMES))
    colors = [STABILITY_COLORS[name] for name in CLASS_NAMES]
    for ax, column in zip(axes.flat, panels):
        ax.bar(x, table[column] * 100, width=0.65, color=colors, zorder=3)
        ax.axhline(0, color=INK_MUTED, linewidth=0.8)
        ax.set_title("Share of gross energy [%]" if column == "share_of_energy" else f"{column} loss [%]",
                     loc="left", fontsize=10)
        style_axes(ax)
    for ax in axes[1]:
        stability_axis(ax)

    shear, turbulence = table["Wind shear"].idxmax(), table["Turbulence"].idxmax()
    titles(
        fig,
        f"Atmospheric losses by stability class ({t.name})",
        f"Wind shear costs most in {shear} air ({table.loc[shear, 'Wind shear']:.1%}), "
        f"turbulence in {turbulence} air ({table.loc[turbulence, 'Turbulence']:.1%}). Negative = gain.",
    )
    return finish(fig, output_file)


def plot_maintenance_downtime(data, turbine=None, repair_hours=12, hs_limit=2.0, failures_per_year=8.3,
                              output_file="maintenance_downtime.png"):
    """
    Left: share of time with waves low enough for access, per month.
    Middle: mean downtime per failure, per month (waiting for weather + repair).
    Right: the energy loss for different wave height limits.
    """
    t = turbines.get(turbine)
    downtime, _ = repair_downtime(data, repair_hours, hs_limit)
    # Months without data are NaN, so no bar is drawn for them
    month = data.index.month
    access = (data["hs"] < hs_limit).groupby(month).mean().reindex(range(1, 13)) * 100
    mean_downtime = downtime.groupby(month).mean().reindex(range(1, 13))
    limits = np.arange(1.0, 3.75, 0.25)
    loss = [weather_maintenance_loss(data, t, failures_per_year, repair_hours, limit) * 100 for limit in limits]
    x = np.arange(12)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4.8))
    ax1.bar(x, access, width=0.7, color=BLUE, zorder=3)
    ax1.set_ylabel("Share of time [%]")
    ax1.set_ylim(0, 100)
    ax1.set_title(f"Access possible (Hs < {hs_limit:g} m)", loc="left", fontsize=10)

    ax2.bar(x, mean_downtime / 24, width=0.7, color=ORANGE, zorder=3)
    ax2.set_ylabel("Downtime per failure [days]")
    ax2.set_title(f"Downtime per failure ({repair_hours:g} h repair)", loc="left", fontsize=10)
    for ax in (ax1, ax2):
        ax.set_xticks(x, MONTHS, rotation=90)

    line_with_markers(ax3, limits, loss, ORANGE)
    ax3.axhline(availability_loss() * 100, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax3.text(limits[-1], availability_loss() * 100, "fixed 14 days", ha="right", va="bottom", fontsize=8.5,
             color=INK_SECONDARY)
    ax3.set_xlabel("Wave height limit for access, Hs [m]")
    ax3.set_ylabel("Energy loss [%]")
    ax3.set_ylim(bottom=0)
    ax3.set_title(f"Energy loss ({failures_per_year} failures/year, {t.name})", loc="left", fontsize=10)
    for ax in (ax1, ax2, ax3):
        style_axes(ax)

    days_per_year = failures_per_year * downtime.mean() / 24
    titles(
        fig,
        "Weather-dependent maintenance",
        f"With Hs < {hs_limit:g} m and {failures_per_year} failures per year the turbine is down about "
        f"{days_per_year:.0f} days per year. The result depends strongly on the wave height limit (right).",
    )
    return finish(fig, output_file)


def plot_tilt_loss_comparison(data, turbine=None, tilt_angle=5.0, wave_response=1.0,
                              output_file="tilt_loss_comparison.png"):
    """
    Compare a constant tilt of the rotor with tilting caused by the waves.

    Left: the tilt angle over one minute for three typical sea states.
    Right: the energy loss for each wave height class.
    """
    t = turbines.get(turbine)
    amplitude = wave_tilt_amplitude(data, response=wave_response)

    gross = power_output(data, t)
    constant = power_with_tilt(data, t, tilt_angle=tilt_angle)
    waves = power_with_tilt(data, t, wave_amplitude=amplitude)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))

    # Left: periodic tilt for calm, typical and rough seas (10th, 50th, 99th percentile of Hs)
    seconds = np.linspace(0, 60, 600)
    for color, q, label in [(AQUA, 0.10, "calm"), (BLUE, 0.50, "typical"), (VIOLET, 0.99, "rough")]:
        i = (data["hs"] - data["hs"].quantile(q)).abs().to_numpy().argmin()
        hs, tp, amp = data["hs"].iloc[i], data["tp"].iloc[i], amplitude.iloc[i]
        ax1.plot(seconds, amp * np.sin(2 * np.pi * seconds / tp), color=color, linewidth=1.8, zorder=3,
                 label=f"{label}: Hs {hs:.1f} m, Tp {tp:.1f} s  (+/- {amp:.1f} deg)")
    if tilt_angle:
        ax1.axhline(tilt_angle, color=INK, linewidth=1.2, linestyle=(0, (4, 3)), zorder=3,
                    label=f"constant tilt {tilt_angle:g} deg")
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel("Tilt angle [deg]")
    ax1.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    style_axes(ax1)

    # Right: loss per wave height class
    hs_top = np.ceil(data["hs"].max())  # the fixed edges above the largest Hs are left out
    hs_bins = [b for b in [0, 1, 2, 3, 4, 5, 6, 8] if b < hs_top] + [hs_top]
    hs_class = pd.cut(data["hs"], hs_bins)
    grouped = pd.DataFrame({"gross": gross, "constant": constant, "waves": waves}).groupby(
        hs_class, observed=True).sum()
    x = np.arange(len(grouped))
    for column, color, label in [("constant", INK, f"constant tilt {tilt_angle:g} deg"),
                                 ("waves", BLUE, "wave motion")]:
        line_with_markers(ax2, x, (1 - grouped[column] / grouped["gross"]) * 100, color, label=label)
    ax2.set_xticks(x, [f"{int(b.left)}-{int(b.right)}" for b in grouped.index])
    ax2.set_xlabel("Significant wave height Hs [m]")
    ax2.set_ylabel("Energy loss [%]")
    ax2.axhline(0, color=BASELINE, linewidth=0.9)
    ax2.legend(frameon=False, fontsize=9)
    style_axes(ax2)

    constant_total = (1 - constant.sum() / gross.sum()) * 100
    waves_total = (1 - waves.sum() / gross.sum()) * 100
    titles(
        fig,
        f"Tilt loss: constant angle vs. wave motion ({t.name})",
        f"Total loss: constant {tilt_angle:g} deg tilt {constant_total:.2f} %, wave motion {waves_total:.2f} %. "
        "In high seas the wind is usually above rated speed, so tilting costs little.",
    )
    return finish(fig, output_file)
