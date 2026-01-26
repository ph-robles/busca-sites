
==========================================================
# 📡 Endereços dos Sites RJ — Versão OTIMIZADA e ESTÁVEL (+ busca por endereço)
# - Lê aba "enderecos" com colunas reais da sua planilha
# - Busca por SIGLA (como antes)
# - Técnicos (aba "acessos") com status ok (como antes)
# - Link para Google Maps logo abaixo do título do site (como antes)
# - Técnicos em caixa de destaque (st.info), um por linha (como antes)
# - NOVO: Caixa de busca por ENDEREÇO → 3 ERBs mais próximas (Haversine)
# - Sem filtros extras e sem diagnóstico
# ============================================================

import streamlit as st
import pandas as pd
import unicodedata
import math
import time
import requests
import numpy as np

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ------------------------------------------------------------
# Auxiliares
# ------------------------------------------------------------
def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Distância Haversine em km entre dois pontos (pode receber arrays para lat2/lon2).
    """
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
# Geocodificação (Nominatim / OpenStreetMap)
# ------------------------------------------------------------
# Bounding box aproximado do RJ para "puxar" resultados corretos:
RJ_VIEWBOX = (-43.8, -23.1, -43.0, -22.7)  # (min_lon, min_lat, max_lon, max_lat)

@st.cache_data(show_spinner=False, ttl=3600)  # cacheia por 1h
def geocode_nominatim(address: str):
    """
    Geocodifica um endereço com Nominatim (OpenStreetMap) e viés BR/RJ.
    Retorna dict {lat, lon, display_name} ou None se não achar.
    """
    if not address or not address.strip():
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
        "countrycodes": "br",
        "accept-language": "pt-BR",
        # viés RJ
        "viewbox": f"{RJ_VIEWBOX[0]},{RJ_VIEWBOX[1]},{RJ_VIEWBOX[2]},{RJ_VIEWBOX[3]}",
        "bounded": 1,
    }
    headers = {
        # Defina um user-agent identificável (idealmente com seu e-mail/site de contato).
        "User-Agent": "busca-sites-b2b/1.0 (contato: raphael@exemplo.com)"
    }
    try:
        # Respeito básico à política de uso (evita flood)
        time.sleep(1.0)
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        item = data[0]
        return {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "display_name": item.get("display_name", address),
        }
    except Exception:
        return None

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
    """
    Detecção simples por substring: procura o último município mencionado no campo 'nome'.
    É chamada apenas após filtrar por SIGLA (1 ou poucas linhas), então é leve.
    """
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

# -------------------- NOVO: BUSCA POR ENDEREÇO -----------------------
st.markdown("---")
st.subheader("🧭 Buscar por ENDEREÇO do cliente → 3 ERBs mais próximas")

with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input(
        "Digite o endereço completo (rua, número, bairro, cidade) — preferencialmente no RJ"
    )
    submitted_endereco = st.form_submit_button("Buscar ERBs")

if submitted_endereco:
    st.session_state["endereco_cliente"] = endereco_cliente

endereco_filtro = st.session_state.get("endereco_cliente", "")

# Quando houver endereço, geocodificar e calcular top-3
if endereco_filtro:
    with st.spinner("Geocodificando endereço e calculando distâncias..."):
        geo = geocode_nominatim(endereco_filtro)

    if not geo:
        st.error("❌ Endereço não encontrado. Tente ser mais específico (ex.: número, bairro, cidade).")
    else:
        lat_cli, lon_cli = geo["lat"], geo["lon"]
        st.success("✅ Endereço localizado:")
        st.markdown(
            f"**{geo['display_name']}**  \n"
            f"🧭 **Coordenadas**: {lat_cli:.6f}, {lon_cli:.6f}"
        )

        # Filtra apenas linhas com coordenadas válidas
        base = df.dropna(subset=["lat", "lon"]).copy()
        if base.empty:
            st.warning("⚠️ Nenhuma ERB na planilha possui coordenadas válidas.")
        else:
            # Distâncias com Haversine (vetorizado)
            base["dist_km"] = haversine_km(lat_cli, lon_cli, base["lat"].values, base["lon"].values)
            top3 = base.nsmallest(3, "dist_km").copy()

            st.markdown("### 📍 3 ERBs mais próximas")
            mostrar_cols = [c for c in ["sigla", "nome", "detentora", "endereco", "lat", "lon", "dist_km"] if c in top3.columns]
            st.dataframe(
                top3[mostrar_cols].assign(dist_km=lambda d: d["dist_km"].round(3)),
                use_container_width=True
            )

            # Cartões com links úteis (Mapa e Rota)
            for i, row in top3.iterrows():
                erb_lat, erb_lon = float(row["lat"]), float(row["lon"])
                maps_erb = f"https://www.google.com/maps/search/?api=1&query={erb_lat},{erb_lon}"
                rota = f"https://www.google.com/maps/dir/?api=1&origin={lat_cli},{lon_cli}&destination={erb_lat},{erb_lon}&travelmode=driving"

                st.markdown(
                    f"**{row.get('sigla', '—')} — {row.get('nome', '—')}**  \n"
                    f"🗺️ Distância: **{row['dist_km']:.3f} km**  \n"
                    f"📌 Coords: {erb_lat:.6f}, {erb_lon:.6f}"
                )
                cols = st.columns(2)
                with cols[0]:
                    st.link_button("🗺️ Ver ERB no Google Maps", maps_erb, type="primary")
                with cols[1]:
                    st.link_button("🚗 Traçar rota (origem = endereço do cliente)", rota)
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
    # Detectar cidade apenas nas linhas filtradas (rápido)
    df_f["cidade"] = df_f["nome"].apply(detectar_cidade)

    st.success(f"🔎 {len(df_f)} site(s) encontrado(s).")

    st.dataframe(
        df_f[["sigla", "cidade", "detentora", "nome", "endereco", "lat", "lon"]],
        use_container_width=True
    )

    # Título geral
    st.markdown("### 📍 Detalhes do(s) site(s) encontrado(s)")

    def tecnicos_por_sigla(sig: str):
        if ACESSOS_OK is None or ACESSOS_OK.empty:
            return []
        temp = ACESSOS_OK[ACESSOS_OK["sigla"].astype(str).str.upper() == str(sig).upper()]
        return sorted(temp["tecnico"].dropna().unique().tolist())

    for _, row in df_f.iterrows():
        # Título do site
        st.markdown(f"**{row['sigla']} — {row['nome']}**")

        # Botão do Google Maps logo abaixo do título
        if pd.notna(row.get("lat")) and pd.notna(row.get("lon")):
            url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.link_button("🗺️ Ver no Google Maps", url, type="primary")

        # Campos do site
        det = row["detentora"] if pd.notna(row["detentora"]) else "—"
        st.markdown(
            f"🏙️ **Cidade:** {row.get('cidade') or '—'}  \n"
            f"🏢 **Detentora:** {det}  \n"
            f"📌 **Endereço:** {row['endereco']}"
        )

        # Técnicos em caixa de destaque, um por linha
        tecnicos = tecnicos_por_sigla(row["sigla"])
        if tecnicos:
            lista_md = "\n".join([f"- {t}" for t in tecnicos])
        else:
            lista_md = "—"

        st.info(f"**👤 Técnicos com acesso liberado:**\n{lista_md}")

        st.markdown("---")

st.caption("❤️ Desenvolvido por Raphael Robles - Stay hungry, stay foolish ! 🚀")

























