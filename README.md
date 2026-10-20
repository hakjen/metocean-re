# metocean-re
Python tool for renewable energy analysis from metocean data

metocean-re is an open-source Python package for analysing renewable energy potential from metocean data. It turns time series of wind, waves, and currents (from hindcasts, reanalyses, or measurements) into energy-focused metrics: resource statistics, power production estimates using turbine and wave energy converter power curves/matrices, capacity factors, variability and intermittency, and combined wind–wave co-location analysis. It is designed to work alongside metocean-api for data retrieval and metocean-stats for general metocean statistics.

## Installation

```shell
git clone https://github.com/MET-OM/metocean-re.git
cd metocean-re
pip install -e .
```

Run the tests with `pip install -e .[test]` and `pytest`.

## Structure

The package follows the structure of [metocean-stats](https://github.com/MET-OM/metocean-stats):

| Module | Content |
|---|---|
| `metocean_re.stats` | calculations: wind over the rotor, atmospheric stability, turbulence, power production, energy losses, loads |
| `metocean_re.stats.turbines` | turbine types (`turbines.cfg`), chosen by rated power or name |
| `metocean_re.plots` | figures (`output_file=...`, return the figure) |
| `metocean_re.tables` | tables (return a DataFrame, save as CSV) |

## Example

```python
from metocean_re import plots, stats, tables
from metocean_re.stats import turbines

df = stats.read_metocean_csv("tests/data/NORA3_utsira_nord_2020_2022.csv")

t = turbines.get(15)                                    # by rated power [MW] or name
losses = stats.annual_energy_losses(df, t)
tables.table_energy_production(df, [5, 10, 15])
plots.plot_losses_by_stability(df, t)
```

See `examples/example_wind_energy.py` for the full workflow.

## Data

The functions use NORA3 column names as written by
[metocean-api](https://github.com/MET-OM/metocean-api). The test dataset
`tests/data/NORA3_utsira_nord_2020_2022.csv` (Utsira Nord, hourly 2020-2022)
is made from NORA3 (MET Norway) with `examples/download_nora3.py` and
`examples/build_dataset.py`.

NORA3 data are provided by the Norwegian Meteorological Institute (MET Norway)
under the [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
licence. Reference for the atmospheric hindcast:

Haakenstad, H., Breivik, Ø., Furevik, B. R., Reistad, M., Bohlinger, P. and
Aarnes, O. J. (2021). NORA3: A nonhydrostatic high-resolution hindcast of the
North Sea, the Norwegian Sea, and the Barents Sea. *Journal of Applied
Meteorology and Climatology* 60(10), 1443-1464.
https://doi.org/10.1175/JAMC-D-21-0029.1

The sources for the formulas in `metocean_re/stats` are listed in
[docs/referanser.md](docs/referanser.md).

Developed with assistance from Claude (Anthropic).
