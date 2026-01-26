

# ============================================================
# 📡 Endereços dos Sites RJ — OSM/OSRM Edition (100% gratuito)
# - Geocoding: Geoapify (opcional, com key) → fallback Nominatim (sem key)
# - Rotas/Matriz: OSRM (sem key) para distância/tempo por trajeto
# - Detecção de cidade aprimorada (regex + fallback no endereço)
# - Geocodificação robusta: normalização de entrada + duas tentativas no Nominatim
# - Sem mensagens/diagnóstico na UI
# - Corrige pd.NA em f-strings (sem usar `or` com pd.NA)
# - Mantém toda a lógica de SIGLA e Acessos OK
# ============================================================

import streamlit as st
import pandas as pd
import unicodedata
import time
import requests
import numpy as np
import math
import re
from typing import List, Tuple

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ------------------------------------------------------------
# Secrets (opcional): GEOAPIFY
# ------------------------------------------------------------
GEOAPIFY_KEY = (st.secrets.get("GEOAPIFY_KEY", "") or "").strip()

# ------------------------------------------------------------
# Helper: rerun compatível (Streamlit novo/antigo)
# ------------------------------------------------------------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------
def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def haversine_km(lat1, lon1, lat2, lon2):
    """Distância Haversine em km (vetorizado para lat2/lon2)."""
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

def fmt_na(x, dash="—"):
    """Substitui pd.NA/NaN/None por '—' evitando TypeError de truthiness com pd.NA."""
    try:
        return dash if (x is pd.NA or pd.isna(x)) else x
    except Exception:
        return dash if x is None else x

# ------------------------------------------------------------
# Parâmetros regionais (viés RJ para Nominatim)
# ------------------------------------------------------------
# viewbox para Nominatim (lon_min, lat_min, lon_max, lat_max)
RJ_VIEWBOX = (-43.8, -23.1, -43.0, -22.7)  # melhora match no RJ

# ------------------------------------------------------------
# Lista de municípios (RJ) + regex para melhor detecção
# ------------------------------------------------------------
MUNICIPIOS_RJ = [
    "Angra dos Reis", "Aperibé", "Araruama", "Areal", "Armação dos Búzios", "Arraial do Cabo",
    "Barra do Piraí", "Barra Mansa", "Belford Roxo", "Bom Jardim", "Bom Jesus do Itabapoana",
    "Cabo Frio", "Cachoeiras de Macacu", "Cambuci", "Campos dos Goytacazes", "Cantagalo",
    "Carapebus", "Cardoso Moreira", "Carmo", "Casimiro de Abreu", "Conceição de Macabu",
    "Cordeiro", "Duas Barras", "Duque de Caxias", "Engenheiro Paulo de Frontin", "Guapimirim",
    "Iguaba Grande", "Itaboraí", "Itaguaí", "Italva", "Itaocara", "Itaperuna", "Itatiaia",
    "Japeri", "Laje do Muriaé", "Macaé", "Macuco", "Magé", "Mangaratiba", "Maricá", "Mendes",
    "Mesquita", "Miguel Pereira", "Miracema", "Natividade", "Nilópolis", "Niterói",
    "Nova Friburgo", "Nova Iguaçu", "Paracambi", "Paraíba do Sul", "Parati", "Paty do Alferes",
    "Petrópolis", "Pinheiral", "Piraí", "Porciúncula", "Porto Real", "Quatis", "Queimados",
    "Quissamã", "Resende", "Rio Bonito", "Rio Claro", "Rio das Flores", "Rio das Ostras",
    "Rio de Janeiro", "Santa Maria Madalena", "Santo Antônio de Pádua", "São Fidélis",
    "São Francisco de Itabapoana", "São Gonçalo", "São João da Barra", "São João de Meriti",
    "São José de Ubá", "São José do Vale do Rio Preto", "São Pedro da Aldeia",
    "São Sebastião do Alto", "Sapucaia", "Saquarema", "Seropédica", "Silva Jardim",
    "Sumidouro", "Tanguá", "Teresópolis", "Trajano de Moraes", "Três Rios", "Valença",
    "Varre-Sai", "Vassouras", "Volta Redonda"
]
MUNI_IDX = {strip_accents(n).lower(): n for n in MUNICIPIOS_RJ}
_CITY_PATTERNS = {key: re.compile(rf"\b{re.escape(key)}\b") for key in MUNI_IDX.keys()}

