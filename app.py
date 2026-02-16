
# ============================================================
# 📡 Endereços dos Sites RJ — OSM/OSRM Edition (100% gratuito)
# Supabase SOMENTE (sem fallback) + Streamlit
# - Geocoding: Geoapify (opcional) → fallback Nominatim
# - Rotas/Matriz: OSRM (sem key)
# - Detecção de cidade (regex + fallback no endereço)
# - UX: chips de sugestões, fuzzy (≤1 erro), Top3 com capacitado mais próximo
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
# Supabase (exige SDK instalada e secrets configurados)
# ------------------------------------------------------------
try:
    from supabase import create_client, Client  # type: ignore
except Exception:
    st.error(
        "❌ Supabase SDK não encontrada. Instale com:\n\n"
        "```\npip install supabase>=2.6.0\n```"
    )
    st.stop()

# Secrets
GEOAPIFY_KEY = (st.secrets.get("GEOAPIFY_KEY", "") or "").strip()
SUPABASE_URL = (st.secrets.get("SUPABASE_URL", "") or "").strip()
SUPABASE_ANON_KEY = (st.secrets.get("SUPABASE_ANON_KEY", "") or "").strip()

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error(
        "❌ Secrets do Supabase ausentes. Configure em `.streamlit/secrets.toml` ou no painel de Secrets do Streamlit Cloud:\n\n"
        "```\nSUPABASE_URL = \"https://SEU-PROJETO.supabase.co\"\n"
        "SUPABASE_ANON_KEY = \"SUA_CHAVE_ANON\"\n```"
    )
    st.stop()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)  # type: ignore
except Exception as e:
    st.error(f"❌ Falha para inicializar o cliente do Supabase: {e}")
    st.stop()

# ------------------------------------------------------------
# Helpers gerais
# ------------------------------------------------------------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    lat1 = np.radians(lat1); lon1 = np.radians(lon1)
    lat2 = np.radians(lat2); lon2 = np.radians(lon2)
    dlat = lat2 - lat1; dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def fmt_na(x, dash="—"):
    try:
        return dash if (x is pd.NA or pd.isna(x)) else x
    except Exception:
        return dash if x is None else x

def normalizar_sigla(sigla: str) -> str:
    if not isinstance(sigla, str):
        return ""
    s = sigla.strip().upper().replace(" ", "").replace("-", "")
    if s.startswith("RJ"):
        s = s[2:]
    return s

YES_ALIASES = {"sim", "s", "yes", "y", "1", "true", "verdadeiro", "ok"}
NO_ALIASES  = {"nao", "não", "n", "no", "0", "false", "falso"}

def _to_str_lower(x):
    try:
        return strip_accents(str(x)).lower().strip()
    except Exception:
        return None

def is_yes(val) -> bool | None:
    if val is pd.NA or pd.isna(val):
        return None
    v = _to_str_lower(val)
    if not v: return None
    if v in YES_ALIASES: return True
    if v in NO_ALIASES:  return False
    return None

def capacitado_badge(val) -> str:
    yn = is_yes(val)
    if yn is True:  return "✅ **Capacitado**"
    if yn is False: return "❌ **Não capacitado**"
    return "—"

BANNER_MSG = """# ============================================================
# 📡 Endereços dos Sites RJ — OSM/OSRM Edition (100% gratuito)
# - Geocoding: Geoapify (opcional, com key) → fallback Nominatim (sem key)
# - Rotas/Matriz: OSRM (sem key) para distância/tempo por trajeto
# - Detecção de cidade aprimorada (regex + fallback no endereço)
# - Geocodificação robusta (duas tentativas no Nominatim)
# - Mantém toda a lógica de SIGLA e Acessos OK
# ============================================================"""

# ------------------------------------------------------------
# Detecção de cidade
# ------------------------------------------------------------
RJ_VIEWBOX = (-43.8, -23.1, -43.0, -22.7)

