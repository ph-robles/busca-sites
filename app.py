
# ============================================================
# 📡 Endereços dos Sites RJ — Google Geocoding + Distance Matrix
# + Diagnóstico + Fallback OSM + Retry + Cache + Compat rerun
# Mantém todas as funcionalidades originais por SIGLA e Acessos OK
# ============================================================

import streamlit as st
import pandas as pd
import unicodedata
import time
import requests
import numpy as np
from typing import List, Tuple, Optional

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ------------------------------------------------------------
# Secrets / Chave Google
# ------------------------------------------------------------
API_KEY = (st.secrets.get("GOOGLE_MAPS_API_KEY", "") or "").strip()

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

# ------------------------------------------------------------
# Parâmetros de Geocoding
# ------------------------------------------------------------
# Bounds aproximado do RJ (latSW,lngSW|latNE,lngNE)
RJ_BOUNDS = "-23.1,-43.8|-22.7,-43.0"   # opcional, melhora match no RJ

# Status que valem retry (transientes)
RETRYABLE_STATUSES = {"UNKNOWN_ERROR", "OVER_QUERY_LIMIT", "RESOURCE_EXHAUSTED"}

# ------------------------------------------------------------
# Geocoding - Google com diagnóstico e retry
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_google_verbose(address: str, use_bounds: bool = True, max_retries: int = 2, base_sleep: float = 1.0):
    """
    Geocodifica endereço via Google Geocoding API.
    Retorna: (result, debug)
      result: {'lat': float, 'lon': float, 'formatted': str} ou None
      debug:  {'provider','status','error_message','raw_sample'}
    - Usa region=br, language=pt-BR, components=country:BR
    - Opcional bounds do RJ
    - Retry exponencial para erros transitórios
    """
    dbg = {"provider": "google", "status": None, "error_message": None, "raw_sample": None}

    if not API_KEY or not address or not address.strip():
        dbg["status"] = "MISSING_API_KEY_OR_ADDRESS"
        return None, dbg

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "region": "br",
        "language": "pt-BR",
        "components": "country:BR",
    }
    if use_bounds:
        params["bounds"] = RJ_BOUNDS

    sleep = base_sleep
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params={**params, "key": API_KEY}, timeout=10)
            data = resp.json()
            status = data.get("status")
            dbg["status"] = status
            dbg["error_message"] = data.get("error_message")
            dbg["raw_sample"] = {
                "results_len": len(data.get("results", [])),
                "first": data.get("results", [{}])[0].get("formatted_address") if data.get("results") else None
            }

            if status == "OK" and data.get("results"):
                res = data["results"][0]
                loc = res["geometry"]["location"]
                return {
                    "lat": float(loc["lat"]),
                    "lon": float(loc["lng"]),
                    "formatted": res.get("formatted_address") or address
                }, dbg

            # ZERO_RESULTS é caso normal (endereço inválido/ambíguo)
            if status == "ZERO_RESULTS":
                return None, dbg

            # Status transitório? Retry
            if status in RETRYABLE_STATUSES and attempt < max_retries:
                time.sleep(sleep)
                sleep *= 2
                continue

            # Qualquer outro erro: não retry
            return None, dbg

        except requests.exceptions.Timeout:
            dbg["status"] = "TIMEOUT"
            if attempt < max_retries:
                time.sleep(sleep)
                sleep *= 2
                continue
            return None, dbg
        except Exception as e:
            dbg["status"] = "EXCEPTION"
            dbg["error_message"] = str(e)
            return None, dbg

# ------------------------------------------------------------
# Fallback: Nominatim (OSM) caso Google falhe
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_nominatim(address: str):
    """
    Fallback leve usando Nominatim (sem chave).
    Retorna (result, debug)
    """
    dbg = {"provider": "nominatim", "status": None, "error_message": None, "raw_sample": None}
    if not address or not address.strip():
        dbg["status"] = "MISSING_ADDRESS"
        return None, dbg
    try:
        # respeita política de uso (não flood)
        time.sleep(1.0)
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "br",
                "accept-language": "pt-BR"
            },
            headers={"User-Agent": "busca-sites-b2b/1.0"},
            timeout=10
        )
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