def _match_city_base(texto: str) -> str | None:
    """Tenta casar município num texto (normalizado sem acentos e lower)."""
    if not isinstance(texto, str) or not texto.strip():
        return None
    base = strip_accents(texto).lower()
    ultimo = None
    for key, pat in _CITY_PATTERNS.items():
        if pat.search(base):
            ultimo = MUNI_IDX[key]
    return ultimo

def detectar_cidade(nome: str, endereco: str | None = None) -> str | None:
    """
    1) Tenta identificar o município no 'nome'
    2) Se não achou, tenta no 'endereco'
    """
    city = _match_city_base(nome)
    if city:
        return city
    if endereco:
        return _match_city_base(endereco)
    return None

# ------------------------------------------------------------
# Geocoding — normalização do endereço + Geoapify (opcional) + Nominatim (duas tentativas)
# ------------------------------------------------------------
def _normalize_address_for_br(addr: str) -> str:
    """
    Se o usuário digitar algo muito curto/sem país/UF, acrescenta 'RJ, Brasil' ou 'Brasil'.
    - Se já houver 'RJ'/'Brasil', mantém.
    """
    if not isinstance(addr, str):
        return addr
    a = addr.strip()
    a_low = strip_accents(a).lower()
    if (" rj" in a_low) or (" rio de janeiro" in a_low) or (" brasil" in a_low) or (" brazil" in a_low):
        return a
    # heurística simples: se só tem 1 parte (sem vírgula), completar com RJ e Brasil
    if len(a.split(",")) == 1:
        return f"{a}, RJ, Brasil"
    # senão, ao menos assegura Brasil
    return f"{a}, Brasil"

@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_geoapify(address: str):
    """
    Geocodifica um endereço usando Geoapify (se GEOAPIFY_KEY estiver configurada).
    Retorna (result, dbg):
      result: {'lat', 'lon', 'formatted'} ou None
      dbg:    {'provider','status','error_message','raw_sample'}
    """
    dbg = {"provider": "geoapify", "status": None, "error_message": None, "raw_sample": None}
    if not GEOAPIFY_KEY or not address or not address.strip():
        dbg["status"] = "MISSING_KEY_OR_ADDRESS"
        return None, dbg

    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": address,
        "lang": "pt",
        "filter": "countrycode:br",   # restringe ao Brasil
        "limit": 1,
        "apiKey": GEOAPIFY_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        feats = j.get("features", [])
        if not feats:
            dbg["status"] = "ZERO_RESULTS"
            return None, dbg
        p = feats[0]["properties"]
        dbg["status"] = "OK"
        dbg["raw_sample"] = {"formatted": p.get("formatted")}
        return {
            "lat": float(p["lat"]),
            "lon": float(p["lon"]),
            "formatted": p.get("formatted") or address
        }, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"
        return None, dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"
        dbg["error_message"] = str(e)
        return None, dbg

@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_nominatim(address: str, strict_rj: bool = True):
    """
    Nominatim (OSM) com duas modalidades:
      - strict_rj=True  -> usa viewbox do RJ (bounded=1)
      - strict_rj=False -> remove bounded e busca no Brasil todo
    Retorna (result, dbg).
    """
    dbg = {"provider": "nominatim", "status": None, "error_message": None, "raw_sample": None}
    address = _normalize_address_for_br(address)
    if not address or not address.strip():
        dbg["status"] = "MISSING_ADDRESS"
        return None, dbg
    try:
        time.sleep(1.0)  # respeita limites do serviço público
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": "br",
            "accept-language": "pt-BR",
        }
        headers = {"User-Agent": "busca-sites-b2b/1.0 (contato: seu-email@exemplo.com)"}
        if strict_rj:
            params.update({
                "viewbox": f"{RJ_VIEWBOX[0]},{RJ_VIEWBOX[1]},{RJ_VIEWBOX[2]},{RJ_VIEWBOX[3]}",
                "bounded": 1
            })
        r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=10)
        j = r.json()
        if j:
            item = j[0]
            dbg["status"] = "OK"
            dbg["raw_sample"] = {"display_name": item.get("display_name")}
            return {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "formatted": item.get("display_name")
            }, dbg
        else:
            dbg["status"] = "ZERO_RESULTS"
            return None, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"
        return None, dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"
        dbg["error_message"] = str(e)
        return None, dbg

