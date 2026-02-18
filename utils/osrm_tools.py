import requests
import streamlit as st

@st.cache_data
def osrm_table(origin_lat, origin_lon, destinos):
    coords = [(origin_lon, origin_lat)] + [(lon, lat) for lat, lon in destinos]
    coord_str = ";".join(f"{x},{y}" for x, y in coords)

    url = f"https://router.project-osrm.org/table/v1/driving/{coord_str}"
    r = requests.get(url, params={"annotations": "duration,distance"})
    data = r.json()

    durations = data["durations"][0][1:]
    distances = data["distances"][0][1:]

    out = []
    for d, m in zip(durations, distances):
        out.append({
            "duration_min": round(d / 60),
            "distance_km": round(m / 1000, 2),
        })
    return out
