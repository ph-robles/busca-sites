

# ============================================================
# 📡 Endereços dos Sites RJ — Google Geocoding + Distance Matrix + Cache
# - Mantém todo o comportamento atual
# - Substitui Nominatim por Google Geocoding API
# - Adiciona tempo/distância por rota (Distance Matrix API)
# - Cache para reduzir custos e latência
# ============================================================

import streamlit as st
import pandas as pd
import unicodedata
import time
import requests
import numpy as np

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ------------------------------------------------------------
# Secrets / Chave da Google
# ------------------------------------------------------------
API_KEY = st.secrets.get("GOOGLE_MAPS_API_KEY", "").strip()

if not API_KEY:
    st.warning(
        "⚠️ Configure sua chave em Settings → Secrets como `GOOGLE_MAPS_API_KEY`. "
        "Enquanto isso, a busca por endereço/rota ficará indisponível."
    )

# ------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------
def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def haversine_km(lat1, lon1, lat2, lon2):
    """Distância Haversine em km (aceita arrays em lat2/lon2)."""
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
# GOOGLE GEOCODING API (Endereço -> Coordenadas)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60*60)  # 1h de cache por endereço
def geocode_google(address: str):
    """
    Retorna: {'lat': float, 'lon': float, 'formatted': str} ou None
    Usa Geocoding API (Google).
    """
    if not API_KEY or not address or not address.strip():
        return None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "region": "br",        # favorece resultados no Brasil
        "language": "pt-BR",   # nomes em pt-BR quando possível
        "key": API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        res = data["results"][0]
        loc = res["geometry"]["location"]
        return {
            "lat": float(loc["lat"]),
            "lon": float(loc["lng"]),
            "formatted": res.get("formatted_address") or address
        }
    except Exception:
        return None

# ------------------------------------------------------------
# GOOGLE DISTANCE MATRIX (origem -> destinos) por carro
# ------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=15*60)  # 15 min de cache por conjunto origem/destinos
def distance_matrix_google(origin_lat, origin_lon, dests, mode="driving"):
    """
    Calcula tempo/distância dirigindo entre origem e destinos.
    dests: lista de tuplas (lat, lon)
    Retorna lista de dicts com 'distance_m', 'distance_text', 'duration_s', 'duration_text'
    na mesma ordem de dests. Se falhar, retorna lista vazia.
    """
    if not API_KEY or not dests:
        return []

    origins = f"{origin_lat},{origin_lon}"
    destinations = "|".join([f"{lat},{lon}" for (lat, lon) in dests])

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origins,
        "destinations": destinations,
        "mode": mode,
        "language": "pt-BR",
        "key": API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            return []

        rows = data.get("rows", [])
        if not rows:
            return []

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
        return out
    except Exception:
        return []

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
    st.experimental_rerun()

# -------------------- BUSCA POR SIGLA (existente) --------------------
with st.form("form_sigla", clear_on_submit=False):
    sigla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

# -------------------- NOVO: BUSCA POR ENDEREÇO (Google) -------------
st.markdown("---")
st.subheader("🧭 Buscar por ENDEREÇO do cliente → 3 ERBs mais próximas")

with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input(
        "Digite o endereço completo (rua, número, bairro, cidade — RJ de preferência)"
    )
    submitted_endereco = st.form_submit_button("Buscar ERBs")

if submitted_endereco:
    st.session_state["endereco_cliente"] = endereco_cliente

endereco_filtro = st.session_state.get("endereco_cliente", "")

if endereco_filtro:
    if not API_KEY:
        st.error("❌ Falta configurar `GOOGLE_MAPS_API_KEY` em Secrets para usar a busca por endereço.")
    else:
        with st.spinner("Geocodificando endereço (Google) e calculando distâncias..."):
            geo = geocode_google(endereco_filtro)

        if not geo:
            st.error("❌ Endereço não encontrado. Tente ser mais específico (número/bairro/cidade).")
        else:
            lat_cli, lon_cli = geo["lat"], geo["lon"]
            st.success("✅ Endereço localizado:")
            st.markdown(
                f"**{geo['formatted']}**  \n"
                f"🧭 **Coordenadas**: {lat_cli:.6f}, {lon_cli:.6f}"
            )

            # Filtra apenas linhas com coordenadas válidas
            base = df.dropna(subset=["lat", "lon"]).copy()
            if base.empty:
                st.warning("⚠️ Nenhuma ERB na planilha possui coordenadas válidas.")
            else:
                # Distância geodésica (linha reta) para ranking inicial
                base["dist_km_linear"] = haversine_km(lat_cli, lon_cli, base["lat"].values, base["lon"].values)
                top3 = base.nsmallest(3, "dist_km_linear").copy()

                # Chama Distance Matrix para tempo/distância por rota
                destinos = [(float(r["lat"]), float(r["lon"])) for _, r in top3.iterrows()]
                dm = distance_matrix_google(lat_cli, lon_cli, destinos, mode="driving")

                # Anexa resultados (se disponíveis)
                if dm and len(dm) == len(top3):
                    top3 = top3.reset_index(drop=True)
                    top3["dist_rodov_text"] = [x["distance_text"] for x in dm]
                    top3["duracao_text"] = [x["duration_text"] for x in dm]
                    top3["duracao_s"] = [x["duration_s"] for x in dm]
                else:
                    top3["dist_rodov_text"] = pd.NA
                    top3["duracao_text"] = pd.NA
                    top3["duracao_s"] = pd.NA

                st.markdown("### 📍 3 ERBs mais próximas (ranking por linha reta, com rota quando disponível)")
                mostrar_cols = [c for c in [
                    "sigla", "nome", "detentora", "endereco", "lat", "lon",
                    "dist_km_linear", "dist_rodov_text", "duracao_text"
                ] if c in top3.columns]
                st.dataframe(
                    top3[mostrar_cols].assign(dist_km_linear=lambda d: d["dist_km_linear"].round(3)),
                    use_container_width=True
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




