def geocode_fallback(address: str, use_bounds: bool = True):
    """
    Tenta Google; se falhar por erro/limite/denied, tenta Nominatim.
    Retorna (result, diag_combined)
    """
    res, dbg = geocode_google_verbose(address, use_bounds=use_bounds)
    if res:
        return res, dbg
    # Se foi ZERO_RESULTS, não vale insistir com OSM (mas podemos tentar)
    if dbg.get("status") in {"OVER_QUERY_LIMIT", "RESOURCE_EXHAUSTED", "REQUEST_DENIED", "TIMEOUT", "EXCEPTION", "UNKNOWN_ERROR"}:
        res2, dbg2 = geocode_nominatim(address)
        if res2:
            return res2, dbg2
        return None, {"provider": "none", "status": f"google_{dbg.get('status')}_and_osm_{dbg2.get('status')}", "error_message": dbg.get("error_message")}
    else:
        # ZERO_RESULTS ou outros
        return None, dbg

# ------------------------------------------------------------
# Distance Matrix (rota) com debug e cache
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=15*60)
def distance_matrix_google(origin_lat: float, origin_lon: float, dests: List[Tuple[float, float]], mode="driving", max_retries: int = 2):
    """
    Calcula tempo/distância por rota (Google Distance Matrix).
    Retorna (out, dbg) onde:
      out: lista dicts na mesma ordem dos destinos
      dbg: {'status','error_message'}
    """
    dbg = {"status": None, "error_message": None}
    if not API_KEY or not dests:
        dbg["status"] = "MISSING_API_KEY_OR_DESTS"
        return [], dbg

    origins = f"{origin_lat},{origin_lon}"
    destinations = "|".join([f"{lat},{lon}" for (lat, lon) in dests])
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    sleep = 1.0
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(url, params={
                "origins": origins,
                "destinations": destinations,
                "mode": mode,
                "language": "pt-BR",
                "key": API_KEY
            }, timeout=10)
            data = r.json()
            status = data.get("status")
            dbg["status"] = status
            dbg["error_message"] = data.get("error_message")

            if status == "OK":
                rows = data.get("rows", [])
                if not rows:
                    return [], dbg
                elements = rows[0].get("elements", [])
                out = []
                for el in elements:
                    if el.get("status") == "OK":
                        out.append({
                            "distance_m": el["distance"]["value"],
                            "distance_text": el["distance"]["text"],
                            "duration_s": el["duration"]["value"],
                            "duration_text": el["duration"]["text"],
                        })
                    else:
                        out.append({
                            "distance_m": None, "distance_text": None,
                            "duration_s": None, "duration_text": None
                        })
                return out, dbg

            # Retry em status transitórios
            if status in RETRYABLE_STATUSES and attempt < max_retries:
                time.sleep(sleep)
                sleep *= 2
                continue

            return [], dbg

        except requests.exceptions.Timeout:
            dbg["status"] = "TIMEOUT"
            if attempt < max_retries:
                time.sleep(sleep)
                sleep *= 2
                continue
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
# Detectar cidade (leve) a partir do nome
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

def detectar_cidade(nome: str):
    if not isinstance(nome, str):
        return None
    base = strip_accents(nome).lower()
    ultimo = None
    for key, city in MUNI_IDX.items():
        if key in base:
            ultimo = city
    return ultimo

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

if not API_KEY:
    st.warning("⚠️ Configure sua chave em Settings → Secrets como `GOOGLE_MAPS_API_KEY`. "
               "Sem isso, a busca por endereço/rota usará apenas o fallback OSM (quando possível).")

# -------------------- BUSCA POR SIGLA (existente) --------------------
with st.form("form_sigla", clear_on_submit=False):
    sigla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

# -------------------- BUSCA POR ENDEREÇO (NOVO) ---------------------
st.markdown("---")
st.subheader("🧭 Buscar por ENDEREÇO do cliente → 3 ERBs mais próximas")

with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input(
        "Digite o endereço completo (rua, número, bairro, cidade — RJ de preferência)"
    )
    use_bounds = st.checkbox("Viés RJ (melhorar acerto usando bounds do RJ)", value=True)
    mostrar_diag = st.checkbox("Mostrar diagnóstico de Geocoding (temporário)", value=False)
    submitted_endereco = st.form_submit_button("Buscar ERBs")

