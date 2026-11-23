"""
Streamlit app: the figures from metocean_re.plots in the browser.

Run with (from the project root):
    pip install -e .[app]
    streamlit run app/streamlit_app.py

The app only calls functions from the metocean_re package; all
calculations and figures live there. The only code here is reading the
data: the test dataset, an uploaded file or a NORA3 point from metocean-api.
"""

import dataclasses
import io
import re
import zipfile
from contextlib import contextmanager
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from PIL import Image

matplotlib.use("Agg")  # draw to images only; a server has no screen

from metocean_re import plots, stats, tables
from metocean_re.stats import turbines

st.set_page_config(page_title="Wind energy", layout="wide")
title_area = st.empty()  # filled in when the turbine is known, so the title stays above the map

# The test dataset (see examples/build_dataset.py)
EXAMPLE_FILE = Path(__file__).resolve().parent.parent / "tests" / "data" / "NORA3_utsira_nord_2020_2022.csv"
SITE = {"name": "Utsira Nord", "lat": 59.27, "lon": 4.54}

# Variables the calculations need at two heights or more, to find them at hub height and over the rotor
# (see metocean_re/stats/aux_funcs.py for all columns)
PROFILE_VARIABLES = ["wind_speed", "wind_direction", "air_temperature", "relative_humidity", "density", "tke"]
WAVE_COLUMNS = ["hs", "tp", "hs_sea", "tp_sea", "hs_swell", "tp_swell"]
ATM3HR_PREFIXES = ("air_temperature_", "relative_humidity_", "density_", "tke_")

# All sources and assumptions behind the calculations
REFERENCES_URL = "https://github.com/hakjen/metocean-re/blob/add-wind-energy/docs/references.md"


@st.cache_data
def load_data(uploaded):
    """The uploaded NORA3 CSV file (same format as the test dataset), or the test dataset."""
    return stats.read_metocean_csv(uploaded if uploaded else EXAMPLE_FILE)


def download_seconds(months, waves=True):
    """
    Rough download time [s] for load_nora3(), measured in October 2026 at
    59-60 N, 4 E: wind about 17 s + 10 s per month, atm3hr 10 s + 25 s per
    month, waves 6 s per month. Depends on the load on thredds.met.no.
    """
    return 30 + months * (35 + (6 if waves else 0))


@contextmanager
def report_months(callback):
    """
    metocean-api loops over the monthly NORA3 files with tqdm; pass the
    progress on to callback(done, total) instead. If the hook is missing
    (another metocean-api version), the download works without progress.
    """
    try:
        from metocean_api.ts.internal.metno import met_product
        original = met_product.tqdm
    except (ImportError, AttributeError):
        yield
        return

    def months(iterable, *args, **kwargs):
        items = list(iterable)
        for done, item in enumerate(items):
            callback(done, len(items))
            yield item

    months.write = original.write
    met_product.tqdm = months
    try:
        yield
    finally:
        met_product.tqdm = original


def load_nora3(lon, lat, start_time, end_time, waves=True, progress=None):
    """
    Download NORA3 data for any point with metocean-api, in the same format
    as the test dataset (merged as in examples/build_dataset.py).

    Gets NORA3_wind_sub and NORA3_atm3hr_sub, and NORA3_wave_sub if waves=True
    (see download_seconds()). metocean-api keeps the downloaded files in
    ./cache, so asking for the same point and period again is fast.
    progress(fraction, text) is called as the monthly files come in.
    """
    from metocean_api import ts

    products = [("NORA3_wind_sub", "wind"), ("NORA3_atm3hr_sub", "temperature, humidity and TKE")]
    if waves:
        products.append(("NORA3_wave_sub", "waves"))
    progress = progress or (lambda fraction, text: None)

    def download(k):
        product, label = products[k]

        def report(done, total):
            progress((k + done / total) / len(products),
                     f"Downloading {label} ({k + 1}/{len(products)}): month {done + 1} of {total}")

        progress(k / len(products), f"Downloading {label} ({k + 1}/{len(products)}): finding the nearest grid point")
        series = ts.TimeSeries(lon=lon, lat=lat, start_time=str(start_time), end_time=str(end_time),
                               product=product)
        with report_months(report):
            series.import_data(save_csv=False, save_nc=False, use_cache=True)
        df = series.data
        df.index = pd.to_datetime(df.index)
        return df

    wind = download(0)
    atm3hr = download(1)
    atm3hr = atm3hr[[c for c in atm3hr.columns if c.startswith(ATM3HR_PREFIXES) or c == "sea_surface_temperature"]]
    atm3hr = atm3hr.reindex(wind.index.union(atm3hr.index)).interpolate(method="time", limit=2).reindex(wind.index)
    parts = [wind, atm3hr]
    if waves:
        wave = download(2)
        parts.append(wave[[c for c in WAVE_COLUMNS if c in wave.columns]].reindex(wind.index))

    df = pd.concat(parts, axis=1)
    for column in [c for c in df.columns if c.startswith("relative_humidity_")]:
        if df[column].max() > 1.5:  # percent -> fraction
            df[column] = df[column] / 100
    df.index.name = "time"
    return df