MUNICIPIOS_RJ = [
    "Angra dos Reis","Aperibé","Araruama","Areal","Armação dos Búzios","Arraial do Cabo",
    "Barra do Piraí","Barra Mansa","Belford Roxo","Bom Jardim","Bom Jesus do Itabapoana",
    "Cabo Frio","Cachoeiras de Macacu","Cambuci","Campos dos Goytacazes","Cantagalo",
    "Carapebus","Cardoso Moreira","Carmo","Casimiro de Abreu","Conceição de Macabu",
    "Cordeiro","Duas Barras","Duque de Caxias","Engenheiro Paulo de Frontin","Guapimirim",
    "Iguaba Grande","Itaboraí","Itaguaí","Italva","Itaocara","Itaperuna","Itatiaia",
    "Japeri","Laje do Muriaé","Macaé","Macuco","Magé","Mangaratiba","Maricá","Mendes",
    "Mesquita","Miguel Pereira","Miracema","Natividade","Nilópolis","Niterói",
    "Nova Friburgo","Nova Iguaçu","Paracambi","Paraíba do Sul","Parati","Paty do Alferes",
    "Petrópolis","Pinheiral","Piraí","Porciúncula","Porto Real","Quatis","Queimados",
    "Quissamã","Resende","Rio Bonito","Rio Claro","Rio das Flores","Rio das Ostras",
    "Rio de Janeiro","Santa Maria Madalena","Santo Antônio de Pádua","São Fidélis",
    "São Francisco de Itabapoana","São Gonçalo","São João da Barra","São João de Meriti",
    "São José de Ubá","São José do Vale do Rio Preto","São Pedro da Aldeia",
    "São Sebastião do Alto","Sapucaia","Saquarema","Seropédica","Silva Jardim",
    "Sumidouro","Tanguá","Teresópolis","Trajano de Moraes","Três Rios","Valença",
    "Varre-Sai","Vassouras","Volta Redonda"
]
MUNI_IDX = {strip_accents(n).lower(): n for n in MUNICIPIOS_RJ}
_CITY_PATTERNS = {key: re.compile(rf"\b{re.escape(key)}\b") for key in MUNI_IDX.keys()}

def _match_city_base(texto: str) -> str | None:
    if not isinstance(texto, str) or not texto.strip():
        return None
    base = strip_accents(texto).lower()
    ultimo = None
    for key, pat in _CITY_PATTERNS.items():
        if pat.search(base):
            ultimo = MUNI_IDX[key]
    return ultimo

def detectar_cidade(nome: str, endereco: str | None = None) -> str | None:
    city = _match_city_base(nome)
    if city: return city
    if endereco: return _match_city_base(endereco)
    return None

# ------------------------------------------------------------
# Geocoding — Geoapify (opcional) + Nominatim
# ------------------------------------------------------------
def _normalize_address_for_br(addr: str) -> str:
    if not isinstance(addr, str): return addr
    a = addr.strip(); a_low = strip_accents(a).lower()
    if (" rj" in a_low) or (" rio de janeiro" in a_low) or (" brasil" in a_low) or (" brazil" in a_low):
        return a
    if len(a.split(",")) == 1:
        return f"{a}, RJ, Brasil"
    return f"{a}, Brasil"

@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_geoapify(address: str):
    dbg = {"provider": "geoapify", "status": None, "error_message": None, "raw_sample": None}
    if not GEOAPIFY_KEY or not address or not address.strip():
        dbg["status"] = "MISSING_KEY_OR_ADDRESS"; return None, dbg
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {"text": address, "lang": "pt", "filter": "countrycode:br", "limit": 1, "apiKey": GEOAPIFY_KEY}
    try:
        r = requests.get(url, params=params, timeout=10); r.raise_for_status()
        j = r.json(); feats = j.get("features", [])
        if not feats: dbg["status"] = "ZERO_RESULTS"; return None, dbg
        p = feats[0]["properties"]
        dbg["status"] = "OK"; dbg["raw_sample"] = {"formatted": p.get("formatted")}
        return {"lat": float(p["lat"]), "lon": float(p["lon"]), "formatted": p.get("formatted") or address}, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"; return None, dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"; dbg["error_message"] = str(e); return None, dbg

