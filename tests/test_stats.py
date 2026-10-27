import os

import numpy as np
import pandas as pd
import pytest

from metocean_re import stats
from metocean_re.stats import turbines

dirname = os.path.dirname(__file__)
ds = stats.read_metocean_csv(os.path.join(dirname, "data", "NORA3_utsira_nord_2020_2022.csv"))

HEIGHTS = [10, 20, 50, 100, 250, 500]


def profile_frame(alpha=0.1, u10=8.0, n=1):
    """A small dataset with a power-law wind profile and constant direction."""
    frame = pd.DataFrame({f"wind_speed_{z}m": [stats.power_law(u10, 10, z, alpha)] * n for z in HEIGHTS})
    for z in HEIGHTS:
        frame[f"wind_direction_{z}m"] = 270.0
    frame.index = pd.date_range("2020-01-01", periods=n, freq="h")
    return frame


# --- turbines -------------------------------------------------------------------


def test_choose_turbine_by_power_and_name():
    assert turbines.get(15).name == "IEA-15MW"
    assert turbines.get("dtu-10mw").rated_power == 10
    assert turbines.get() == turbines.get(turbines.DEFAULT_TURBINE)


def test_unknown_turbine_gives_clear_error():
    with pytest.raises(ValueError, match="Available"):
        turbines.get(7)


def test_add_and_load_turbine(tmp_path):
    turbines.add("Test-3MW", rated_power=3, cut_in=3, rated_speed=12, cut_out=25, hub_height=80, rotor_diameter=100)
    assert turbines.get(3).name == "Test-3MW"

    cfg = tmp_path / "custom.cfg"
    cfg.write_text("[Test-4MW]\nrated_power = 4\ncut_in = 3\nrated_speed = 12\ncut_out = 25\n"
                   "hub_height = 90\nrotor_diameter = 120\n")
    assert turbines.load(cfg) == ["Test-4MW"]
    assert turbines.get(4).hub_height == 90


def test_power_curve_shape():
    t = turbines.get(15)
    assert t.power([0, t.cut_in, t.rated_speed, 20, t.cut_out, 26]).tolist() == [0, 0, 15, 15, 15, 0]


# --- data and wind profile ------------------------------------------------------


def test_read_nora3():
    assert isinstance(ds.index, pd.DatetimeIndex)
    assert {"wind_speed_100m", "hs", "tp", "tke_100m", "sea_surface_temperature"} <= set(ds.columns)
    assert stats.measured_heights(ds) == {z: f"wind_speed_{z}m" for z in [10, 20, 50, 100, 250, 500, 750]}
    assert ds["relative_humidity_50m"].max() <= 1.0


@pytest.mark.parametrize("times", [
    ["2021-07-27 07:00:00", "2021-07-27 08:00:00"],
    ["27.07.2021 07:00", "27.07.2021 08:00"],
    ["27/07/2021 07:00", "27/07/2021 08:00"],
    ["07/27/2021 07:00", "07/27/2021 08:00"],
])
def test_time_formats(times):
    expected = pd.DatetimeIndex(["2021-07-27 07:00", "2021-07-27 08:00"])
    assert stats.parse_time(times).equals(expected)


def test_ambiguous_slash_dates_give_clear_error():
    with pytest.raises(ValueError, match="dd/mm/yyyy or mm/dd/yyyy"):
        stats.parse_time(["03/04/2021 07:00", "03/04/2021 08:00"])


def test_read_sorts_rows_by_time(tmp_path):
    path = tmp_path / "unsorted.csv"
    path.write_text("# comment\ntime,wind_speed_100m\n02.01.2021 00:00,5\n01.01.2021 00:00,4\n")
    df = stats.read_metocean_csv(path)
    assert list(df.index) == [pd.Timestamp("2021-01-01"), pd.Timestamp("2021-01-02")]
    assert list(df["wind_speed_100m"]) == [4, 5]


def test_power_law_interpolation_is_exact_for_power_law_profile():
    frame = profile_frame(alpha=0.12)
    assert stats.wind_speed_at_height(frame, 150).iloc[0] == pytest.approx(stats.power_law(8.0, 10, 150, 0.12))
    assert stats.shear_exponent(frame, 30, 270).iloc[0] == pytest.approx(0.12)
    assert stats.rotor_wind_speeds(frame, 15)["alpha"].iloc[0] == pytest.approx(0.12)


def test_measured_height_is_used_directly():
    assert (stats.wind_speed_at_height(ds, 100) == ds["wind_speed_100m"]).all()