# Cached figures and results: moving one slider only redraws the figures that depend on it. The data
# are hashed by content (a few ms) and the turbine by its parameters, so a changed input gives a new figure.
MAX_IMAGE_WIDTH = 1460  # px, the widest image Streamlit shows without resizing
CACHE_HASHES = {pd.DataFrame: lambda data: int(pd.util.hash_pandas_object(data).sum()),
                turbines.Turbine: dataclasses.astuple}


@st.cache_data(show_spinner=False, max_entries=500, hash_funcs=CACHE_HASHES)
def figure_png(name, *args, **kwargs):
    """The figure plots.<name>(*args, **kwargs) as PNG bytes."""
    fig = getattr(plots, name)(*args, output_file=None, **kwargs)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    # Streamlit shrinks images wider than this on every rerun; do it once here instead
    image = Image.open(buffer)
    if image.width > MAX_IMAGE_WIDTH:
        image = image.resize((MAX_IMAGE_WIDTH, round(image.height * MAX_IMAGE_WIDTH / image.width)), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def show(name, *args, **kwargs):
    """Show a figure from metocean_re.plots, e.g. show("plot_thrust", df, turbine)."""
    st.image(figure_png(name, *args, **kwargs), width="stretch")


@st.cache_data(show_spinner=False, max_entries=100, hash_funcs=CACHE_HASHES)
def energy_losses(data, turbine, **loss_options):
    return stats.annual_energy_losses(data, turbine, **loss_options)


@st.cache_data(show_spinner=False, max_entries=100, hash_funcs=CACHE_HASHES)
def mean_hub_height_wind(data, turbine):
    return stats.hub_height_wind_speed(data, turbine).mean()


# Columns of an uploaded file, with units (NORA3 names, as written by metocean-api)
FILE_COLUMNS = pd.DataFrame(
    [
        ("time", "", "Required", "First column. ISO 8601 (2021-07-27 07:00) or dd.mm.yyyy hh:mm"),
        ("wind_speed_{z}m", "m/s", "Required", "z is the height in m, e.g. wind_speed_100m"),
        ("wind_direction_{z}m", "deg", "Required", "Direction the wind comes from"),
        ("air_temperature_{z}m", "K", "Required", ""),
        ("relative_humidity_{z}m", "0-1", "Required", "As a fraction, not in percent"),
        ("density_{z}m", "kg/m3", "Required", ""),
        ("tke_{z}m", "m2/s2", "Required", "Turbulent kinetic energy"),
        ("sea_surface_temperature", "K", "Required", ""),
        ("hs, tp", "m, s", "Optional", "Significant wave height and peak period. Without them the wave-dependent "
                                       "losses are left out"),
    ],
    columns=["Column", "Unit", "", "Note"],
)
EXAMPLE_COLUMNS = [f"{var}_{z}m" for var in ["wind_speed", "wind_direction"] for z in (10, 100, 250)] + [
    f"{var}_{z}m" for var in ["air_temperature", "relative_humidity", "density", "tke"] for z in (50, 100)] + [
    "sea_surface_temperature", "hs", "tp"]


def show_file_format():
    """What an uploaded file must look like, with a small example file to start from."""
    st.subheader("Upload your own data")
    st.markdown("A CSV file with one row per time step (e.g. hourly) and the columns below. "
                "The columns with a height `{z}` are needed at **two heights or more**, so they can be "
                "found at hub height and over the rotor; heights around the rotor give the best results. "
                "Lines starting with `#` are skipped, so a description can be put at the top.")
    st.dataframe(FILE_COLUMNS, hide_index=True, width="stretch")
    example = load_data(None).loc["2020-01", EXAMPLE_COLUMNS]
    st.download_button(
        "Example file (CSV)",
        f"# NORA3 hindcast (MET Norway), {SITE['name']}, January 2020, only the columns the app needs\n"
        + example.to_csv(),
        file_name="example_upload.csv", mime="text/csv", icon=":material/download:", on_click="ignore",
        help=f"One month from {SITE['name']}, to see the format or to fill in your own data.")


# --- Sidebar: data, turbine and loss settings ------------------------------------

st.sidebar.header("Data")
source = st.sidebar.radio("Source", [f"NORA3, {SITE['name']}", "Upload file", "NORA3 point (metocean-api)"])

if source == "Upload file":
    uploaded = st.sidebar.file_uploader("Time series (CSV)", type=["csv"])
    if not uploaded:
        show_file_format()
        st.stop()
    try:
        df = load_data(uploaded)
    except ValueError as error:
        st.error(f"Could not read the file: {error}")
        show_file_format()
        st.stop()
elif source == "NORA3 point (metocean-api)":
    import folium
    from streamlit_folium import st_folium

    # Clicking the map fills in latitude and longitude; they can still be typed in
    st.session_state.setdefault("lat", SITE["lat"])
    st.session_state.setdefault("lon", SITE["lon"])
    with st.expander("Choose a point on the map", expanded="nora3_request" not in st.session_state):
        point_map = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=5)
        folium.Marker([st.session_state["lat"], st.session_state["lon"]], tooltip="Chosen point").add_to(point_map)
        clicked = st_folium(point_map, height=420, use_container_width=True,
                            returned_objects=["last_clicked"]).get("last_clicked")
    # st_folium keeps returning the last click, so only use a new one
    if clicked and clicked != st.session_state.get("map_click"):
        st.session_state["map_click"] = clicked
        st.session_state["lat"] = round(min(max(clicked["lat"], 50.0), 80.0), 2)
        st.session_state["lon"] = round(min(max(clicked["lng"], -20.0), 40.0), 2)
        st.rerun()

    lat = st.sidebar.number_input("Latitude", 50.0, 80.0, step=0.1, key="lat")
    lon = st.sidebar.number_input("Longitude", -20.0, 40.0, step=0.1, key="lon")
    start = st.sidebar.date_input("From", pd.Timestamp("2020-01-01"), format="YYYY-MM-DD")
    end = st.sidebar.date_input("To", pd.Timestamp("2020-12-31"), format="YYYY-MM-DD")
    waves = st.sidebar.checkbox("Include waves", value=True)
    if end < start:
        st.sidebar.error("'To' must be after 'From'.")
        st.stop()
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    st.sidebar.caption(
        f"Rough download time: {max(download_seconds(months, waves) / 60, 1):.0f} min. "
        "A point already downloaded takes about 1 min (metocean-api still looks up the grid point), "
        "and is instant later in the same session."
    )
    # Only download when the button is pressed, not on every change of the inputs
    if st.sidebar.button("Download"):
        st.session_state["nora3_request"] = (lon, lat, start, end, waves)
    request = st.session_state.get("nora3_request")
    if request is None:
        st.info("Click on the map or type a point in the sidebar, choose a period, then press Download.")
        st.stop()
    if request != (lon, lat, start, end, waves):
        st.sidebar.warning("Settings changed: press Download to get data for them.")
    # Downloaded data are kept for the session, so moving a slider does not download again
    downloaded = st.session_state.setdefault("nora3_data", {})
    if request not in downloaded:
        bar = st.progress(0.0, "Connecting to MET Norway ...")
        try:
            downloaded[request] = load_nora3(*request, progress=bar.progress)
        except Exception as error:
            st.error(f"Download from MET Norway failed: {error}. Try again, or try without waves.")
            st.stop()
        bar.empty()
    df = downloaded[request]
