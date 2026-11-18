from pathlib import Path
import pandas as pd
import streamlit as st

POLLUTANTS = ["PM2.5", "PM10", "NO", "NO2", "NOx", "CO", "SO2", "O3"]
CITY_COORDS = {
    "Ahmedabad": (23.0225,72.5714), "Aizawl": (23.7271,92.7176), "Amaravati": (16.5062,80.6480),
    "Amritsar": (31.6340,74.8723), "Bengaluru": (12.9716,77.5946), "Bhopal": (23.2599,77.4126),
    "Brajrajnagar": (21.8167,83.9167), "Chandigarh": (30.7333,76.7794), "Chennai": (13.0827,80.2707),
    "Delhi": (28.6139,77.2090), "Ernakulam": (9.9816,76.2999), "Gurugram": (28.4595,77.0266),
    "Guwahati": (26.1445,91.7362), "Hyderabad": (17.3850,78.4867), "Jaipur": (26.9124,75.7873),
    "Jorapokhar": (23.7167,86.4167), "Kochi": (9.9312,76.2673), "Kolkata": (22.5726,88.3639),
    "Lucknow": (26.8467,80.9462), "Mumbai": (19.0760,72.8777), "Patna": (25.5941,85.1376),
    "Shillong": (25.5788,91.8933), "Talcher": (20.9517,85.2333), "Thiruvananthapuram": (8.5241,76.9366),
    "Visakhapatnam": (17.6868,83.2185),
}

@st.cache_data(show_spinner="Loading cleaned air-quality data…")
def load_data(path):
    df = pd.read_csv(path, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in POLLUTANTS + ["AQI"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["City", "Date", "AQI"])

def status_color(aqi):
    return "#f06b62" if aqi >= 201 else "#f0b45c" if aqi >= 101 else "#61d7c2"

def build_priority(df):
    rows = []
    for city, group in df.groupby("City"):
        group = group.sort_values("Date")
        mean_aqi = group["AQI"].mean()
        severity = min(100, max(0, mean_aqi / 500 * 100))
        persistence = (group["AQI"] >= 201).mean() * 100
        recent = group[group.Date >= group.Date.max() - pd.Timedelta(days=29)]["AQI"].mean()
        previous = group[(group.Date < group.Date.max() - pd.Timedelta(days=29)) & (group.Date >= group.Date.max() - pd.Timedelta(days=119))]["AQI"].mean()
        spike = 50 if pd.isna(previous) or previous <= 0 else min(100, max(0, ((recent - previous) / previous) * 100))
        exposure = 50  # Neutral score; population was not supplied in the project ZIP.
        score = .40 * severity + .30 * persistence + .20 * spike + .10 * exposure
        rows.append({"City": city, "Priority score": round(score, 1), "Mean AQI": round(mean_aqi, 1), "Severe-day persistence (%)": round(persistence, 1), "Recent spike score": round(spike, 1), "Population exposure": "Unavailable (neutral)", "Observations": len(group)})
    return pd.DataFrame(rows).sort_values(["Priority score", "Mean AQI"], ascending=False).reset_index(drop=True)