@st.cache_data(show_spinner=False, ttl=60*60)
def geocode_nominatim(address: str, strict_rj: bool = True):
    dbg = {"provider": "nominatim", "status": None, "error_message": None, "raw_sample": None}
    address = _normalize_address_for_br(address)
    if not address or not address.strip():
        dbg["status"] = "MISSING_ADDRESS"; return None, dbg
    try:
        time.sleep(1.0)
        params = {"q": address, "format": "json", "limit": 1, "countrycodes": "br", "accept-language": "pt-BR"}
        headers = {"User-Agent": "busca-sites-b2b/1.0 (contato: seu-email@exemplo.com)"}
        if strict_rj:
            params.update({"viewbox": f"{RJ_VIEWBOX[0]},{RJ_VIEWBOX[1]},{RJ_VIEWBOX[2]},{RJ_VIEWBOX[3]}", "bounded": 1})
        r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=10)
        j = r.json()
        if j:
            item = j[0]; dbg["status"] = "OK"; dbg["raw_sample"] = {"display_name": item.get("display_name")}
            return {"lat": float(item["lat"]), "lon": float(item["lon"]), "formatted": item.get("display_name")}, dbg
        dbg["status"] = "ZERO_RESULTS"; return None, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"; return None, dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"; dbg["error_message"] = str(e); return None, dbg

def geocode_address(address: str):
    if GEOAPIFY_KEY:
        res, dbg = geocode_geoapify(address)
        if res: return res, dbg
    res2, dbg2 = geocode_nominatim(address, strict_rj=True)
    if res2: return res2, dbg2
    res3, dbg3 = geocode_nominatim(address, strict_rj=False)
    if res3: return res3, dbg3
    return None, {"provider": "none", "status": "ZERO_RESULTS", "error_message": None}

# ------------------------------------------------------------
# OSRM Table — distância/tempo
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=15*60)
def osrm_table(origin_lat: float, origin_lon: float, dests: List[Tuple[float, float]]):
    dbg = {"status": None, "error_message": None}
    if not dests: dbg["status"] = "NO_DESTS"; return [], dbg
    coords = [(origin_lon, origin_lat)] + [(lon, lat) for (lat, lon) in dests]  # OSRM usa lon,lat
    coord_str = ";".join([f"{lon},{lat}" for (lon, lat) in coords])
    url = f"https://router.project-osrm.org/table/v1/driving/{coord_str}"
    params = {"annotations": "duration,distance"}
    try:
        r = requests.get(url, params=params, timeout=10); r.raise_for_status()
        data = r.json(); dbg["status"] = data.get("code", "OK")
        if data.get("code") != "Ok":
            dbg["error_message"] = data.get("message"); return [], dbg
        durations = data.get("durations") or []; distances = data.get("distances") or []
        if not durations or not distances: return [], dbg
        row0_dur = durations[0]; row0_dis = distances[0]
        out = []
        for i in range(1, len(row0_dur)):
            dur = row0_dur[i]; dist = row0_dis[i]
            out.append({
                "distance_m": None if dist is None else float(dist),
                "distance_text": None if dist is None else f"{dist/1000:.1f} km",
                "duration_s": None if dur is None else float(dur),
                "duration_text": None if dur is None else f"{math.ceil(dur/60)} min",
            })
        return out, dbg
    except requests.exceptions.Timeout:
        dbg["status"] = "TIMEOUT"; return [], dbg
    except Exception as e:
        dbg["status"] = "EXCEPTION"; dbg["error_message"] = str(e); return [], dbg