else:
    df = load_data(None)

st.sidebar.caption(
    f"{source}: {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}, {len(df)} time steps"
)
heights = {var: [c for c in df.columns if re.fullmatch(rf"{var}_\d+m", c)] for var in PROFILE_VARIABLES}
missing = [f"{var}_{{z}}m (found {', '.join(found) or 'none'})" for var, found in heights.items() if len(found) < 2]
missing += [] if "sea_surface_temperature" in df.columns else ["sea_surface_temperature"]
if missing:
    st.error("The data is missing columns. Need these at two heights or more, e.g. density_50m and "
             f"density_100m: {', '.join(missing)}")
    if source == "Upload file":
        show_file_format()
    st.stop()
has_waves = {"hs", "tp"} <= set(df.columns)

st.sidebar.header("Turbine")
choice = st.sidebar.selectbox("Turbine", turbines.names() + ["Custom"], index=turbines.names().index("IEA-15MW"))
if choice == "Custom":
    turbine = turbines.Turbine(
        name=st.sidebar.text_input("Name", "My turbine"),
        rated_power=st.sidebar.number_input("Rated power [MW]", 0.5, 30.0, 12.0),
        cut_in=st.sidebar.number_input("Cut-in [m/s]", 0.0, 10.0, 3.0),
        rated_speed=st.sidebar.number_input("Rated speed [m/s]", 5.0, 20.0, 11.0),
        cut_out=st.sidebar.number_input("Cut-out [m/s]", 15.0, 40.0, 25.0),
        hub_height=st.sidebar.number_input("Hub height [m]", 20.0, 300.0, 140.0),
        rotor_diameter=st.sidebar.number_input("Rotor diameter [m]", 20.0, 350.0, 220.0),
    )
    if not turbine.cut_in < turbine.rated_speed < turbine.cut_out:
        st.sidebar.error("Need cut-in < rated speed < cut-out.")
        st.stop()