def geocode_address(address: str):
    """
    Ordem:
      1) Geoapify (se key)
      2) Nominatim com viés RJ estrito
      3) Nominatim sem bounded (apenas BR)
    """
    # 1) Geoapify
    if GEOAPIFY_KEY:
        res, dbg = geocode_geoapify(address)
        if res:
            return res, dbg
    # 2) Nominatim com RJ estrito
    res2, dbg2 = geocode_nominatim(address, strict_rj=True)
    if res2:
        return res2, dbg2
    # 3) Nominatim sem bounded (Brasil inteiro)
    res3, dbg3 = geocode_nominatim(address, strict_rj=False)
    if res3:
        return res3, dbg3
    # nada encontrado
    return None, {"provider": "none", "status": "ZERO_RESULTS", "error_message": None}

# ------------------------------------------------------------
# Rotas/Matriz — OSRM (sem key)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=15*60)
def osrm_table(origin_lat: float, origin_lon: float, dests: List[Tuple[float, float]]):
    """
    Usa OSRM Table API (router.project-osrm.org) para obter duration/distance.
    dests: lista [(lat, lon), ...]
    Retorna (out, dbg):
      out: [{'distance_m','distance_text','duration_s','duration_text'}, ...]
      dbg: {'status','error_message'}
    """
    dbg = {"status": None, "error_message": None}
    if not dests:
        dbg["status"] = "NO_DESTS"
        return [], dbg

    # OSRM usa ordem lon,lat
    coords = [(origin_lon, origin_lat)] + [(lon, lat) for (lat, lon) in dests]
    coord_str = ";".join([f"{lon},{lat}" for (lon, lat) in coords])
    url = f"https://router.project-osrm.org/table/v1/driving/{coord_str}"
    params = {"annotations": "duration,distance"}

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        dbg["status"] = data.get("code", "OK")

        if data.get("code") != "Ok":
            dbg["error_message"] = data.get("message")
            return [], dbg

        durations = data.get("durations") or []
        distances = data.get("distances") or []
        if not durations or not distances:
            return [], dbg

        row0_dur = durations[0]  # origem -> todos
        row0_dis = distances[0]

        out = []
        for i in range(1, len(row0_dur)):
            dur = row0_dur[i]
            dist = row0_dis[i]
            out.append({
                "distance_m": None if dist is None else float(dist),
                "distance_text": None if dist is None else f"{dist/1000:.1f} km",
                "duration_s": None if dur is None else float(dur),
                "duration_text": None if dur is None else f"{math.ceil(dur/60)} min",
            })
        return out, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"
        return [], dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"
        dbg["error_message"] = str(e)
        return [], dbg

