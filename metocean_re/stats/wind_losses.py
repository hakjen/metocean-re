"""
Energy losses: from gross to net annual energy production.

Gross production is the power curve applied to the hub-height wind speed.
Each loss below has its own function returning the loss as a fraction of
the energy (0.05 = 5 %); negative values are gains.

    Fixed
        availability_loss        fixed number of days per year stopped for maintenance
        electrical_loss          cables, transformers etc.
    Weather-dependent maintenance
        weather_maintenance_loss repairs can only be done when the waves are low enough
    Atmosphere
        air_density_loss         cold, dense air gives more power; warm air less
        turbulence_loss          wind fluctuations within the hour
        wind_shear_loss          wind speed varying over the rotor height
        wind_veer_loss           wind direction varying over the rotor height
        high_wind_hysteresis_loss  after a storm stop, restart only below a lower wind speed
    Floating turbine
        tilt_loss                rotor tilted by a constant angle
        wave_tilt_loss           rotor tilting back and forth with the waves

annual_energy_losses() combines them; the losses are applied one after
another, so each acts on what is left:  net = gross * (1 - L1) * (1 - L2) * ...
Interactions between the atmospheric losses are ignored (each is computed
against the gross production on its own).

losses_by_stability() gives the atmospheric losses per stability class.
"""

import numpy as np
import pandas as pd

from . import turbines
from .wind_power import HOURS_PER_YEAR, power_output
from .stability import obukhov_length, stability_class
from .turbulence import power_with_turbulence
from .profile import hub_height_wind_speed, rotor_equivalent_wind_speed, value_at_height

GRAVITY = 9.81  # m/s^2

# Power curves are given for the standard air density at sea level
# (ISO 2533:1975, Standard Atmosphere).
STANDARD_AIR_DENSITY = 1.225  # kg/m^3


def _time_step_hours(data):
    """Length of one time step [hours]."""
    seconds = np.diff(data.index.values).astype("timedelta64[s]").astype(float)
    return float(np.median(seconds)) / 3600


def _loss(power, reference):
    """Loss fraction between two power time series."""
    return 1 - power.sum() / reference.sum()


# --- Fixed losses -------------------------------------------------------------


def availability_loss(downtime_days=14):
    """Share of the year the turbine is stopped for maintenance (default two weeks)."""
    return downtime_days / 365.25


def electrical_loss(fraction=0.02):
    """Electrical losses in the turbine and grid connection, as a fixed fraction."""
    return fraction


# --- Weather-dependent maintenance ----------------------------------------------


def repair_downtime(data, repair_hours=12, hs_limit=2.0):
    """
    Downtime [hours] if the turbine fails at each time step.

    A repair needs `repair_hours` in a row with significant wave height below
    `hs_limit` [m] (the limit for safe access by vessel). The turbine is down
    from the failure until the end of the first such weather window.

    Returns a Series, plus the index position where each repair ends (used
    internally to sum the lost energy).
    """
    dt = _time_step_hours(data)
    n = int(np.ceil(repair_hours / dt))
    calm = (data["hs"] < hs_limit).to_numpy()

    # A weather window starts at i if the next n time steps are all calm
    calm_ahead = pd.Series(calm[::-1]).rolling(n).sum().to_numpy()[::-1]
    window_start = calm_ahead == n

    # First window start at or after each time step (len(data) if none)
    positions = np.where(window_start, np.arange(len(data)), np.nan)
    next_start = pd.Series(positions).bfill().fillna(len(data)).to_numpy(dtype=int)
    repair_end = np.minimum(next_start + n, len(data))

    downtime = pd.Series((repair_end - np.arange(len(data))) * dt, index=data.index, name="downtime_hours")
    return downtime, repair_end


