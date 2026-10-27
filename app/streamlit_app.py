"""
Streamlit app: the figures from metocean_re.plots in the browser.

Run with (from the project root):
    pip install -e .[app]
    streamlit run app/streamlit_app.py

The app only calls functions from the metocean_re package; all
calculations and figures live there. The only code here is reading the
data: the test dataset, an uploaded file or a NORA3 point from metocean-api.
"""

from contextlib import contextmanager
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

matplotlib.use("Agg")  # draw to images only; a server has no screen

from metocean_re import plots, stats
from metocean_re.stats import turbines

st.set_page_config(page_title="Wind energy", layout="wide")
title_area = st.empty()  # filled in when the turbine is known, so the title stays above the map

# The test dataset (see examples/build_dataset.py)
EXAMPLE_FILE = Path(__file__).resolve().parent.parent / "tests" / "data" / "NORA3_utsira_nord_2020_2022.csv"
SITE = {"name": "Utsira Nord", "lat": 59.27, "lon": 4.54}

# Columns the calculations need (see metocean_re/stats/aux_funcs.py for all columns)
REQUIRED_COLUMNS = ["wind_speed_100m", "wind_direction_100m", "air_temperature_50m", "relative_humidity_50m",
                    "density_50m", "tke_50m", "sea_surface_temperature"]
WAVE_COLUMNS = ["hs", "tp", "hs_sea", "tp_sea", "hs_swell", "tp_swell"]
ATM3HR_PREFIXES = ("air_temperature_", "relative_humidity_", "density_", "tke_")

# All sources and assumptions behind the calculations
REFERENCES_URL = "https://github.com/hakjen/metocean-re/blob/docs/docs/references.md"


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


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


# --- Sidebar: data, turbine and loss settings ------------------------------------

st.sidebar.header("Data")
source = st.sidebar.radio("Source", [f"NORA3, {SITE['name']}", "Upload file", "NORA3 point (metocean-api)"])

if source == "Upload file":
    uploaded = st.sidebar.file_uploader("Time series (NORA3 CSV, as made by examples/build_dataset.py)", type=["csv"])
    if not uploaded:
        st.info("Upload a file in the sidebar.")
        st.stop()
    try:
        df = load_data(uploaded)
    except ValueError as error:
        st.error(f"Could not read the file: {error}")
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
missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
if missing:
    st.error(f"The data is missing these columns: {', '.join(missing)}")
    st.stop()
# Wind at hub height and the shear come from the power law between two heights
wind_heights = stats.measured_heights(df)
if len(wind_heights) < 2:
    st.error("Need wind speed at two heights or more (e.g. wind_speed_10m and wind_speed_100m) to find the wind "
             f"at hub height and the wind shear. Found only: {', '.join(wind_heights.values())}")
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

# --- Figures ---------------------------------------------------------------------

title_area.title(f"Wind energy: {turbine.name}")
turbine_tab, wind_tab, stability_tab, production_tab, loss_tab, load_tab = st.tabs(
    ["Turbines", "Wind", "Stability", "Production", "Losses", "Loads"])

with turbine_tab:
    all_turbines = turbines.names() + ([turbine] if choice == "Custom" else [])
    show(plots.plot_power_curves(all_turbines, output_file=None))
    show(plots.plot_turbine_comparison(df, all_turbines, output_file=None, **loss_options))

with wind_tab:
    show(plots.plot_wind_profile(df, turbine, output_file=None))
    show(plots.plot_wind_shear_explained(df, turbine, output_file=None))
    show(plots.plot_wind_and_energy_distribution(df, turbine, output_file=None))
    show(plots.plot_turbulence_intensity(df, turbine, output_file=None))
    show(plots.plot_turbulence_power_curve(turbine, output_file=None))

with stability_tab:
    start = st.date_input("Stability time series from", df.index[0], min_value=df.index[0],
                          max_value=df.index[-1], key="stability_start", format="YYYY-MM-DD")
    show(plots.plot_stability_timeseries(df, pd.Timestamp(start), pd.Timestamp(start) + pd.Timedelta(days=31),
                                         output_file=None))
    show(plots.plot_stability_by_month(df, output_file=None))
    show(plots.plot_stability_effects(df, turbine, output_file=None))

with production_tab:
    start = st.date_input("Time series from", max(df.index[0], df.index[-1].replace(month=1, day=1)),
                          min_value=df.index[0], max_value=df.index[-1], format="YYYY-MM-DD")
    days = st.slider("Number of days", 1, 90, 31)
    show(plots.plot_power_output(df, turbine, pd.Timestamp(start), pd.Timestamp(start) + pd.Timedelta(days=days),
                                 output_file=None))
    show(plots.plot_monthly_energy(df, turbine, output_file=None))
    show(plots.plot_energy_per_year(df, turbine, output_file=None))

with loss_tab:
    show(plots.plot_energy_losses(df, turbine, output_file=None, **loss_options))
    show(plots.plot_losses_by_stability(df, turbine, output_file=None))
    if has_waves:
        if maintenance == "weather":
            show(plots.plot_maintenance_downtime(df, turbine, output_file=None, **maintenance_options))
        show(plots.plot_tilt_loss_comparison(df, turbine, tilt_angle=loss_options["tilt_angle"],
                                             wave_response=loss_options["wave_response"], output_file=None))

with load_tab:
    st.caption("Simple estimates for comparing conditions, not for design.")
    show(plots.plot_thrust(df, turbine, output_file=None))
    show(plots.plot_loads_by_stability(df, turbine, output_file=None))
