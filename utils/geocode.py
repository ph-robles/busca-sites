import time
import requests
import streamlit as st

GEOAPIFY_KEY = (st.secrets.get("GEOAPIFY_KEY", "") or "").strip()

@st.cache_data
def geocode_address(addr: str):
    if GEOAPIFY_KEY:
        r = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={"text": addr, "apiKey": GEOAPIFY_KEY, "limit": 1}
        )
        j = r.json()
        if j.get("features"):
            p = j["features"][0]["properties"]
            return p["lat"], p["lon"], p.get("formatted")

    # Fallback — Nominatim
    time.sleep(1)
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": addr, "format": "json", "limit": 1, "countrycodes": "br"},
        headers={"User-Agent": "site-app"}
    )
    j = r.json()
    if j:
        return float(j[0]["lat"]), float(j[0]["lon"]), j[0]["display_name"]

    return None