if submitted_endereco:
    st.session_state["endereco_cliente"] = endereco_cliente
    st.session_state["use_bounds"] = use_bounds
    st.session_state["mostrar_diag"] = mostrar_diag

endereco_filtro = st.session_state.get("endereco_cliente", "")
use_bounds = st.session_state.get("use_bounds", True)
mostrar_diag = st.session_state.get("mostrar_diag", False)

if endereco_filtro:
    with st.spinner("Geocodificando endereço e calculando distâncias..."):
        geo, dbg = geocode_fallback(endereco_filtro, use_bounds=use_bounds)

    # Diagnóstico opcional
    if mostrar_diag:
        st.code(
            f"Provider: {dbg.get('provider')}\n"
            f"Status:   {dbg.get('status')}\n"
            f"Erro:     {dbg.get('error_message')}\n"
            f"Amostra:  {dbg.get('raw_sample')}",
            language="text"
        )

    if not geo:
        st.error("❌ Endereço não encontrado. Tente incluir número/bairro/cidade. "
                 "Se persistir, revise as restrições da API key (Geocoding habilitado, Application=None, API restrito).")
    else:
        lat_cli, lon_cli = geo["lat"], geo["lon"]
        prov = dbg.get("provider", "google")
        st.success(f"✅ Endereço localizado ({'Google' if prov=='google' else 'OSM'}):")
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

            # Distance Matrix (rota) – só se tiver API_KEY
            dm_out, dm_dbg = ([], {})
            if API_KEY:
                dm_out, dm_dbg = distance_matrix_google(
                    lat_cli, lon_cli,
                    [(float(r["lat"]), float(r["lon"])) for _, r in top3.iterrows()],
                    mode="driving"
                )

            if dm_out and len(dm_out) == len(top3):
                top3 = top3.reset_index(drop=True)
                top3["dist_rodov_text"] = [x["distance_text"] for x in dm_out]
                top3["duracao_text"] = [x["duration_text"] for x in dm_out]
                top3["duracao_s"] = [x["duration_s"] for x in dm_out]
            else:
                top3["dist_rodov_text"] = pd.NA
                top3["duracao_text"] = pd.NA
                top3["duracao_s"] = pd.NA

            st.markdown("### 📍 3 ERBs mais próximas (ranking por linha reta; rota quando disponível)")
            mostrar_cols = [c for c in [
                "sigla", "nome", "detentora", "endereco", "lat", "lon",
                "dist_km_linear", "dist_rodov_text", "duracao_text"
            ] if c in top3.columns]
            st.dataframe(
                top3[mostrar_cols].assign(dist_km_linear=lambda d: d["dist_km_linear"].round(3)),
                use_container_width=True
            )

            # Diagnóstico Distance Matrix (se pedido)
            if mostrar_diag and dm_dbg:
                st.code(
                    f"[DistanceMatrix] Status: {dm_dbg.get('status')} | Erro: {dm_dbg.get('error_message')}",
                    language="text"
                )

            # Cartões com links (Mapa e Rota)
            for _, row in top3.iterrows():
                erb_lat, erb_lon = float(row["lat"]), float(row["lon"])
                maps_erb = f"https://www.google.com/maps/search/?api=1&query={erb_lat},{erb_lon}"
                rota = f"https://www.google.com/maps/dir/?api=1&origin={lat_cli},{lon_cli}&destination={erb_lat},{erb_lon}&travelmode=driving"

                title = f"**{row.get('sigla', '—')} — {row.get('nome', '—')}**"
                meta = (
                    f"🗺️ Linha reta: **{row['dist_km_linear']:.3f} km**  \n"
                    f"🚗 Rota: {row.get('dist_rodov_text') or '—'}  \n"
                    f"⏱️ Tempo: {row.get('duracao_text') or '—'}  \n"
                    f"📌 Coords: {erb_lat:.6f}, {erb_lon:.6f}"
                )
                st.markdown(title + "  \n" + meta)
                cols = st.columns(2)
                with cols[0]:
                    st.link_button("🗺️ Ver ERB no Google Maps", maps_erb, type="primary")
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
    df_f["cidade"] = df_f["nome"].apply(detectar_cidade)

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





