# ------------------------------------------------------------
# Dados principais (aba: enderecos)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_dados():
    df = pd.read_excel(
        "enderecos.xlsx",
        sheet_name="enderecos",  # <- sua aba real
        engine="openpyxl",
    )

    # padronizar nomes de colunas
    df.columns = df.columns.str.strip().str.lower()

    # renomear para padrão interno
    df = df.rename(columns={
        "sigla_da_torre": "sigla",
        "nome_da_torre": "nome",
        "endereço": "endereco",
        "latitude": "lat",
        "longitude": "lon",
    })

    # normalização textual
    for col in ["sigla", "nome", "endereco", "detentora"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # coordenadas com ponto
    for col in ["lat", "lon"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", pd.NA)
                .astype(float)
            )

    # garantir detentora
    if "detentora" not in df.columns:
        df["detentora"] = pd.NA

    return df

# ------------------------------------------------------------
# Aba "acessos" (técnicos com status ok)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_acessos_ok():
    try:
        acc = pd.read_excel("enderecos.xlsx", sheet_name="acessos", engine="openpyxl")
    except Exception:
        return None

    acc.columns = acc.columns.str.strip().str.lower()

    if "tecnico" not in acc.columns:
        for alt in ["técnico", "nome_tecnico", "colaborador"]:
            if alt in acc.columns:
                acc = acc.rename(columns={alt: "tecnico"})
                break

    if "sigla" not in acc.columns:
        for alt in ["sigla_da_torre", "site", "torre"]:
            if alt in acc.columns:
                acc = acc.rename(columns={alt: "sigla"})
                break

    # checagem mínima
    if "sigla" not in acc.columns or "tecnico" not in acc.columns:
        return None

    if "status" not in acc.columns:
        acc["status"] = "ok"

    for c in ["sigla", "tecnico", "status"]:
        acc[c] = acc[c].astype("string").str.strip()

    def norm(x): return strip_accents(str(x)).lower()
    acc = acc[acc["status"].apply(norm) == "ok"]

    return acc.reset_index(drop=True)

# ------------------------------------------------------------
# Carregar bases
# ------------------------------------------------------------
df = carregar_dados()
ACESSOS_OK = carregar_acessos_ok()

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("📡 Endereços dos Sites RJ")

if st.button("🔄 Atualizar dados (limpar cache)"):
    st.cache_data.clear()
    _rerun()

# -------------------- BUSCA POR SIGLA (existente) --------------------
with st.form("form_sigla", clear_on_submit=False):
    sigla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

# -------------------- BUSCA POR ENDEREÇO (sem diagnóstico) ----------
st.markdown("---")
st.subheader("🧭 Buscar por ENDEREÇO do cliente → 3 sites mais próximos")

with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input(
        "Digite o endereço completo (rua, número, bairro, cidade — RJ de preferência)"
    )
    submitted_endereco = st.form_submit_button("Buscar sites")

if submitted_endereco:
    st.session_state["endereco_cliente"] = endereco_cliente

endereco_filtro = st.session_state.get("endereco_cliente", "")

if endereco_filtro:
    with st.spinner("Geocodificando endereço e calculando distâncias..."):
        geo, _ = geocode_address(endereco_filtro)

    if not geo:
        st.error("❌ Endereço não encontrado. Tente incluir número/bairro/cidade. "
                 "Se persistir, refine o endereço ou tente outro próximo.")
    else:
        lat_cli, lon_cli = geo["lat"], geo["lon"]
        st.success("✅ Endereço localizado:")
        st.markdown(
            f"**{geo['formatted']}**  \n"
            f"🧭 **Coordenadas**: {lat_cli:.6f}, {lon_cli:.6f}"
        )

        # Filtra ERBs com coordenadas válidas
        base = df.dropna(subset=["lat", "lon"]).copy()
        if base.empty:
            st.warning("⚠️ Nenhuma ERB na planilha possui coordenadas válidas.")
        else:
            base["dist_km_linear"] = haversine_km(lat_cli, lon_cli, base["lat"].values, base["lon"].values)
            top3 = base.nsmallest(3, "dist_km_linear").copy()

            # OSRM: origem -> destinos top3
            dm_out, dm_dbg = osrm_table(
                lat_cli, lon_cli,
                [(float(r["lat"]), float(r["lon"])) for _, r in top3.iterrows()]
            )

            if dm_out and len(dm_out) == len(top3) and (dm_dbg.get("status") in ("Ok", "OK", None)):
                top3 = top3.reset_index(drop=True)
                top3["dist_rodov_text"] = [x["distance_text"] for x in dm_out]
                top3["duracao_text"]    = [x["duration_text"] for x in dm_out]
                top3["duracao_s"]       = [x["duration_s"] for x in dm_out]
            else:
                # Mantém a UI estável mesmo se OSRM falhar
                top3["dist_rodov_text"] = pd.NA
                top3["duracao_text"]    = pd.NA
                top3["duracao_s"]       = pd.NA

            st.markdown("### 📍 3 sites mais próximos (Quando disponível)")
            mostrar_cols = [c for c in [
                "sigla", "nome", "detentora", "endereco", "lat", "lon",
                "dist_km_linear", "dist_rodov_text", "duracao_text"
            ] if c in top3.columns]
            st.dataframe(
                top3[mostrar_cols].assign(dist_km_linear=lambda d: d["dist_km_linear"].round(3)),
                use_container_width=True
            )

            # Cartões com links (Mapa e Rota) — sem usar `or` com pd.NA
            for _, row in top3.iterrows():
                erb_lat, erb_lon = float(row["lat"]), float(row["lon"])
                maps_erb = f"https://www.google.com/maps/search/?api=1&query={erb_lat},{erb_lon}"
                rota = f"https://www.google.com/maps/dir/?api=1&origin={lat_cli},{lon_cli}&destination={erb_lat},{erb_lon}&travelmode=driving"

                dist_rodov_text = fmt_na(row.get("dist_rodov_text"))
                duracao_text    = fmt_na(row.get("duracao_text"))

                title = f"**{row.get('sigla', '—')} — {row.get('nome', '—')}**"
                meta = (
                    f"🗺️ Linha reta: **{row['dist_km_linear']:.3f} km**  \n"
                    f"🚗 Rota: {dist_rodov_text}  \n"
                    f"⏱️ Tempo: {duracao_text}  \n"
                    f"📌 Coords: {erb_lat:.6f}, {erb_lon:.6f}"
                )
                st.markdown(title + "  \n" + meta)
                cols = st.columns(2)
                with cols[0]:
                    st.link_button("🗺️ Ver no Google Maps", maps_erb, type="primary")
                with cols[1]:
                    st.link_button("🚗 Traçar rota a partir do cliente", rota)
                st.markdown("---")

st.markdown("---")

# -------------------- RESULTADO DA BUSCA POR SIGLA (existente) --------------------
if sigla_filtro:
    df_f = df[df["sigla"].astype(str).str.upper() == str(sigla_filtro).upper()].copy()
else:
    df_f = pd.DataFrame()

if df_f.empty:
    st.warning("⚠️ Nenhum site encontrado.")
else:
    # Detecção de cidade aprimorada: tenta no 'nome' e, se não, no 'endereco'
    df_f["cidade"] = df_f.apply(lambda r: detectar_cidade(r.get("nome"), r.get("endereco")), axis=1)

    st.success(f"🔎 {len(df_f)} site(s) encontrado(s).")

    st.dataframe(
        df_f[["sigla", "cidade", "detentora", "nome", "endereco", "lat", "lon"]],
        use_container_width=True
    )

    st.markdown("### 📍 Detalhes do(s) site(s) encontrado(s)")

    def tecnicos_por_sigla(sig: str):
        if ACESSOS_OK is None or ACESSOS_OK.empty:
            return []
        temp = ACESSOS_OK[ACESSOS_OK["sigla"].astype(str).str.upper() == str(sig).upper()]
        return sorted(temp["tecnico"].dropna().unique().tolist())

    for _, row in df_f.iterrows():
        st.markdown(f"**{row['sigla']} — {row['nome']}**")

        if pd.notna(row.get("lat")) and pd.notna(row.get("lon")):
            url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.link_button("🗺️ Ver no Google Maps", url, type="primary")

        det = row["detentora"] if pd.notna(row["detentora"]) else "—"
        st.markdown(
            f"🏙️ **Cidade:** {row.get('cidade') or '—'}  \n"
            f"🏢 **Detentora:** {det}  \n"
            f"📌 **Endereço:** {row['endereco']}"
        )

        tecnicos = tecnicos_por_sigla(row["sigla"])
        lista_md = "\n".join([f"- {t}" for t in tecnicos]) if tecnicos else "—"
        st.info(f"**👤 Técnicos com acesso liberado:**\n{lista_md}")

        st.markdown("---")

st.caption("❤️ Desenvolvido por Raphael Robles - Stay hungry, stay foolish ! 🚀")


































