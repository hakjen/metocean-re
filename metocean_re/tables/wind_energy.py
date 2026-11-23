"""
Tables of wind energy results. Each function returns a DataFrame and, if
output_file is given, saves it as a CSV file.
"""

import numpy as np
import pandas as pd

from ..stats import turbines
from ..stats.stability import CLASS_NAMES, obukhov_length, stability_class
from ..stats.wind_losses import annual_energy_losses, losses_by_stability
from ..stats.profile import hub_height_wind_speed
from ..stats.wind_power import HOURS_PER_YEAR, fit_weibull


def _save(table, output_file):
    if output_file:
        table.to_csv(output_file)
    return table


def table_turbines(output_file="table_turbines.csv"):
    """All available turbine types and their parameters."""
    return _save(turbines.table(), output_file)


def table_annual_energy_losses(data, turbine=None, output_file="table_annual_energy_losses.csv", **loss_options):
    """
    Gross energy, each loss and net energy [MWh/year] for one turbine.
    loss_options are passed on to stats.annual_energy_losses().
    """
    losses = annual_energy_losses(data, turbine, **loss_options)
    table = pd.DataFrame({"loss_percent": losses["loss_fraction"] * 100, "energy_MWh_per_year": -losses["loss_MWh"]})
    table.loc["Gross"] = [np.nan, losses.attrs["gross_MWh"]]
    table.loc["Net"] = [np.nan, losses.attrs["net_MWh"]]
    table = table.reindex(["Gross", *losses.index, "Net"])
    return _save(table.round(3), output_file)


def table_energy_production(data, turbine_list=None, output_file="table_energy_production.csv", **loss_options):
    """Gross and net annual energy production and capacity factors for several turbines."""
    rows = {}
    for choice in turbine_list or turbines.names():
        t = turbines.get(choice)
        losses = annual_energy_losses(data, t, **loss_options)
        gross, net = losses.attrs["gross_MWh"], losses.attrs["net_MWh"]
        rows[t.name] = {
            "rated_power_MW": t.rated_power,
            "hub_height_m": t.hub_height,
            "gross_GWh_per_year": gross / 1000,
            "net_GWh_per_year": net / 1000,
            "gross_capacity_factor": gross / (t.rated_power * HOURS_PER_YEAR),
            "net_capacity_factor": net / (t.rated_power * HOURS_PER_YEAR),
        }
    return _save(pd.DataFrame.from_dict(rows, orient="index").round(3), output_file)


def table_losses_by_stability(data, turbine=None, output_file="table_losses_by_stability.csv"):
    """Share of time and energy, and the atmospheric losses [%], per stability class."""
    return _save((losses_by_stability(data, turbine) * 100).round(3), output_file)


def table_stability_by_month(data, output_file="table_stability_by_month.csv"):
    """Share of time [%] in each stability class for each calendar month."""
    classes = stability_class(obukhov_length(data))
    table = pd.crosstab(classes.index.month, classes, normalize="index").reindex(columns=CLASS_NAMES, fill_value=0)
    table.index.name = "month"
    return _save((table * 100).round(1), output_file)


def table_site_comparison(datasets, turbine=None, output_file="table_site_comparison.csv", **loss_options):
    """
    Key numbers for the same turbine at several sites, one column per site.

    datasets is a dict {site name: data}; loss_options are passed on to
    stats.annual_energy_losses().
    """
    t = turbines.get(turbine)
    columns = {}
    for name, data in datasets.items():
        u = hub_height_wind_speed(data, t).dropna()
        losses = annual_energy_losses(data, t, **loss_options)
        gross, net = losses.attrs["gross_MWh"], losses.attrs["net_MWh"]
        classes = stability_class(obukhov_length(data))
        columns[name] = {
            "period": f"{data.index[0]:%Y-%m-%d} to {data.index[-1]:%Y-%m-%d}",
            "mean_wind_speed_hub_m_s": u.mean(),
            "weibull_shape_k": fit_weibull(u)[0],
            "time_at_rated_or_above_percent": (u >= t.rated_speed).mean() * 100,
            "gross_GWh_per_year": gross / 1000,
            "net_GWh_per_year": net / 1000,
            "net_capacity_factor_percent": net / (t.rated_power * HOURS_PER_YEAR) * 100,
            "total_loss_percent": (1 - net / gross) * 100,
            "maintenance_loss_percent": losses.loc["Maintenance", "loss_fraction"] * 100,
            "time_stable_percent": classes.isin(["near-neutral stable", "stable", "very stable"]).mean() * 100,
            "mean_hs_m": data["hs"].mean() if "hs" in data else np.nan,
        }
    table = pd.DataFrame(columns)
    numbers = table.drop(index="period").astype(float).round(3)
    return _save(pd.concat([table.loc[["period"]], numbers]), output_file)