# ------------------------------------------------------------
# Carga (Supabase SOMENTE)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60)
def carregar_dados():
    """
    Lê a tabela 'enderecos' do Supabase e normaliza colunas para o app:
    - sigla, nome, detentora, endereco, lat, lon, capacitado (opcional)
    """
    resp = supabase.table("enderecos").select(
        "sigla, nome, detentora, endereco, latitude, longitude, capacitado"
    ).execute()

    rows = resp.data or []
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("⚠️ Nenhum registro encontrado em 'enderecos'.")
        return pd.DataFrame(columns=["sigla","nome","detentora","endereco","lat","lon","capacitado"])

    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={"latitude":"lat","longitude":"lon"})
    for col in ["sigla","nome","endereco","detentora","capacitado"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    for col in ["lat","lon"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "detentora" not in df.columns: df["detentora"] = pd.NA
    if "capacitado" not in df.columns: df["capacitado"] = pd.NA
    return df

@st.cache_data(show_spinner=False, ttl=60)
def carregar_capacitados_lista():
    """
    Lê 'capacitados' (sigla, status) no Supabase.
    Retorna set(SIGLA) onde status é 'SIM' (considera variações via is_yes()).
    Se tabela vazia/inexistente, retorna set() (app ainda funciona usando coluna 'capacitado' da 'enderecos', se houver).
    """
    try:
        resp = supabase.table("capacitados").select("sigla, status").execute()
    except Exception:
        return set()
    rows = resp.data or []
    if not rows:
        return set()
    dfc = pd.DataFrame(rows)
    dfc.columns = dfc.columns.str.strip().str.lower()
    if "sigla" not in dfc.columns:
        return set()
    if "status" in dfc.columns:
        mask_ok = dfc["status"].apply(is_yes) == True
        siglas_ok = dfc.loc[mask_ok,"sigla"].astype(str).str.upper().unique().tolist()
    else:
        siglas_ok = dfc["sigla"].astype(str).str.upper().unique().tolist()
    return set(siglas_ok)

@st.cache_data(show_spinner=False, ttl=60)
def carregar_acessos_ok():
    """
    Lê 'acessos' (sigla, tecnico, status) no Supabase e filtra status == 'ok'.
    Se a tabela não existir ou estiver vazia, retorna None (app continua funcionando).
    """
    try:
        resp = supabase.table("acessos").select("sigla, tecnico, status").execute()
    except Exception:
        return None
    rows = resp.data or []
    if not rows:
        return None
    acc = pd.DataFrame(rows)
    acc.columns = acc.columns.str.strip().str.lower()
    for c in ["sigla","tecnico","status"]:
        if c in acc.columns:
            acc[c] = acc[c].astype("string").str.strip()

    def norm(x): return strip_accents(str(x)).lower()
    acc = acc[acc["status"].apply(norm) == "ok"]
    return acc.reset_index(drop=True) if not acc.empty else None

# ------------------------------------------------------------
# Unificação de 'capacitado'
# ------------------------------------------------------------
def unificar_capacitado(df: pd.DataFrame, siglas_cap_set: set | None):
    df = df.copy()
    if "capacitado" in df.columns:
        df["capacitado"] = df["capacitado"].astype("string").str.strip()
        df["_is_capacitado"] = df["capacitado"].apply(is_yes) == True
        df["capacitado"] = df["_is_capacitado"].map({True:"SIM", False:"NÃO"}).astype("string")
    elif siglas_cap_set is not None:
        siglas_upper = df["sigla"].astype(str).str.upper()
        is_cap = siglas_upper.isin(siglas_cap_set)
        df["_is_capacitado"] = is_cap
        df["capacitado"] = is_cap.map({True:"SIM", False:"NÃO"}).astype("string")
    else:
        df["_is_capacitado"] = False
        df["capacitado"] = pd.NA
    return df

# ------------------------------------------------------------
# Carregar bases
# ------------------------------------------------------------
df_raw = carregar_dados()
siglas_cap_set = carregar_capacitados_lista()
df = unificar_capacitado(df_raw, siglas_cap_set)
ACESSOS_OK = carregar_acessos_ok()

# ------------------------------------------------------------
# Detector de atualização (contagem Supabase)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=30)
def _count_enderecos():
    resp = supabase.table("enderecos").select("id", count="exact").limit(1).execute()
    # PostgrestResponse geralmente possui .count com o total
    return resp.count or (len(resp.data) if resp.data is not None else 0)

curr_count = _count_enderecos()
prev_count = st.session_state.get("enderecos_count")
if prev_count is None:
    st.session_state["enderecos_count"] = curr_count
elif prev_count != curr_count:
    st.session_state["enderecos_count"] = curr_count
    st.info(f"**Base de dados atualizada!**\n\n```\n{BANNER_MSG}\n```")

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("📡 Endereços dos Sites RJ")

if st.button("🔄 Atualizar dados (limpar cache)"):
    st.cache_data.clear()
    _rerun()

# ============================================================
# BUSCA POR SIGLA
# ============================================================
st.markdown("---")
st.subheader("🔍 Buscar por SIGLA")

lista_siglas = sorted(df["sigla"].dropna().astype(str).str.upper().unique().tolist())

if "busca_sigla_input" not in st.session_state:
    st.session_state["busca_sigla_input"] = ""

if "busca_sigla_pending" in st.session_state:
    st.session_state["busca_sigla_input"] = st.session_state.pop("busca_sigla_pending")

auto_trigger = st.session_state.pop("do_busca_sigla", False)
sigla_results_ct = st.container()

def _levenshtein(a: str, b: str) -> int:
    if a == b: return 0
    if not a:  return len(b)
    if not b:  return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            ins = prev[j] + 1
            dele = curr[j - 1] + 1
            sub = prev[j - 1] + (ca != cb)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]

def _gerar_sugestoes(busca_raw: str, candidatos: list[str], limite: int = 8) -> list[str]:
    if not busca_raw: return []
    bn = normalizar_sigla(busca_raw)
    pares = [(s, normalizar_sigla(s)) for s in candidatos]
    pref = [s for s, n in pares if n.startswith(bn)]
    seen = set(pref)
    if len(pref) < limite:
        substr = [s for s, n in pares if (bn in n) and (s not in seen)]
        pref.extend(substr); seen.update(substr)
    if len(pref) < limite:
        fuzzy = []
        for s, n in pares:
            if s in seen: continue
            d = _levenshtein(n, bn)
            if d <= 1: fuzzy.append((d, s))
        fuzzy = [s for _, s in sorted(fuzzy, key=lambda x: (x[0], x[1]))]
        pref.extend(fuzzy)
    return pref[:limite]

def _select_sugestao(value: str):
    st.session_state["busca_sigla_pending"] = value
    st.session_state["do_busca_sigla"] = True

with st.form("form_sigla", clear_on_submit=False):
    busca = st.text_input("Digite a sigla do site/ERB", key="busca_sigla_input")
    submitted = st.form_submit_button("OK")

# CSS chips
st.markdown(
    """
<style>
#chips-scope { margin-top: .25rem; }
#chips-scope div[data-testid="stHorizontalBlock"] { row-gap: .5rem; }
#chips-scope div[data-testid="stButton"] > button {
  border-radius: 9999px; padding: .35rem .9rem; font-size: 0.9rem; line-height: 1rem;
  border: 1px solid rgba(49,51,63,0.25); background: rgba(49,51,63,0.04);
  color: inherit; cursor: pointer; transition: all .15s ease-in-out;
}
#chips-scope div[data-testid="stButton"] > button:hover {
  background: rgba(49,51,63,0.08); border-color: rgba(49,51,63,0.4); transform: translateY(-1px);
}
#chips-scope div[data-testid="stButton"] > button:active { transform: translateY(0px) scale(.98); }
:root .st-dark #chips-scope div[data-testid="stButton"] > button {
  border-color: rgba(250, 250, 250, 0.18); background: rgba(250, 250, 250, 0.06);
}
:root .st-dark #chips-scope div[data-testid="stButton"] > button:hover {
  border-color: rgba(250, 250, 250, 0.35); background: rgba(250, 250, 250, 0.12);
}
</style>
""",
    unsafe_allow_html=True,
)

if busca:
    sugestoes = _gerar_sugestoes(busca, lista_siglas, limite=8)
    if sugestoes:
        st.markdown("### 🔎 Sugestões (clique para buscar)")
        st.markdown('<div id="chips-scope">', unsafe_allow_html=True)
        cols = st.columns(max(2, min(6, len(sugestoes))))
        for i, s in enumerate(sugestoes):
            with cols[i % len(cols)]:
                st.button(s, key=f"sug_{s}", on_click=_select_sugestao, args=(s,))
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("Nenhuma sugestão encontrada.")

if (submitted or auto_trigger) and st.session_state.get("busca_sigla_input"):
    busca_val = st.session_state.get("busca_sigla_input", "")
    busca_norm = normalizar_sigla(busca_val)
    sigla_encontrada = None
    for s_ in lista_siglas:
        if normalizar_sigla(s_) == busca_norm:
            sigla_encontrada = s_; break
    if sigla_encontrada is None:
        dists = [(s_, _levenshtein(normalizar_sigla(s_), busca_norm)) for s_ in lista_siglas]
        s_best, d_best = min(dists, key=lambda x: x[1]) if dists else (None, 999)
        if d_best <= 1: sigla_encontrada = s_best
    if sigla_encontrada:
        df_f = df[df["sigla"].astype(str).str.upper() == sigla_encontrada].copy()
    else:
        df_f = pd.DataFrame()
else:
    df_f = pd.DataFrame()

with sigla_results_ct:
    if df_f.empty:
        st.warning("⚠️ Nenhum site encontrado.")
    else:
        df_f["cidade"] = df_f.apply(lambda r: detectar_cidade(r.get("nome"), r.get("endereco")), axis=1)
        st.success(f"🔎 {len(df_f)} site(s) encontrado(s).")

        cols_sigla = [c for c in ["sigla","cidade","detentora","nome","endereco","lat","lon","capacitado"] if c in df_f.columns]
        st.dataframe(df_f[cols_sigla], use_container_width=True)

        st.markdown("### 📍 Detalhes do(s) site(s) encontrado(s)")

        def tecnicos_por_sigla(sig: str):
            if ACESSOS_OK is None or ACESSOS_OK.empty: return []
            temp = ACESSOS_OK[ACESSOS_OK["sigla"].astype(str).str.upper() == str(sig).upper()]
            return sorted(temp["tecnico"].dropna().unique().tolist())

        for _, row in df_f.iterrows():
            st.markdown(f"**{row['sigla']} — {row['nome']}**")

            if pd.notna(row.get("lat")) and pd.notna(row.get("lon")):
                url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
                st.link_button("🗺️ Ver no Google Maps", url, type="primary")

            det = row["detentora"] if pd.notna(row["detentora"]) else "—"
            cap_badge_row = capacitado_badge(row.get("capacitado"))
            st.markdown(
                f"🏙️ **Cidade:** {row.get('cidade') or '—'}  \n"
                f"🏢 **Detentora:** {det}  \n"
                f"📌 **Endereço:** {row['endereco']}  \n"
                f"🧰 {cap_badge_row}"
            )

            tecnicos = tecnicos_por_sigla(row["sigla"])
            lista_md = "\n".join([f"- {t}" for t in tecnicos]) if tecnicos else "—"
            st.info(f"**👤 Técnicos com acesso liberado:**\n{lista_md}")

            st.markdown("---")

# ============================================================
# BUSCA POR ENDEREÇO
# ============================================================
st.markdown("---")
st.subheader("🧭 Buscar por ENDEREÇO do cliente → 3 sites mais próximos")

with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input("Digite o endereço completo (rua, número, bairro, cidade — RJ de preferência)")
    submitted_endereco = st.form_submit_button("Buscar sites")

endereco_results_ct = st.container()

if submitted_endereco:
    st.session_state["endereco_cliente"] = endereco_cliente
endereco_filtro = st.session_state.get("endereco_cliente", "")

with endereco_results_ct:
    if endereco_filtro:
        with st.spinner("Geocodificando endereço e calculando distâncias..."):
            geo, _ = geocode_address(endereco_filtro)

        if not geo:
            st.error("❌ Endereço não encontrado. Tente incluir número/bairro/cidade. "
                     "Se persistir, refine o endereço ou tente outro próximo.")
        else:
            lat_cli, lon_cli = geo["lat"], geo["lon"]
            st.success("✅ Endereço localizado:")
            st.markdown(f"**{geo['formatted']}**  \n🧭 **Coordenadas**: {lat_cli:.6f}, {lon_cli:.6f}")

            base = df.dropna(subset=["lat","lon"]).copy()
            if base.empty:
                st.warning("⚠️ Nenhuma ERB na base possui coordenadas válidas.")
            else:
                base["dist_km_linear"] = haversine_km(lat_cli, lon_cli, base["lat"].values, base["lon"].values)

                # 1) Top3 normal
                top3 = base.nsmallest(3, "dist_km_linear").copy()

                # 2) Capacitado mais próximo (se houver)
                base_cap = base[base["_is_capacitado"] == True].copy()
                forced_cap_row = None
                if not base_cap.empty:
                    idx_min_cap = base_cap["dist_km_linear"].idxmin()
                    forced_cap_row = base_cap.loc[[idx_min_cap]].copy()

                # 3) Garantir inclusão do capacitado mais próximo
                if forced_cap_row is not None:
                    if forced_cap_row.iloc[0]["sigla"] not in top3["sigla"].astype(str).tolist():
                        union_df = pd.concat([top3, forced_cap_row], ignore_index=True)
                        union_df = union_df.sort_values("dist_km_linear", ascending=True)
                        union_df = union_df.drop_duplicates(subset=["sigla"], keep="first")
                        if len(union_df) > 3:
                            sigla_cap = forced_cap_row.iloc[0]["sigla"]
                            first3 = union_df.head(3)
                            if sigla_cap not in first3["sigla"].astype(str).tolist():
                                union_df = pd.concat([union_df.head(2), forced_cap_row], ignore_index=True)
                                union_df = union_df.drop_duplicates(subset=["sigla"], keep="first")
                                union_df = union_df.sort_values("dist_km_linear", ascending=True)
                        top3 = union_df.head(3).reset_index(drop=True)
                    else:
                        top3 = top3.sort_values("dist_km_linear", ascending=True).reset_index(drop=True)
                else:
                    top3 = top3.sort_values("dist_km_linear", ascending=True).reset_index(drop=True)

                # OSRM
                dm_out, dm_dbg = osrm_table(
                    lat_cli, lon_cli,
                    [(float(r["lat"]), float(r["lon"])) for _, r in top3.iterrows()]
                )
                if dm_out and len(dm_out) == len(top3) and (dm_dbg.get("status") in ("Ok","OK",None)):
                    top3["dist_rodov_text"] = [x["distance_text"] for x in dm_out]
                    top3["duracao_text"]    = [x["duration_text"] for x in dm_out]
                    top3["duracao_s"]       = [x["duration_s"] for x in dm_out]
                else:
                    top3["dist_rodov_text"] = pd.NA
                    top3["duracao_text"]    = pd.NA
                    top3["duracao_s"]       = pd.NA

                st.markdown("### 📍 3 sites mais próximos (priorizando o capacitado mais próximo)")
                mostrar_cols = [c for c in [
                    "sigla","nome","detentora","endereco","lat","lon",
                    "capacitado","dist_km_linear","dist_rodov_text","duracao_text"
                ] if c in top3.columns]
                st.dataframe(
                    top3[mostrar_cols].assign(dist_km_linear=lambda d: d["dist_km_linear"].round(3)),
                    use_container_width=True
                )

                # Cartões
                for _, row in top3.iterrows():
                    erb_lat, erb_lon = float(row["lat"]), float(row["lon"])
                    maps_erb = f"https://www.google.com/maps/search/?api=1&query={erb_lat},{erb_lon}"
                    rota = f"https://www.google.com/maps/dir/?api=1&origin={lat_cli},{lon_cli}&destination={erb_lat},{erb_lon}&travelmode=driving"

                    dist_rodov_text = fmt_na(row.get("dist_rodov_text"))
                    duracao_text    = fmt_na(row.get("duracao_text"))
                    cap_badge       = capacitado_badge(row.get("capacitado"))

                    title = f"**{row.get('sigla', '—')} — {row.get('nome', '—')}**"
                    meta = (
                        f"🗺️ Linha reta: **{row['dist_km_linear']:.3f} km**  \n"
                        f"🚗 Rota: {dist_rodov_text}  \n"
                        f"⏱️ Tempo: {duracao_text}  \n"
                        f"📌 Coords: {erb_lat:.6f}, {erb_lon:.6f}  \n"
                        f"🧰 {cap_badge}"
                    )
                    st.markdown(title + "  \n" + meta)
                    cols = st.columns(2)
                    with cols[0]:
                        st.link_button("🗺️ Ver no Google Maps", maps_erb, type="primary")
                    with cols[1]:
                        st.link_button("🚗 Traçar rota a partir do cliente", rota)
                    st.markdown("---")

st.caption("❤️ Desenvolvido por Raphael Robles - Stay hungry, stay foolish ! 🚀")
 

























































