import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from helpers import load_data, status_color, build_priority, CITY_COORDS, POLLUTANTS
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="AIR-SHIELD | Air quality intelligence", page_icon="🌫️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding-top: 1.5rem; max-width: 1440px; }
h1,h2,h3 { font-family:'Manrope',sans-serif; letter-spacing:-.035em; }
[data-testid="stMetric"] { background:#101d29; border:1px solid #233442; padding:16px 18px; border-radius:14px; }
[data-testid="stMetricLabel"] p { color:#99aebb; }
.eyebrow { color:#61d7c2; text-transform:uppercase; letter-spacing:.16em; font-size:11px; font-weight:700; }
.note { background:#101d29; border:1px solid #233442; border-radius:12px; padding:14px 16px; color:#c0cdd5; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="eyebrow">AIR-SHIELD · INDIA</div>', unsafe_allow_html=True)
st.sidebar.title("Air intelligence")
page = st.sidebar.radio("Navigate", ["Overview", "Hotspots", "Forecast", "Pollution Drivers", "Intervention Priority"], label_visibility="collapsed")
st.sidebar.caption("Historical air-quality analysis · Daily city data")

data_path = ROOT / "data" / "processed" / "cleaned_air_quality.csv"
try:
    df = load_data(data_path)
except Exception as exc:
    st.error(f"Could not load the cleaned dataset: {exc}")
    st.stop()

cities = sorted(df["City"].dropna().unique())
with st.sidebar:
    selected_city = st.selectbox("City", ["All cities"] + cities)
    date_min, date_max = df["Date"].min().date(), df["Date"].max().date()
    date_range = st.date_input("Date range", (date_min, date_max), min_value=date_min, max_value=date_max)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        start = end = date_range

view = df[(df.Date.dt.date >= start) & (df.Date.dt.date <= end)].copy()
if selected_city != "All cities":
    view = view[view.City == selected_city]
if view.empty:
    st.warning("No observations match these filters.")
    st.stop()

latest = view.sort_values("Date").groupby("City", as_index=False).tail(1)
latest_aqi = latest.AQI.median()
city_count = view.City.nunique()
poor_share = (view.AQI >= 201).mean() * 100
pm25 = view["PM2.5"].mean()

st.markdown('<div class="eyebrow">DECISION SUPPORT · HISTORICAL SIGNALS</div>', unsafe_allow_html=True)
st.title(page)
st.caption(f"{start:%d %b %Y} — {end:%d %b %Y}  ·  {city_count} {'city' if city_count == 1 else 'cities'} in view")

if page == "Overview":
    cols = st.columns(4)
    cols[0].metric("Median latest AQI", f"{latest_aqi:.0f}", help="Median of each city's latest in-range observation")
    cols[1].metric("Mean PM₂.₅", f"{pm25:.1f} µg/m³")
    cols[2].metric("Poor or worse days", f"{poor_share:.1f}%", help="Share of daily observations with AQI ≥ 201")
    cols[3].metric("Cities covered", f"{city_count}")
    left, right = st.columns([1.55, 1])
    trend = view.groupby("Date", as_index=False).agg(AQI=("AQI", "mean"), PM25=("PM2.5", "mean"))
    with left:
        st.subheader("Daily air-quality trend")
        fig = px.line(trend, x="Date", y="AQI", color_discrete_sequence=["#61d7c2"], template="plotly_dark")
        fig.update_layout(margin=dict(l=0,r=0,t=8,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Mean AQI")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Latest city status")
        status = latest[["City", "Date", "AQI", "AQI_Bucket"]].sort_values("AQI", ascending=False)
        st.dataframe(status, use_container_width=True, hide_index=True, height=370)
    st.markdown('<div class="note">This view summarizes the cleaned historical dataset. It does not represent live sensor readings or official real-time alerts.</div>', unsafe_allow_html=True)

elif page == "Hotspots":
    st.subheader("Historical hotspot ranking")
    hotspot_file = ROOT / "data" / "processed" / "city_hotspot_results.csv"
    pollution_file = ROOT / "data" / "processed" / "pollution_hotspots.csv"
    if hotspot_file.exists():
        import pandas as pd
        raw_hotspots = pd.read_csv(hotspot_file)
        raw_hotspots["City"] = raw_hotspots["City"].astype(str)
        raw_hotspots["AQI"] = pd.to_numeric(raw_hotspots["AQI"], errors="coerce")
        rank = raw_hotspots[raw_hotspots.City.isin(view.City.unique())].copy()
        rank = rank.rename(columns={"AQI": "mean_aqi", "Risk_Level": "risk_level"})
        rank["mean_pm25"] = rank.City.map(view.groupby("City")["PM2.5"].mean())
        rank["poor_days"] = rank.City.map(view.groupby("City")["AQI"].apply(lambda x: (x >= 201).mean() * 100))
        rank["observations"] = rank.City.map(view.groupby("City")["AQI"].count())
        st.caption("Rankings and risk labels come from Person 2's city_hotspot_results.csv. Pollutant context follows the selected filters.")
    else:
        rank = view.groupby("City", as_index=False).agg(mean_aqi=("AQI", "mean"), mean_pm25=("PM2.5", "mean"), poor_days=("AQI", lambda x: (x >= 201).mean() * 100), observations=("AQI", "count"))
        st.caption("Person 2's hotspot file is missing; showing a descriptive ranking from the cleaned dataset instead.")
    rank = rank.sort_values("mean_aqi", ascending=False)
    hover = ["risk_level"] if "risk_level" in rank.columns else None
    fig = px.bar(rank.head(15).sort_values("mean_aqi"), x="mean_aqi", y="City", orientation="h", color="mean_aqi", color_continuous_scale=["#5dd6c0", "#f0b45c", "#f06b62"], template="plotly_dark", hover_data=hover)
    fig.update_layout(margin=dict(l=0,r=0,t=8,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False, xaxis_title="AQI from Person 2 hotspot output", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    map_data = rank[rank.City.isin(CITY_COORDS)].copy()
    map_data["lat"] = map_data.City.map(lambda c: CITY_COORDS[c][0]); map_data["lon"] = map_data.City.map(lambda c: CITY_COORDS[c][1])
    if len(map_data):
        st.subheader("City-level pattern")
        m = px.scatter_mapbox(map_data, lat="lat", lon="lon", size="mean_aqi", color="mean_aqi", hover_name="City", hover_data={"mean_aqi":":.1f", "mean_pm25":":.1f", "lat":False,"lon":False}, zoom=3.2, center={"lat":22.8,"lon":79.2}, mapbox_style="carto-darkmatter", color_continuous_scale=["#5dd6c0","#f0b45c","#f06b62"], template="plotly_dark")
        m.update_layout(height=480, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(m, use_container_width=True)
    if pollution_file.exists():
        supplied = pd.read_csv(pollution_file)
        st.markdown("**Person 2 supplied hotspot list**")
        st.dataframe(supplied, use_container_width=True, hide_index=True)
    st.dataframe(rank.rename(columns={"mean_aqi":"Mean AQI","mean_pm25":"Mean PM₂.₅","poor_days":"Poor+ days (%)","observations":"Days","risk_level":"Person 2 risk label"}), use_container_width=True, hide_index=True)

elif page == "Forecast":
    st.subheader("City forecast")
    city = selected_city if selected_city != "All cities" else st.selectbox("Choose a city", cities, key="forecast_city")
    forecast_files = list((ROOT / "results").glob("*forecast*.csv")) if (ROOT / "results").exists() else []
    if not forecast_files:
        st.info("No saved Person 3 forecast file was included in the ZIP. The chart below shows observed history only; it does not invent a forecast.")
    hist = df[df.City == city].sort_values("Date").tail(365)
    fig = px.line(hist, x="Date", y="AQI", color_discrete_sequence=["#61d7c2"], template="plotly_dark")
    fig.update_layout(margin=dict(l=0,r=0,t=8,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Observed AQI")
    st.plotly_chart(fig, use_container_width=True)
    if forecast_files:
        st.caption("Forecast files found: " + ", ".join(p.name for p in forecast_files) + ". Map their columns in the integration helper to display model predictions.")

elif page == "Pollution Drivers":
    st.subheader("Pollutant patterns")
    st.caption("Associations in the supplied data are descriptive and do not establish causation.")
    pollutant_cols = [c for c in POLLUTANTS if c in view.columns]
    c1, c2 = st.columns(2)
    with c1:
        means = view[pollutant_cols].mean().sort_values(ascending=False).rename_axis("Pollutant").reset_index(name="Mean concentration")
        fig = px.bar(means, x="Pollutant", y="Mean concentration", color="Mean concentration", color_continuous_scale=["#5dd6c0","#f0b45c","#f06b62"], template="plotly_dark")
        fig.update_layout(margin=dict(l=0,r=0,t=8,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        corr = view[pollutant_cols + (["AQI"] if "AQI" in view.columns else [])].corr()
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlBu_r", zmin=-1, zmax=1, aspect="auto", template="plotly_dark")
        fig.update_layout(margin=dict(l=0,r=0,t=8,b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    if "Season" in view.columns:
        seasonal = view.groupby("Season", as_index=False)["PM2.5"].mean()
        fig = px.bar(seasonal, x="Season", y="PM2.5", color_discrete_sequence=["#61d7c2"], template="plotly_dark", title="Mean PM₂.₅ by season")
        fig.update_layout(margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.subheader("Intervention priority ranking")
    st.markdown('<div class="note"><b>Documented demo score (0–100):</b> 40% severity + 30% persistence + 20% recent spike + 10% population exposure. Severity is normalized mean AQI; persistence is the share of days with AQI ≥ 201; recent spike compares the latest 30-day mean AQI with the previous 90-day mean, capped at a 100% increase. Population data was not included, so exposure is held at a neutral 50/100 for all cities and does not affect their relative order. It must be replaced with a real population layer before operational use.</div>', unsafe_allow_html=True)
    priority = build_priority(view)
    st.dataframe(priority, use_container_width=True, hide_index=True)
    st.download_button("Download ranking CSV", priority.to_csv(index=False).encode("utf-8"), "air_shield_intervention_priority.csv", "text/csv")
