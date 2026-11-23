import os

import pytest

from metocean_re import stats, tables

dirname = os.path.dirname(__file__)
ds = stats.read_metocean_csv(os.path.join(dirname, "data", "NORA3_utsira_nord_2020_2022.csv"))


def test_table_turbines(tmp_path):
    output_file = tmp_path / "turbines.csv"
    table = tables.table_turbines(output_file=str(output_file))
    assert output_file.exists()
    assert {"NREL-5MW", "DTU-10MW", "IEA-15MW"} <= set(table.index)


def test_table_annual_energy_losses_adds_up():
    table = tables.table_annual_energy_losses(ds, 15, output_file=None)
    gross, net = table.loc["Gross", "energy_MWh_per_year"], table.loc["Net", "energy_MWh_per_year"]
    losses = table.drop(["Gross", "Net"])["energy_MWh_per_year"].sum()
    assert gross + losses == pytest.approx(net, abs=0.01)


def test_table_energy_production():
    table = tables.table_energy_production(ds, [5, 15], output_file=None)
    assert list(table.index) == ["NREL-5MW", "IEA-15MW"]
    assert (table["net_GWh_per_year"] < table["gross_GWh_per_year"]).all()


def test_table_stability_by_month_rows_sum_to_100():
    table = tables.table_stability_by_month(ds, output_file=None)
    assert len(table) == 12
    assert table.sum(axis=1).to_numpy() == pytest.approx(100, abs=0.5)


def test_table_losses_by_stability():
    table = tables.table_losses_by_stability(ds, 15, output_file=None)
    assert table["share_of_time"].sum() == pytest.approx(100, abs=0.01)  # values are rounded
