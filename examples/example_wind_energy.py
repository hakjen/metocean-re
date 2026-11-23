"""
Example: energy production, losses and loads for offshore wind turbines at
Utsira Nord, using NORA3 data (2020-2022) from tests/data.

Run from the repository root after "pip install -e .":
    python examples/example_wind_energy.py
"""

import os

from metocean_re import plots, stats, tables
from metocean_re.stats import turbines

dirname = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(dirname, "..", "outputs")

# Turbines to compare, chosen by rated power [MW]
TURBINES = [5, 10, 15]

# The turbine used for the detailed figures (15 MW is the default)
TURBINE = 15


def out(name):
    return os.path.join(OUTPUT_DIR, name)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = stats.read_metocean_csv(os.path.join(dirname, "..", "tests", "data", "NORA3_utsira_nord_2020_2022.csv"))
    print(f"NORA3 data, Utsira Nord: {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}, {len(df)} hours\n")

    # A custom turbine can be added like this (or loaded from a .cfg file
    # with turbines.load("my_turbines.cfg")):
    turbines.add("Example-12MW", rated_power=12, cut_in=3, rated_speed=11, cut_out=25,
                 hub_height=135, rotor_diameter=215, description="Made-up example turbine")

    # --- Tables ------------------------------------------------------------------
    print(tables.table_turbines(output_file=out("table_turbines.csv")), "\n")
    print(tables.table_energy_production(df, TURBINES, output_file=out("table_energy_production.csv"),
                                         tilt_angle=5.0), "\n")
    print(tables.table_annual_energy_losses(df, TURBINE, output_file=out("table_annual_energy_losses.csv"),
                                            tilt_angle=5.0), "\n")
    tables.table_losses_by_stability(df, TURBINE, output_file=out("table_losses_by_stability.csv"))
    tables.table_stability_by_month(df, output_file=out("table_stability_by_month.csv"))

    # --- Figures -----------------------------------------------------------------
    plots.plot_power_curves(TURBINES, output_file=out("power_curves.png"))
    plots.plot_wind_and_energy_distribution(df, TURBINE, output_file=out("wind_and_energy_distribution.png"))
    plots.plot_power_output(df, TURBINE, "2022-01-01", "2022-01-31", output_file=out("power_output_january.png"))
    plots.plot_monthly_energy(df, TURBINE, output_file=out("monthly_energy.png"))
    plots.plot_energy_per_year(df, TURBINE, output_file=out("energy_per_year.png"))
    plots.plot_turbine_comparison(df, TURBINES, output_file=out("turbine_comparison.png"), tilt_angle=5.0)

    plots.plot_wind_profile(df, TURBINE, output_file=out("wind_profile.png"))
    plots.plot_wind_shear_explained(df, TURBINE, output_file=out("wind_shear_explained.png"))
    plots.plot_turbulence_intensity(df, TURBINE, output_file=out("turbulence_intensity.png"))
    plots.plot_turbulence_power_curve(TURBINE, output_file=out("turbulence_power_curve.png"))

    plots.plot_stability_timeseries(df, "2022-05-01", "2022-05-31", output_file=out("stability_timeseries_may.png"))
    plots.plot_stability_by_month(df, output_file=out("stability_by_month.png"))
    plots.plot_stability_effects(df, TURBINE, output_file=out("stability_effects.png"))

    plots.plot_energy_losses(df, TURBINE, output_file=out("energy_losses.png"), tilt_angle=5.0)
    plots.plot_losses_by_stability(df, TURBINE, output_file=out("losses_by_stability.png"))
    plots.plot_maintenance_downtime(df, TURBINE, output_file=out("maintenance_downtime.png"))
    plots.plot_tilt_loss_comparison(df, TURBINE, tilt_angle=5.0, output_file=out("tilt_loss_comparison.png"))

    plots.plot_thrust(df, TURBINE, output_file=out("thrust.png"))
    plots.plot_loads_by_stability(df, TURBINE, output_file=out("loads_by_stability.png"))

    print(f"Tables and figures saved to {os.path.abspath(OUTPUT_DIR)}")