def weather_maintenance_loss(data, turbine=None, failures_per_year=8.3, repair_hours=12, hs_limit=2.0):
    """
    Expected energy loss from repairs that have to wait for low waves.

    A failure can happen at any time step with equal probability. For each
    possible failure time, the energy lost until the repair is done is
    found from the time series; the average loss per failure is multiplied
    by the number of failures per year.

    Default failure rate and repair time from Carroll et al. (2016), Wind
    Energy 19, 1107-1119: 8.3 failures per turbine per year (sec. 5.1,
    p. 1110), and 12 h as the mean repair time weighted by failure rate
    (Table II, p. 1117: minor 6.7 h, major 17.6 h, replacement 116 h; the
    repair time excludes travel and waiting for access). Hs < 2.0 m is an
    assumption. The result depends strongly on hs_limit - see
    plots.plot_maintenance_downtime().
    """
    t = turbines.get(turbine)
    power = power_output(data, t).to_numpy()
    dt = _time_step_hours(data)

    _, repair_end = repair_downtime(data, repair_hours, hs_limit)
    energy_before = np.concatenate([[0], np.cumsum(power * dt)])  # MWh produced before each step
    lost_per_failure = energy_before[repair_end] - energy_before[: len(data)]

    lost_per_year = failures_per_year * lost_per_failure.mean()
    return lost_per_year / (power.mean() * HOURS_PER_YEAR)


# --- Atmosphere -----------------------------------------------------------------


def power_with_air_density(data, turbine=None):
    """
    Power output [MW] corrected for the air density at hub height.

    For a pitch-regulated turbine the wind speed is scaled so that the
    kinetic energy flux matches the standard density:

        u_n = u * (rho / rho_0) ^ (1/3)

    Source: IEC 61400-12-1:2017, air density normalisation of the wind speed
    for pitch-regulated turbines.
    """
    t = turbines.get(turbine)
    rho = value_at_height(data, t.hub_height, "density")
    u = hub_height_wind_speed(data, t)
    u_n = u * (rho / STANDARD_AIR_DENSITY) ** (1 / 3)
    power = np.where(u > t.cut_out, 0.0, t.power(u_n))
    return pd.Series(power, index=data.index, name="power_MW")


def air_density_loss(data, turbine=None):
    """Loss from air density differing from 1.225 kg/m3 (negative = gain from dense, cold air)."""
    t = turbines.get(turbine)
    return _loss(power_with_air_density(data, t), power_output(data, t))


def turbulence_loss(data, turbine=None):
    """Loss from turbulence smoothing the power curve (see turbulence.power_with_turbulence())."""
    t = turbines.get(turbine)
    return _loss(power_with_turbulence(data, t), power_output(data, t))


def wind_shear_loss(data, turbine=None):
    """
    Difference in energy between using the rotor-equivalent wind speed
    (wind speed varying over the rotor) and only the hub-height wind speed.

    The wind is stronger above the hub and weaker below it. Because energy
    scales with u^3, the two halves do not cancel exactly: with a typical
    offshore profile the rotor-equivalent wind speed is slightly lower than
    the hub wind (a small loss), with a strongly curved profile it can be
    higher (a gain).
    """
    t = turbines.get(turbine)
    rews = rotor_equivalent_wind_speed(data, t)
    return _loss(pd.Series(t.power(rews)), pd.Series(t.power(hub_height_wind_speed(data, t))))


def wind_veer_loss(data, turbine=None):
    """
    Loss from the wind direction changing over the rotor height: parts of
    the rotor see the wind at an angle and only the component u * cos(dphi)
    is used (IEC 61400-12-1:2017, REWS with veer).
    """
    t = turbines.get(turbine)
    with_veer = rotor_equivalent_wind_speed(data, t, include_veer=True)
    without_veer = rotor_equivalent_wind_speed(data, t)
    return _loss(pd.Series(t.power(with_veer)), pd.Series(t.power(without_veer)))