def test_rews_equals_hub_speed_without_shear():
    assert stats.rotor_equivalent_wind_speed(profile_frame(alpha=0.0), 15).iloc[0] == pytest.approx(8.0)


def test_veer_reduces_rews():
    frame = profile_frame(alpha=0.0)
    for z in HEIGHTS:
        frame[f"wind_direction_{z}m"] = 250.0 + 0.1 * z  # turns clockwise with height
    plain = stats.rotor_equivalent_wind_speed(frame, 15).iloc[0]
    with_veer = stats.rotor_equivalent_wind_speed(frame, 15, include_veer=True).iloc[0]
    assert with_veer < plain
    assert stats.wind_veer(frame, 15).iloc[0] == pytest.approx(24.0)


# --- stability ------------------------------------------------------------------


def test_richardson_relation_is_monotonic():
    zeta = np.linspace(-5, 5, 101)
    assert np.all(np.diff(stats.stability._richardson_from_zeta(zeta, 50)) > 0)


def test_stability_classes():
    classes = stats.stability_class([-30, -150, -300, 1e6, -1e6, 300, 100, 20])
    assert classes.tolist() == ["very unstable", "unstable", "near-neutral unstable", "neutral", "neutral",
                                "near-neutral stable", "stable", "very stable"]


def test_warm_air_over_cold_sea_is_stable():
    frame = ds.iloc[:1].copy()
    frame["sea_surface_temperature"] = frame["air_temperature_50m"] - 5  # air much warmer than sea
    assert stats.obukhov_length(frame).iloc[0] > 0
    frame["sea_surface_temperature"] = frame["air_temperature_50m"] + 5
    assert stats.obukhov_length(frame).iloc[0] < 0


# --- turbulence -----------------------------------------------------------------


def test_sigma_from_tke():
    tke = 0.5 * 1.0**2 * (1 + 0.8**2 + 0.5**2)
    assert stats.sigma_u_from_tke(tke) == pytest.approx(1.0)


def test_turbulent_power_without_turbulence_is_power_curve():
    t = turbines.get(15)
    u = np.array([5.0, 9.0, 12.0, 20.0])
    assert stats.turbulent_power(t, u, 0.0) == pytest.approx(t.power(u))


def test_turbulence_lowers_power_at_rated_speed():
    t = turbines.get(15)
    assert stats.turbulent_power(t, [t.rated_speed], 1.0)[0] < t.rated_power


# --- energy and losses ----------------------------------------------------------


def test_aep_is_between_zero_and_rated():
    t = turbines.get(15)
    assert 0 < stats.annual_energy_production(ds, t) < t.rated_power * stats.HOURS_PER_YEAR


def test_fixed_losses():
    assert stats.availability_loss(14) == pytest.approx(14 / 365.25)
    assert stats.electrical_loss(0.03) == 0.03


def test_no_tilt_means_no_loss():
    assert stats.tilt_loss(ds, 15, tilt_angle=0) == pytest.approx(0)
    assert stats.wave_tilt_loss(ds, 15, response=0) == pytest.approx(0)


def test_repair_waits_for_calm_weather():
    frame = pd.DataFrame({"hs": [3, 3, 1, 1, 1, 3]}, index=pd.date_range("2020-01-01", periods=6, freq="h"))
    downtime, _ = stats.repair_downtime(frame, repair_hours=2, hs_limit=1.5)
    # A failure at hour 0 waits until hour 2, then repairs in 2 h -> 4 h downtime
    assert downtime.iloc[0] == 4


def test_hysteresis_keeps_turbine_stopped():
    frame = profile_frame(alpha=0.0, n=4)
    for z in HEIGHTS:
        frame[f"wind_speed_{z}m"] = [15, 26, 22, 15]
    assert stats.power_with_hysteresis(frame, 15, restart_speed=20).tolist() == [15, 0, 0, 15]


def test_loss_table_adds_up():
    table = stats.annual_energy_losses(ds, 15, tilt_angle=5)
    assert table.attrs["gross_MWh"] - table["loss_MWh"].sum() == pytest.approx(table.attrs["net_MWh"])


# --- loads ----------------------------------------------------------------------


def test_thrust_coefficient_limits():
    ct = stats.thrust_coefficient(15, [2.0, 8.0, 20.0, 26.0])
    assert ct[0] == 0 and ct[-1] == 0
    assert 0 < ct[2] < ct[1] <= 8 / 9


def test_fatigue_damage_shares_sum_to_one():
    assert stats.relative_fatigue_damage(ds.iloc[:500], 15).sum() == pytest.approx(1.0)
