


# ============================================================
# 📡 Endereços dos Sites RJ — Versão OTIMIZADA
# Removido: filtros extras, diagnóstico e cálculos globais pesados.
# Mantido: busca por SIGLA, mapa, técnicos da aba "acessos".
# Cidade é calculada somente após filtrar (muito mais rápido!).
# ============================================================

import re
import unicodedata
import streamlit as st
import pandas as pd

# ------------------------------------------------------------
# Configuração inicial
# ------------------------------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------
def strip_accents(s: str):
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------
# Carregar planilha principal — AGORA MAIS RÁPIDO
# (Lê diretamente a *aba fixa* "dados")
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_dados():
    df = pd.read_excel(
        "enderecos.xlsx",
        sheet_name="dados",        # <- muito mais rápido que scan de abas
        engine="openpyxl"
    )

    df.columns = df.columns.str.strip().str.lower()

    rename_map = {
        "sigla_da_torre": "sigla",
        "nome_da_torre": "nome",
        "endereço": "endereco",
        "latitude": "lat",
        "longitude": "lon",
    }
    df = df.rename(columns=rename_map)

    # Detentora – mapeamento robusto
    ALIAS = [
        "detentora", "nome_da_detentora", "nome detentora", "proprietaria",
        "proprietária", "operadora", "empresa_detentora", "empresa detentora",
        "responsavel_site", "responsável_site", "responsavel", "responsável"
    ]
    for c in df.columns:
        if any(a in c.lower() for a in ALIAS):
            df = df.rename(columns={c: "detentora"})
            break

    # Normalizar colunas
    for col in ["sigla", "nome", "endereco"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Coordenadas com ponto
    for col in ["lat", "lon"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", pd.NA)
                .astype(float)
            )

    if "detentora" not in df.columns:
        df["detentora"] = pd.NA

    return df


# ------------------------------------------------------------
# Carregar aba "acessos" (somente status OK)
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

    if "sigla" not in acc.columns or "tecnico" not in acc.columns:
        return None

    if "status" not in acc.columns:
        acc["status"] = "ok"

    # Normalizar
    for c in ["sigla", "tecnico", "status"]:
        acc[c] = acc[c].astype("string").str.strip()

    # Filtrar apenas status ok
    def norm(x): return strip_accents(str(x)).lower()
    acc = acc[acc["status"].apply(norm) == "ok"]

    return acc.reset_index(drop=True)


# ------------------------------------------------------------
# Tabela e acessos
# ------------------------------------------------------------
df = carregar_dados()
ACESSOS_OK = carregar_acessos_ok()


# ------------------------------------------------------------
# Extrair cidade – agora só é usado após filtrar (MUITO MAIS RÁPIDO)
# ------------------------------------------------------------
MUNICIPIOS_RJ = [
    "Angra dos Reis", "Aperibé", "Araruama", "Areal", "Armação dos Búzios", "Arraial do Cabo",
    "Barra do Piraí", "Barra Mansa", "Belford Roxo", "Bom Jardim", "Bom Jesus do Itabapoana",
    "Cabo Frio", "Cachoeiras de Macacu", "Cambuci", "Campos dos Goytacazes", "Cantagalo",
    "Carapebus", "Cardoso Moreira", "Carmo", "Casimiro de Abreu", "Comendador Levy Gasparian",
    "Conceição de Macabu", "Cordeiro", "Duas Barras", "Duque de Caxias", "Engenheiro Paulo de Frontin",
    "Guapimirim", "Iguaba Grande", "Itaboraí", "Itaguaí", "Italva", "Itaocara", "Itaperuna",
    "Itatiaia", "Japeri", "Laje do Muriaé", "Macaé", "Macuco", "Magé", "Mangaratiba", "Maricá",
    "Mendes", "Mesquita", "Miguel Pereira", "Miracema", "Natividade", "Nilópolis", "Niterói",
    "Nova Friburgo", "Nova Iguaçu", "Paracambi", "Paraíba do Sul", "Parati", "Paty do Alferes",
    "Petrópolis", "Pinheiral", "Piraí", "Porciúncula", "Porto Real", "Quatis", "Queimados", "Quissamã",
    "Resende", "Rio Bonito", "Rio Claro", "Rio das Flores", "Rio das Ostras", "Rio de Janeiro",
    "Santa Maria Madalena", "Santo Antônio de Pádua", "São Fidélis", "São Francisco de Itabapoana",
    "São Gonçalo", "São João da Barra", "São João de Meriti", "São José de Ubá", "São José do Vale do Rio Preto",
    "São Pedro da Aldeia", "São Sebastião do Alto", "Sapucaia", "Saquarema", "Seropédica", "Silva Jardim",
    "Sumidouro", "Tanguá", "Teresópolis", "Trajano de Moraes", "Três Rios", "Valença",
    "Varre-Sai", "Vassouras", "Volta Redonda",
]
MUNICIPIOS_IDX = {strip_accents(n).lower(): n for n in MUNICIPIOS_RJ}


def detectar_cidade(nome):
    """Executa extração de cidade apenas sob demanda (rápido)."""
    if not isinstance(nome, str):
        return None
    base = strip_accents(nome).lower()
    ultimo = None
   .title("📡 Endereços dos Sites RJ")

if st.button("🔄 Atualizar dados (limpar cache)"):
    st.cache_data.clear()
    st.experimental_rerun()

with st.form("form_sigla"):
    sigla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

# ------------------------------------------------------------
# Filtragem rápida
# ------------------------------------------------------------
if sigla_filtro:
    df_f = df[df["sigla"].str.upper() == sigla_filtro.upper()]
else:
    df_f = pd.DataFrame()

# ------------------------------------------------------------
# Exibir resultados
# ------------------------------------------------------------
if df_f.empty:
    st.warning("⚠️ Nenhum site encontrado.")
else:
    # Cidade calculada somente aqui — econômico
    df_f["cidade"] = df_f["nome"].apply(detectar_cidade)

    st.success(f"🔎 {len(df_f)} site(s) encontrado(s).")

    st.dataframe(
        df_f[["sigla", "cidade", "detentora", "nome", "endereco", "lat", "lon"]],
        use_container_width=True
    )

    st.markdown("### 📍 Detalhes")

    def tecnicos(sigla):
        if ACESSOS_OK is None:
            return []
        temp = ACESSOS_OK[ACESSOS_OK["sigla"].str.upper() == sigla.upper()]
        return sorted(temp["tecnico"].dropna().unique().tolist())

    for _, row in df_f.iterrows():
        det = row["detentora"] if pd.notna(row["detentora"]) else "—"
        tecs = tecnicos(row["sigla"])

        st.markdown(
            f"**{row['sigla']} — {row['nome']}**  \n"
            f"🏙️ Cidade: {row['cidade'] or '—'}  \n"
            f"🏢 Detentora: {det}  \n"
            f"👤 Técnicos: {', '.join(tecs) if tecs else '—'}  \n"
            f"📌 Endereço: {row['endereco']}"
        )

        if row["lat"] and row["lon"]:
            url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.link_button("🗺️ Ver no Google Maps", url, type="primary")

        st.markdown("---")

st.caption("Feito com ❤️ em Streamlit — Dev Raphael Robles.")
``














