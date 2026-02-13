# ============================================================
# 📡 Endereços dos Sites RJ — Versão PRO Inteligente
# ============================================================
 
import streamlit as st
import pandas as pd
import unicodedata
import time
import requests
import numpy as np
import math
import re
import os
import difflib
from typing import List, Tuple
 
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")
 
# ------------------------------------------------------------
# NORMALIZAÇÃO INTELIGENTE
# ------------------------------------------------------------
def normalizar_sigla(sigla: str) -> str:
    if not isinstance(sigla, str):
        return ""
    s = sigla.strip().upper()
    s = s.replace(" ", "").replace("-", "")
    if s.startswith("RJ"):
        s = s[2:]
    return s
 
 
def similaridade(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()
 
 
# ------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ------------------------------------------------------------
def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
 
 
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c
 
 
@st.cache_data(show_spinner=False)
def carregar_dados():
    df = pd.read_excel("enderecos.xlsx", sheet_name="enderecos", engine="openpyxl")
    df.columns = df.columns.str.strip().str.lower()
 
    df = df.rename(columns={
        "sigla_da_torre": "sigla",
        "nome_da_torre": "nome",
        "endereço": "endereco",
        "latitude": "lat",
        "longitude": "lon",
    })
 
    for col in ["sigla", "nome", "endereco"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
 
    for col in ["lat", "lon"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", pd.NA)
                .astype(float)
            )
 
    return df
 
 
df = carregar_dados()
 
st.title("📡 Endereços dos Sites RJ")
 
# ============================================================
# 🔍 BUSCA INTELIGENTE NÍVEL GOOGLE
# ============================================================
 
st.markdown("---")
st.subheader("🔍 Buscar por SIGLA")
 
lista_siglas = sorted(
    df["sigla"].dropna().astype(str).str.upper().unique().tolist()
)
 
busca = st.text_input(
    "Digite a sigla (aceita RJDJU, rj-dju, erro pequeno etc...)"
)
 
sigla_final = None
 
if busca:
    busca_norm = normalizar_sigla(busca)
 
    # Calcula similaridade
    scores = []
    for s in lista_siglas:
        s_norm = normalizar_sigla(s)
        score = similaridade(busca_norm, s_norm)
        scores.append((s, score))
 
    # Ordena por similaridade
    scores.sort(key=lambda x: x[1], reverse=True)
 
    melhores = [s[0] for s in scores if s[1] > 0.5][:5]
 
    if melhores:
        st.markdown("### 🔎 Sugestões:")
        for sug in melhores:
            if st.button(f"👉 {sug}", key=sug):
                sigla_final = sug
    else:
        st.warning("Nenhuma sugestão encontrada.")
 
# Se digitou exato
if busca and not sigla_final:
    busca_norm = normalizar_sigla(busca)
    for s in lista_siglas:
        if normalizar_sigla(s) == busca_norm:
            sigla_final = s
            break
 
# ============================================================
# RESULTADO
# ============================================================
 
if sigla_final:
    df_f = df[df["sigla"].astype(str).str.upper() == sigla_final]
 
    if df_f.empty:
        st.warning("⚠️ Nenhum site encontrado.")
    else:
        st.success(f"🔎 Site encontrado: {sigla_final}")
 
        st.dataframe(
            df_f[["sigla", "nome", "endereco", "lat", "lon"]],
            use_container_width=True
        )
 
        for _, row in df_f.iterrows():
            if pd.notna(row.get("lat")) and pd.notna(row.get("lon")):
                url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
                st.link_button("🗺️ Ver no Google Maps", url, type="primary")
 
st.caption("❤️ Desenvolvido por Raphael Robles - Stay hungry, stay foolish ! 🚀")
 






































