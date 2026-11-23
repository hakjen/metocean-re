"""Figures: wind profile, wind shear and turbulence."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.turbulence import IEC_TI_REF, iec_normal_turbulence, turbulence_intensity, turbulent_power
from ..stats.profile import (
    hub_height_wind_speed,
    mean_wind_profile,
    rotor_equivalent_wind_speed,
    rotor_wind_speeds,
    wind_speed_at_height,
)
from ._style import (
    BLUE, DASHED, INK, INK_MUTED, INK_SECONDARY, ORANGE, SHADE, SURFACE, VIOLET, AQUA,
    finish, line_with_markers, style_axes, titles,
)


def plot_wind_profile(data, turbine=None, output_file="wind_profile.png"):
    """
    Left: mean wind speed against height at the NORA3 heights, with the
    rotor of the turbine. Right: the shear exponent across the rotor for
    every time step.
    """
    t = turbines.get(turbine)
    profile = mean_wind_profile(data)
    rotor = rotor_wind_speeds(data, t)

    # Interpolated line through the mean profile (power law between the heights)
    z_max = t.rotor_top * 1.15
    means = pd.DataFrame([data[[f"wind_speed_{z}m" for z in profile.index]].mean()])
    z_line = np.linspace(profile.index.min(), z_max, 200)
    u_line = [wind_speed_at_height(means, z).iloc[0] for z in z_line]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.6), gridspec_kw={"width_ratios": [1.2, 1]})

    ax1.axhspan(t.rotor_bottom, t.rotor_top, color=SHADE, zorder=1)
    ax1.axhline(t.hub_height, color=INK_MUTED, linewidth=0.8, zorder=2)
    ax1.plot(u_line, z_line, color=BLUE, linewidth=2, zorder=3, label="power law between heights")
    shown = profile[profile.index <= z_max]
    ax1.plot(shown.values, shown.index, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE,
             markeredgewidth=2, zorder=4, label="NORA3 mean")

    for name, column, z in [("rotor top", "top", t.rotor_top), ("hub", "hub", t.hub_height),
                            ("rotor bottom", "bottom", t.rotor_bottom)]:
        ax1.text(0.02, z, f"{name}  {z:.0f} m:  {rotor[column].mean():.2f} m/s",
                 transform=ax1.get_yaxis_transform(), va="bottom", fontsize=8.5, color=INK_SECONDARY)

    ax1.set_xlabel("Mean wind speed [m/s]")
    ax1.set_ylabel("Height above sea level [m]")
    ax1.set_ylim(0, z_max)
    ax1.set_xlim(min(u_line) - 2.5, max(u_line) + 0.5)
    ax1.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 0.1), fontsize=8.5)
    style_axes(ax1, grid_axis="both")

    alpha = rotor["alpha"].dropna()
    median = alpha.median()
    ax2.hist(alpha.clip(-0.2, 0.5), bins=np.linspace(-0.2, 0.5, 36), color=BLUE, rwidth=0.85, zorder=3)
    ax2.axvline(median, color=INK, linewidth=1, linestyle=DASHED, zorder=4)
    ax2.text(median, 1.0, f" median {median:.3f}", transform=ax2.get_xaxis_transform(), va="top",
             fontsize=8.5, color=INK_SECONDARY)
    ax2.set_xlabel("Shear exponent alpha across the rotor (clipped to -0.2 - 0.5)")
    ax2.set_ylabel("Number of hours")
    style_axes(ax2)

    difference = rotor["difference"].mean()
    titles(
        fig,
        f"Wind profile over the rotor ({t.name})",
        f"On average the wind at the top of the rotor is {difference:.2f} m/s "
        f"({difference / rotor['hub'].mean():.0%} of hub wind) stronger than at the bottom.",
    )
    return finish(fig, output_file)


def plot_wind_shear_explained(data, turbine=None, output_file="wind_shear_explained.png"):
    """
    Why a large top-bottom difference gives only a small energy effect.

    For bins of the shear exponent across the rotor:
    left   - how often each bin occurs
    middle - the difference in wind speed between top and bottom of the rotor
    right  - the energy with the rotor-equivalent wind speed compared with
             only the hub-height wind speed
    """
    t = turbines.get(turbine)
    rotor = rotor_wind_speeds(data, t)
    hub_power = t.power(rotor["hub"])
    rews_power = t.power(rotor_equivalent_wind_speed(data, t))

    edges = np.arange(-0.1, 0.45, 0.05)
    alpha_bin = pd.cut(rotor["alpha"].clip(edges[0] + 1e-6, edges[-1] - 1e-6), edges)
    grouped = pd.DataFrame({"difference": rotor["difference"], "hub": hub_power, "rews": rews_power}).groupby(
        alpha_bin, observed=False)
    share = grouped.size() / len(rotor) * 100
    difference = grouped["difference"].mean()
    energy_effect = (grouped["rews"].sum() / grouped["hub"].sum() - 1) * 100
    x = (edges[:-1] + edges[1:]) / 2

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharex=True)
    axes[0].bar(x, share, width=0.04, color=BLUE, zorder=3)
    axes[0].set_ylabel("Share of time [%]")
    axes[0].set_title("How often", loc="left", fontsize=10)

    axes[1].bar(x, difference, width=0.04, color=BLUE, zorder=3)
    axes[1].set_ylabel("Top - bottom wind speed [m/s]")
    axes[1].set_title("Wind speed difference over the rotor", loc="left", fontsize=10)

    line_with_markers(axes[2], x, energy_effect, ORANGE)
    axes[2].axhline(0, color=INK_MUTED, linewidth=0.9)
    axes[2].set_ylabel("Energy, REWS vs hub wind [%]")
    axes[2].set_title("Effect on energy", loc="left", fontsize=10)

    for ax in axes:
        ax.set_xlabel("Shear exponent across the rotor")
        style_axes(ax)

    total_effect = (rews_power.sum() / hub_power.sum() - 1) * 100
    titles(
        fig,
        f"Wind shear: large difference over the rotor, small effect on energy ({t.name})",
        f"Mean top - bottom difference {rotor['difference'].mean():.2f} m/s, but the energy changes only "
        f"{total_effect:+.2f} %: the stronger wind above the hub and the weaker wind below nearly cancel.",
    )
    return finish(fig, output_file)


def plot_turbulence_intensity(data, turbine=None, output_file="turbulence_intensity.png"):
    """Turbulence intensity at hub height against wind speed, compared with the IEC turbine classes."""
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t)
    ti = turbulence_intensity(data, t)

    edges = np.arange(3, 26, 1.0)
    grouped = ti.groupby(pd.cut(u, edges), observed=False)
    x = (edges[:-1] + edges[1:]) / 2
    mean, p90 = grouped.mean() * 100, grouped.quantile(0.9) * 100

    fig, ax = plt.subplots(figsize=(9, 5.2))
    u_fine = np.linspace(3, 25, 100)
    for name in IEC_TI_REF:
        ax.plot(u_fine, iec_normal_turbulence(u_fine, name) * 100, color=INK_MUTED, linewidth=1,
                linestyle=DASHED, zorder=2)
        ax.text(25.2, iec_normal_turbulence(25, name) * 100, f"IEC class {name}", va="center", fontsize=8.5,
                color=INK_SECONDARY)
    line_with_markers(ax, x, p90, VIOLET, label="NORA3, 90 % quantile")
    line_with_markers(ax, x, mean, BLUE, label="NORA3, mean")

    ax.set_xlabel("Wind speed at hub height [m/s]")
    ax.set_ylabel("Turbulence intensity [%]")
    ax.set_xlim(2, 28.5)
    ax.set_ylim(0, max(iec_normal_turbulence(3, "A") * 100, p90.max()) * 1.05)
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(0.88, 1))
    style_axes(ax)

    ti_15 = p90.iloc[np.argmin(np.abs(x - 15))]
    iec_15 = ", ".join(f"{name} {iec_normal_turbulence(15, name) * 100:.1f} %" for name in IEC_TI_REF)
    titles(
        fig,
        f"Turbulence intensity at hub height ({t.name}, {t.hub_height:.0f} m)",
        f"At 15 m/s the 90 % quantile is {ti_15:.1f} % (IEC classes: {iec_15}). "
        "TI is estimated from NORA3 model TKE.",
    )
    return finish(fig, output_file)


def plot_turbulence_power_curve(turbine=None, ti_levels=(0.05, 0.10, 0.15), output_file="turbulence_power_curve.png"):
    """How turbulence changes the effective power curve (bends it near cut-in and rated speed)."""
    t = turbines.get(turbine)
    u = np.linspace(0, 27, 541)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.plot(u, t.power(u), color=INK, linewidth=2, zorder=4, label="no turbulence")
    colors = [AQUA, BLUE, VIOLET]
    for ti, color in zip(ti_levels, colors):
        power = turbulent_power(t, u, ti * u)
        ax1.plot(u, power, color=color, linewidth=2, zorder=3, label=f"TI {ti:.0%}")
        ax2.plot(u, power - t.power(u), color=color, linewidth=2, zorder=3, label=f"TI {ti:.0%}")

    ax1.set_ylabel("Power [MW]")
    ax1.set_title("Power curve", loc="left", fontsize=10)
    ax2.axhline(0, color=INK_MUTED, linewidth=0.9)
    ax2.set_ylabel("Change in power [MW]")
    ax2.set_title("Difference from the curve without turbulence", loc="left", fontsize=10)
    for ax in (ax1, ax2):
        ax.set_xlabel("Mean wind speed [m/s]")
        ax.legend(frameon=False, fontsize=9)
        style_axes(ax)

    titles(fig, f"Effect of turbulence on the power curve ({t.name})",
           "Turbulence adds power just above cut-in, but removes power near rated speed, "
           "where gusts above rated cannot give more than full power.")
    return finish(fig, output_file)
