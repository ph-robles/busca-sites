
import streamlit as st
import pandas as pd
import unicodedata


# ---------------------------------------
# CONFIG
# ---------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")


# ---------------------------------------
# AUX
# ---------------------------------------
def strip_accents(s):
    if not isinstance(s, str):
        return s
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------
# CARREGAR PLANILHA PRINCIPAL
# ---------------------------------------
@st.cache_data(show_spinner=False)
def carregar_dados():
    df = pd.read_excel(
        "enderecos.xlsx",
        sheet_name="enderecos",  # ABA REAL DA SUA PLANILHA
        engine="openpyxl",
    )

    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(
        columns={
            "sigla_da_torre": "sigla",
            "nome_da_torre": "nome",
            "endereço": "endereco",
            "latitude": "lat",
            "longitude": "lon",
        }
    )

    # normalização
    for col in ["sigla", "nome", "endereco"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # coordenadas
    for col in ["lat", "lon"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", pd.NA)
                .astype(float)
            )

    if "detentora" not in df.columns:
        df["detentora"] = pd.NA

    return df


# ---------------------------------------
# CARREGAR ACESSOS OK
# ---------------------------------------
@st.cache_data(show_spinner=False)
def carregar_acessos_ok():
    try:
        acc = pd.read_excel("enderecos.xlsx", sheet_name="acessos", engine="openpyxl")
    except:
        return None

    acc.columns = acc.columns.str.strip().str.lower()

    if "tecnico" not in acc.columns:
        for alt in ["técnico", "colaborador", "nome_tecnico"]:
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

    for c in ["sigla", "tecnico", "status"]:
        acc[c] = acc[c].astype(str).strip()

    def norm(x):
        return strip_accents(str(x)).lower()

   "Campos dos Goytacazes", "Cantagalo", "Carapebus",
    "Cardoso Moreira", "Carmo", "Casimiro de Abreu", "Conceição de Macabu",
    "Cordeiro", "Duas Barras", "Duque de Caxias", "Engenheiro Paulo de Frontin",
    " Sul", "Parati", "Paty do Alferes",
    "Petrópolis", "Pinheiral", "Piraí", "Porciúncula", "Porto Real", "Quatis",
    "Queimados", "Quissamã", "Resende", "Rio Bonito", "Rio Claro",
    "Rio das Flores", "Rio das Ostras", "Rio de Janeiro",
    "Santa Maria Madalena", "Santo Antônio de Pádua", "São Fidélis",
    "São Francisco de Itabapoana", "São Gonçalo", "São João da Barra",
    "São João de Meriti", "São José de Ubá", "São José do Vale do Rio Preto",
    "São Pedro da Aldeia", "São Sebastião do Alto", "Sapucaia", "Saquarema",
    "Seropédica", "Silva Jardim", "Sumidouro", "Tanguá", "Teresópolis",
   ():
        if key in base:
            ultimo = city
    return ultimo


# ---------------------------------------
# CARREGAMENTO
# ---------------------------------------
df = carregar_dados()
ACESSOS_OK = carregar_acessos_ok()


# ---------------------------------------
# UI
# ---------------------------------------
st.title("📡 Endereços dos Sites RJ")

if st.button("🔄 Atualizar dados (limpar cache)"):
    st.cache_data.clear()
    st.experimentalla = st.text_input("🔍 Buscar por SIGLA:")
    submitted = st.form_submit_button("OK")

if submitted:
    st.session_state["sigla"] = sigla

sigla_filtro = st.session_state.get("sigla", "")

if sigla_filtro:
    df_f = df[df["sigla"].str.upper() == sigla_filtro.upper()]
else:
    df_f = pd.DataFrame()

if df_f.empty:
    st.warning("⚠️ Nenhum site encontrado.")
else:
    df_f["cidade"] = df_f["nome"].apply(detectar_cidade)

    st.success(f"🔎 {len(df_f)} site(s) encontrado(s).")

    st.dataframe(
        df_f[["sigla", "cidade", "detentora", "nome", "endereco", "lat", "lon"]],
        use_container_width=True,
    )

    st.markdown("### 📍 Detalhes dos sites encontrados")

    def tecnicos(sig):
        if ACESSOS_OK is None:
            return []
        t = ACESSOS_OK[ACESSOS_OK["sigla"].str.upper() == sig.upper()]
        return sorted(t["tecnico"].dropna().unique().tolist())

    for _, row in df_f.iterrows():
        det = row["detentora"] if pd.notna(row["detentora"]) else "—"
        tecs = tecnicos(row["sigla"])

        st.markdown(
            f"**{row['sigla']} — {row['nome']}**\n"
            f"🏙️ Cidade: {row['cidade'] or '—'}\n"
            f"🏢 Detentora: {det}\n"
            f"👤 Técnicos: {', '.join(tecs) if tecs else '—'}\n"
            f"📌 Endereço: {row['endereco']}"
        )

        if pd.notna(row["lat"]) and pd.notna(row["lon"]):
            url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.link_button("🗺️ Ver no Google Maps", url, type="primary")

        st.markdown("---")



st.caption("Feito com ❤️ em Streamlit — Dev Raphael Robles 🚀")



