def power_with_hysteresis(data, turbine=None, restart_speed=20.0):
    """
    Power output [MW] with high-wind hysteresis: after shutting down above
    cut-out, the turbine waits until the wind drops below restart_speed
    [m/s] before starting again. 20 m/s is a typical value, not from a
    specific turbine.
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t).to_numpy()
    running = np.ones(len(u), dtype=bool)
    stopped = False
    for i, speed in enumerate(u):
        if speed > t.cut_out:
            stopped = True
        elif stopped and speed < restart_speed:
            stopped = False
        running[i] = not stopped
    return pd.Series(np.where(running, t.power(u), 0.0), index=data.index, name="power_MW")


def high_wind_hysteresis_loss(data, turbine=None, restart_speed=20.0):
    """Energy lost while waiting to restart after a storm stop."""
    t = turbines.get(turbine)
    return _loss(power_with_hysteresis(data, t, restart_speed), power_output(data, t))


# --- Tilted rotor (floating turbine) ----------------------------------------------
#
# When the rotor is tilted by an angle theta, it only "sees" the part of the
# wind that blows straight into it, u * cos(theta). Below rated wind speed
# the power scales with u^3, so the loss is about 1 - cos^3(theta). Above
# rated wind speed there is wind to spare, and the turbine still makes rated
# power - so the loss is found by running u * cos(theta) through the power curve.


def power_with_tilt(data, turbine=None, tilt_angle=0.0, wave_amplitude=0.0, n_phases=36):
    """
    Power output [MW] of a tilted rotor.

    The tilt angle [degrees] varies periodically with the waves:

        theta(t) = tilt_angle + wave_amplitude * sin(2 * pi * t / Tp)

    tilt_angle     : constant tilt [deg]
    wave_amplitude : amplitude of the wave motion [deg], a number or one value
                     per time step (e.g. from wave_tilt_amplitude())

    For each time step the power is averaged over one full wave period,
    sampled at n_phases points.
    """
    t = turbines.get(turbine)
    u = hub_height_wind_speed(data, t).to_numpy()[:, np.newaxis]
    amplitude = np.broadcast_to(np.asarray(wave_amplitude, dtype=float), (len(data),))[:, np.newaxis]

    phase = np.linspace(0, 2 * np.pi, n_phases, endpoint=False)[np.newaxis, :]
    theta = np.radians(tilt_angle + amplitude * np.sin(phase))

    power = t.power(u * np.cos(theta))
    # The turbine still shuts down when the actual wind is above cut-out
    power[np.broadcast_to(u > t.cut_out, power.shape)] = 0.0
    return pd.Series(power.mean(axis=1), index=data.index, name="power_MW")


def wave_tilt_amplitude(data, hs="hs", tp="tp", response=1.0):
    """
    Tilt amplitude [deg] of a floating turbine caused by the waves.

    Simple model: the platform follows the slope of the waves. For a deep
    water wave with height Hs and period Tp,

        wavelength L = g * Tp^2 / (2 * pi)
        max slope    = arctan(pi * Hs / L)

    so higher and shorter (steeper) waves give more tilt. `response` scales
    the result: 1.0 means the platform follows the waves fully, 0.5 means it
    only tilts half as much (large floaters move less than the waves).

    Source (deep water wavelength): Holthuijsen (2007), Waves in Oceanic and
    Coastal Waters, Cambridge University Press, sec. 5.4.3, eq. (5.4.18).
    The max slope pi * H / L follows from the harmonic wave in Note 5A
    (p. 118). Using Hs for H in an irregular sea is a simplification.
    """
    wavelength = GRAVITY * data[tp] ** 2 / (2 * np.pi)
    slope = np.degrees(np.arctan(np.pi * data[hs] / wavelength))
    return (response * slope).fillna(0.0).rename("tilt_amplitude_deg")


def tilt_loss(data, turbine=None, tilt_angle=5.0):
    """Energy loss from a rotor tilted by a constant angle [deg]."""
    t = turbines.get(turbine)
    return _loss(power_with_tilt(data, t, tilt_angle=tilt_angle), power_output(data, t))


def wave_tilt_loss(data, turbine=None, response=1.0):
    """Energy loss from the rotor tilting back and forth with the waves."""
    t = turbines.get(turbine)
    amplitude = wave_tilt_amplitude(data, response=response)
    return _loss(power_with_tilt(data, t, wave_amplitude=amplitude), power_output(data, t))


# --- All losses together ------------------------------------------------------


def annual_energy_losses(
    data,
    turbine=None,
    maintenance="weather",
    downtime_days=14,
    failures_per_year=8.3,
    repair_hours=12,
    hs_limit=2.0,
    electrical=0.02,
    restart_speed=20.0,
    tilt_angle=0.0,
    wave_response=1.0,
):
    """
    Gross and net annual energy production with a breakdown of the losses.

    maintenance   : 'weather' (repairs wait for Hs < hs_limit) or 'fixed' (downtime_days per year)
    tilt_angle    : constant tilt [deg]; 0 leaves this loss out
    wave_response : see wave_tilt_amplitude(); 0 leaves the wave loss out
    Other arguments: see the individual loss functions.

    Returns a DataFrame with one row per loss and the columns
        loss_fraction   the loss as a fraction (0-1), negative = gain
        loss_MWh        energy lost [MWh/year]
    plus the attributes .attrs['gross_MWh'] and .attrs['net_MWh'].
    """
    t = turbines.get(turbine)
    if maintenance == "weather":
        maintenance_loss = weather_maintenance_loss(data, t, failures_per_year, repair_hours, hs_limit)
    else:
        maintenance_loss = availability_loss(downtime_days)

    fractions = {
        "Maintenance": maintenance_loss,
        "Electrical": electrical_loss(electrical),
        "Air density": air_density_loss(data, t),
        "Turbulence": turbulence_loss(data, t),
        "Wind shear": wind_shear_loss(data, t),
        "Wind veer": wind_veer_loss(data, t),
        "High-wind hysteresis": high_wind_hysteresis_loss(data, t, restart_speed),
    }
    if tilt_angle:
        fractions["Constant tilt"] = tilt_loss(data, t, tilt_angle)
    if wave_response:
        fractions["Wave motion"] = wave_tilt_loss(data, t, wave_response)

    gross = power_output(data, t).mean() * HOURS_PER_YEAR
    remaining = gross
    rows = {}
    for name, fraction in fractions.items():
        lost = remaining * fraction
        rows[name] = {"loss_fraction": fraction, "loss_MWh": lost}
        remaining -= lost

    table = pd.DataFrame.from_dict(rows, orient="index")
    table.attrs["gross_MWh"] = gross
    table.attrs["net_MWh"] = remaining
    return table


def losses_by_stability(data, turbine=None, restart_speed=20.0):
    """
    The atmospheric losses [fraction] for each stability class.

    Returns a DataFrame with one row per stability class and one column per
    loss, plus 'share_of_time' and 'share_of_energy' (gross) of each class.
    """
    t = turbines.get(turbine)
    gross = power_output(data, t)
    rews = pd.Series(t.power(rotor_equivalent_wind_speed(data, t)), index=data.index)
    rews_veer = pd.Series(t.power(rotor_equivalent_wind_speed(data, t, include_veer=True)), index=data.index)

    series = pd.DataFrame({
        "gross": gross,
        "air_density": power_with_air_density(data, t),
        "turbulence": power_with_turbulence(data, t),
        "rews": rews,
        "rews_veer": rews_veer,
        "hysteresis": power_with_hysteresis(data, t, restart_speed),
    })
    classes = stability_class(obukhov_length(data))
    sums = series.groupby(classes, observed=False).sum()

    table = pd.DataFrame({
        "share_of_time": classes.value_counts(normalize=True).reindex(sums.index),
        "share_of_energy": sums["gross"] / sums["gross"].sum(),
        "Air density": 1 - sums["air_density"] / sums["gross"],
        "Turbulence": 1 - sums["turbulence"] / sums["gross"],
        "Wind shear": 1 - sums["rews"] / sums["gross"],
        "Wind veer": 1 - sums["rews_veer"] / sums["rews"],
        "High-wind hysteresis": 1 - sums["hysteresis"] / sums["gross"],
    })
    return table