else:
    turbine = turbines.get(choice)

st.sidebar.header("Losses")
maintenance = st.sidebar.radio("Maintenance", ["weather", "fixed"], horizontal=True,
                               index=0 if has_waves else 1, disabled=not has_waves)
if maintenance == "weather":
    maintenance_options = dict(
        hs_limit=st.sidebar.slider("Wave height limit for access, Hs [m]", 1.0, 4.0, 2.0, 0.25,
                                   help="Own assumption (no source). The loss depends strongly on this limit."),
        failures_per_year=st.sidebar.slider("Failures per year", 1.0, 15.0, 8.3, 0.1,
                                            help="8.3 per turbine per year: Carroll et al. (2016), Wind Energy 19."),
        repair_hours=st.sidebar.slider("Repair time [hours]", 2, 48, 12,
                                       help="12 h: mean repair time weighted by failure rate, Carroll et al. (2016). "
                                            "Excludes travel and waiting for access."),
    )
else:
    maintenance_options = dict(downtime_days=st.sidebar.slider("Maintenance [days/year]", 0, 60, 14,
                                                                 help="Own assumption, agreed with supervisor (MET)."))
loss_options = dict(
    maintenance=maintenance,
    **maintenance_options,
    electrical=st.sidebar.slider("Electrical loss [%]", 0.0, 10.0, 2.0, 0.5,
                                 help="Own assumption (no source). Typical values are 1-3 %.") / 100,
    restart_speed=st.sidebar.slider("Restart after storm stop [m/s]", 15.0, 25.0, 20.0, 0.5,
                                    help="Own assumption (no source). Typical value, not from a specific turbine."),
    tilt_angle=st.sidebar.slider("Constant tilt [deg]", 0.0, 15.0, 5.0, 0.5,
                                 help="Own assumption (no source). Scenario choice."),
    wave_response=st.sidebar.slider("Wave response (0 = off)", 0.0, 1.0, 1.0, 0.1,
                                    help="Own assumption (no source). 1.0 is a deliberate upper limit.") if has_waves else 0.0,
)
if not has_waves:
    st.sidebar.caption("No hs/tp columns in the data, so the wave-dependent losses are left out.")
st.sidebar.caption("Hover over ? for where a default value comes from. "
                   f"All sources and assumptions: [docs/references.md]({REFERENCES_URL})")

st.sidebar.header("Download")
if source == "NORA3 point (metocean-api)":
    lon, lat, start, end, _ = request
    data_name, data_note = f"NORA3_{lat:.2f}N_{lon:.2f}E_{start:%Y%m%d}_{end:%Y%m%d}", (
        f"NORA3 hindcast (MET Norway), nearest grid point to {lat:.2f} N {lon:.2f} E, downloaded with metocean-api")
elif source == "Upload file":
    data_name, data_note = Path(uploaded.name).stem, f"Uploaded file {uploaded.name}"
else:
    data_name, data_note = EXAMPLE_FILE.stem, f"NORA3 hindcast (MET Norway), {SITE['name']}"
st.sidebar.download_button(
    "Data (CSV)", lambda: f"# {data_note}\n" + df.to_csv(), file_name=f"{data_name}.csv", mime="text/csv",
    icon=":material/download:", on_click="ignore", width="stretch",
    help="The time series used in the figures. Can be uploaded again with 'Upload file'.")


