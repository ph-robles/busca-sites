# ============================================================
# 📡 Endereços dos Sites RJ — Versão OTIMIZADA e ESTÁVEL
# - Lê aba "enderecos" com colunas reais da sua planilha
# - Busca por SIGLA
# - Técnicos (aba "acessos") com status ok
# - Link para Google Maps logo abaixo do título do site
# - Técnicos em caixa de destaque (st.info), um por linha
# - Sem filtros extras e sem diagnóstico
# ============================================================

import streamlit as st
import pandas as pd
import unicodedata

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

with st.form("form_sigla", clear_on_submit=False):
    sigla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

# ------------------------------------------------------------
# Filtro
# ------------------------------------------------------------
if sigla_filtro:
    df_f = df[df["sigla"].astype(str).str.upper() == str(sigla_filtro).upper()].copy()
else:
    df_f = pd.DataFrame()

# ------------------------------------------------------------
# Resultado
# ------------------------------------------------------------
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



st.caption("Feito com ❤️ em Streamlit — Dev Raphael Robles 🚀")























