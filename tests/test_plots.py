import os

import pytest

from metocean_re import plots, stats

dirname = os.path.dirname(__file__)
ds = stats.read_metocean_csv(os.path.join(dirname, "data", "NORA3_utsira_nord_2020_2022.csv"))

# Every figure function with its arguments (besides output_file)
FIGURES = [
    (plots.plot_power_curves, ([5, 10, 15],)),
    (plots.plot_wind_and_energy_distribution, (ds, 15)),
    (plots.plot_power_output, (ds, 15, "2022-01-01", "2022-01-31")),
    (plots.plot_monthly_energy, (ds, 15)),
    (plots.plot_energy_per_year, (ds, 15)),
    (plots.plot_turbine_comparison, (ds, [5, 15])),
    (plots.plot_wind_profile, (ds, 15)),
    (plots.plot_wind_shear_explained, (ds, 15)),
    (plots.plot_turbulence_intensity, (ds, 15)),
    (plots.plot_turbulence_power_curve, (15,)),
    (plots.plot_stability_timeseries, (ds, "2022-05-01", "2022-05-31")),
    (plots.plot_stability_by_month, (ds,)),
    (plots.plot_stability_effects, (ds, 15)),
    (plots.plot_energy_losses, (ds, 15)),
    (plots.plot_losses_by_stability, (ds, 15)),
    (plots.plot_maintenance_downtime, (ds, 15)),
    (plots.plot_tilt_loss_comparison, (ds, 15)),
    (plots.plot_thrust, (ds, 15)),
    (plots.plot_loads_by_stability, (ds, 15)),
]


@pytest.mark.parametrize("function, args", FIGURES, ids=[f.__name__ for f, _ in FIGURES])
def test_figure_is_saved(function, args, tmp_path):
    output_file = tmp_path / f"{function.__name__}.png"
    fig = function(*args, output_file=str(output_file))
    assert output_file.exists()
    assert fig.axes, "the figure has no axes"


def test_monthly_energy_less_than_a_year(tmp_path):
    # Data that do not cover every calendar month (e.g. a short NORA3 download in the app)
    fig = plots.plot_monthly_energy(ds.loc["2021-02"], 15, output_file=str(tmp_path / "monthly.png"))
    assert "Feb gives 1.0x the energy of Feb" in fig.texts[-1].get_text()


def test_obukhov_validation_figure(tmp_path):
    # The estimate compared with itself must give a perfect match
    reference = ds.iloc[:200].copy()
    reference["atmosphere_obukhov_length"] = stats.obukhov_length(reference)
    fig = plots.plot_obukhov_validation(ds.iloc[:200], reference, output_file=str(tmp_path / "validation.png"))
    assert "100%" in fig.texts[-1].get_text()