def tables_zip():
    """All tables for the chosen turbine and losses as CSV files in one ZIP file (made on click)."""
    all_turbines = turbines.names() + ([turbine] if choice == "Custom" else [])
    files = {
        "energy_production.csv": tables.table_energy_production(df, all_turbines, output_file=None, **loss_options),
        "annual_energy_losses.csv": tables.table_annual_energy_losses(df, turbine, output_file=None, **loss_options),
        "losses_by_stability.csv": tables.table_losses_by_stability(df, turbine, output_file=None),
        "stability_by_month.csv": tables.table_stability_by_month(df, output_file=None),
        "turbines.csv": tables.table_turbines(output_file=None),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, table in files.items():
            archive.writestr(name, table.to_csv())
    return buffer.getvalue()


st.sidebar.download_button(
    "Tables (ZIP)", tables_zip, file_name=f"wind_energy_tables_{data_name}.zip", mime="application/zip",
    icon=":material/download:", on_click="ignore", width="stretch",
    help="Energy production for all turbines, the losses and the stability classes as CSV files, "
         "with the turbine and losses chosen above.")

# --- Figures ---------------------------------------------------------------------

title_area.title(f"Wind energy: {turbine.name}")

# Key numbers for the chosen turbine, data and losses, above the tabs
losses = energy_losses(df, turbine, **loss_options)
gross_MWh, net_MWh = losses.attrs["gross_MWh"], losses.attrs["net_MWh"]
net_column, cf_column, loss_column, wind_column = st.columns(4)
net_column.metric("Net energy production", f"{net_MWh / 1000:.1f} GWh/year", border=True,
                  help="Mean over the whole period, after all the losses in the Losses tab.")
cf_column.metric("Net capacity factor", f"{net_MWh / (turbine.rated_power * stats.HOURS_PER_YEAR):.0%}",
                 border=True, help="Net production divided by what the turbine would make at rated power all the time.")
loss_column.metric("Total losses", f"{1 - net_MWh / gross_MWh:.1%}", border=True,
                   help=f"Of the gross production of {gross_MWh / 1000:.1f} GWh/year. "
                        "The single losses are in the Losses tab.")
wind_column.metric("Mean wind at hub height", f"{mean_hub_height_wind(df, turbine):.1f} m/s",
                   border=True, help=f"At {turbine.hub_height:.0f} m, from the power law between the two "
                                     "nearest heights in the data.")
turbine_tab, wind_tab, stability_tab, production_tab, loss_tab, load_tab = st.tabs(
    ["Turbines", "Wind", "Stability", "Production", "Losses", "Loads"])

with turbine_tab:
    all_turbines = turbines.names() + ([turbine] if choice == "Custom" else [])
    show("plot_power_curves", all_turbines)
    show("plot_turbine_comparison", df, all_turbines, **loss_options)

with wind_tab:
    show("plot_wind_profile", df, turbine)
    show("plot_wind_shear_explained", df, turbine)
    show("plot_wind_and_energy_distribution", df, turbine)
    show("plot_turbulence_intensity", df, turbine)
    show("plot_turbulence_power_curve", turbine)

with stability_tab:
    start = st.date_input("Stability time series from", df.index[0], min_value=df.index[0],
                          max_value=df.index[-1], key="stability_start", format="YYYY-MM-DD")
    show("plot_stability_timeseries", df, pd.Timestamp(start), pd.Timestamp(start) + pd.Timedelta(days=31))
    show("plot_stability_by_month", df)
    show("plot_stability_effects", df, turbine)

with production_tab:
    start = st.date_input("Time series from", max(df.index[0], df.index[-1].replace(month=1, day=1)),
                          min_value=df.index[0], max_value=df.index[-1], format="YYYY-MM-DD")
    days = st.slider("Number of days", 1, 90, 31)
    show("plot_power_output", df, turbine, pd.Timestamp(start), pd.Timestamp(start) + pd.Timedelta(days=days))
    show("plot_monthly_energy", df, turbine)
    show("plot_energy_per_year", df, turbine)

with loss_tab:
    show("plot_energy_losses", df, turbine, **loss_options)
    show("plot_losses_by_stability", df, turbine)
    if has_waves:
        if maintenance == "weather":
            show("plot_maintenance_downtime", df, turbine, **maintenance_options)
        show("plot_tilt_loss_comparison", df, turbine, tilt_angle=loss_options["tilt_angle"],
             wave_response=loss_options["wave_response"])

with load_tab:
    st.caption("Simple estimates for comparing conditions, not for design.")
    show("plot_thrust", df, turbine)
    show("plot_loads_by_stability", df, turbine)
