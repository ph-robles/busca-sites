

import re
import unicodedata
import streamlit as st
import pandas as pd

# =========================
# Carregar os dados
# =========================
@st.cache_data(show_spinner=False)
def carregar_dados(caminho: str) -> pd.DataFrame:
    df = pd.read_excel(caminho, engine="openpyxl")

    # Padronizar nomes de colunas
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        'sigla_da_torre': 'sigla',
        'nome_da_torre': 'nome',
        'endereço': 'endereco',
        'latitude': 'lat',
        'longitude': 'lon'
    })

    # Corrigir vírgulas para pontos nas coordenadas e converter para float
    df['lat'] = (
        df['lat']
        .astype(str).str.replace(',', '.', regex=False)
        .str.strip()
        .replace({'': pd.NA})
        .astype(float)
    )
    df['lon'] = (
        df['lon']
        .astype(str).str.replace(',', '.', regex=False)
        .str.strip()
        .replace({'': pd.NA})
        .astype(float)
    )
    return df

df = carregar_dados("enderecos.xlsx")

# =========================
# Funções de extração de cidade (robustas)
# =========================

# Lista de municípios do RJ (92)
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
    "Varre-Sai", "Vassouras", "Volta Redonda"
]

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

MUNICIPIOS_IDX = {strip_accents(n).lower(): n for n in MUNICIPIOS_RJ}

PREPOSICOES_PT = {"de", "da", "das", "do", "dos", "e", "d'", "d’"}

def smart_title_pt(s: str) -> str:
    """Title Case preservando preposições e siglas (ex.: RJ)"""
    if not isinstance(s, str) or not s.strip():
        return s
    tokens = re.split(r"(\s+|-|’|')", s.strip())
    out = []
    for i, tok in enumerate(tokens):
        if re.fullmatch(r"\s+|-|’|'", tok or ""):
            out.append(tok)
            continue
        if re.fullmatch(r"[A-Z]{2,3}", tok or ""):
            out.append(tok)
            continue
        low = tok.lower()
        if i != 0 and low in PREPOSICOES_PT:
            out.append(low)
            continue
        out.append(low.capitalize())
    s2 = "".join(out)
    s2 = re.sub(r"\bD'’", lambda m: "d’" + m.group(1).upper(), s2)
    s2 = re.sub(r"\s+", " ", s2).strip()
    s2 = re.sub(r"\s*-\s*", "-", s2)
    return s2

PALAVRAS_TIPO_LOGRADOURO = {
    "R", "R.", "RUA", "AV", "AV.", "AVENIDA", "AL", "AL.", "ALAMEDA", "TRAV", "TRAV.", "TRAVESSA",
    "ROD", "ROD.", "RODOVIA", "ESTR", "ESTR.", "ESTRADA", "LGO", "LARGO", "PÇA", "PCA", "PRAÇA"
}

def parece_logradouro(s: str) -> bool:
    if not isinstance(s, str):
        return False
    t = strip_accents(s).upper()
    if " COM " in t or " C/ " in t or " R." in t or " AV." in t:
        return True
    inicio = t.split()[0] if t.split() else ""
    if inicio in PALAVRAS_TIPO_LOGRADOURO:
        return True
    if sum(ch.isdigit() for ch in t) >= 3 and "-" not in s:
        return True
    return False

UF_PATTERN = r"(RJ|SP|MG|ES|PR|SC|RS|BA|PE|CE|PA|AM|GO|MT|MS|DF)"

def extrair_cidade(nome: str) -> str | None:
    """Extrai cidade priorizando 'CIDADE - ...'; fallback: último município presente no texto; evita logradouro."""
    if not isinstance(nome, str) or not nome.strip():
        return None
    s = nome.strip()

    # 1) Padrão "CIDADE - RESTO"
    if "-" in s:
        parte_inicial = re.split(r"\s*-\s*", s, maxsplit=1)[0].strip()
        parte_inicial = re.sub(rf"[\s/,-]*{UF_PATTERN}$", "", parte_inicial, flags=re.IGNORECASE).strip()
        m = re.match(r"^([A-Za-zÀ-ÖØ-öø-ÿ\s\-’']+)", parte_inicial)
        if m:
            cand = m.group(1).strip()
            if len(cand) >= 2:
                cand_norm = smart_title_pt(cand)
                key = strip_accents(cand_norm).lower()
                if key in MUNICIPIOS_IDX:
                    return MUNICIPIOS_IDX[key]
                return cand_norm  # pode ser cidade válida mesmo se não bater com a lista

    # 2) Sem hífen (ou não bateu): evitar endereços
    if parece_logradouro(s):
        return None

    # 3) Procurar o ÚLTIMO município do RJ que apareça no texto (cobre "DGV-... VALENÇA")
    s_key = strip_accents(s).lower()
    ultimo, pos = None, -1
    for key_norm, nome_mun in MUNICIPIOS_IDX.items():
        padrao = r"(?:^|\b|\s)" + re.escape(key_norm) + r"(?:$|\b|\s|,|-|/)"
        for m2 in re.finditer(padrao, s_key):
            if m2.start() > pos:
                pos = m2.start()
                ultimo = nome_mun
    return ultimo

# Aplicar ao DataFrame + aliases úteis
df['cidade'] = df['nome'].apply(extrair_cidade)
ALIASES = {
    "Seropedica": "Seropédica",
    "Armacao dos Buzios": "Armação dos Búzios",
    "Niteroi": "Niterói",
    "Sao Goncalo": "São Gonçalo",
    "Rio De Janeiro": "Rio de Janeiro",
}
df['cidade'] = df['cidade'].replace(ALIASES)

# =========================
# UI
# =========================
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")
st.title("📡 Endereços dos Sites RJ")

# ---- Filtros (3 colunas) ----
col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

with col1:
    # Formulário para a busca de SIGLA + botão OK
    with st.form("form_sigla", clear_on_submit=False):
        sigla_input_val = st.text_input("🔍 Buscar por sigla:", value=st.session_state.get("sigla_input", ""))
        ok_busca = st.form_submit_button("OK")
        if ok_busca:
            st.session_state["sigla_commit"] = sigla_input_val
            st.session_state["sigla_input"] = sigla_input_val

    # Valor de filtro efetivo (só muda ao clicar OK)
    sigla_filtro = st.session_state.get("sigla_commit", "")

with col2:
    somente_reconhecida = st.checkbox("✅ Somente entradas com cidade reconhecida", value=True)

    # Select de cidade: SEM None e ordenado
    cidades_unicas = sorted(df['cidade'].dropna().unique().tolist())
    cidade_opcao = st.selectbox("🏙️ Filtrar por Localidade:", options=["Todas"] + cidades_unicas)

with col3:
    # Select de nome da torre (lista completa; pode ser dinâmica por cidade se desejar)
    nomes_unicos = sorted(df['nome'].dropna().unique().tolist())
    nome_opcao = st.selectbox("📍 Filtrar por nome da torre:", options=["Todas"] + nomes_unicos)

# =========================
# Aplicar filtros
# =========================
df_filtrado = df.copy()

if sigla_filtro:
    df_filtrado = df_filtrado[df_filtrado['sigla'].astype(str).str.upper() == str(sigla_filtro).upper()]

if somente_reconhecida:
    df_filtrado = df_filtrado[df_filtrado['cidade'].notna()]

if cidade_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_opcao]

if nome_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado['nome'] == nome_opcao]

# =========================
# Resultados (SEM MAPA)
# =========================
if df_filtrado.empty:
    st.warning("⚠️ Nenhum site encontrado com os filtros selecionados.")
else:
    st.success(f"🔎 {len(df_filtrado)} Site(s) encontrado(s).")

    # Tabela com resultados
    st.dataframe(
        df_filtrado[['sigla', 'cidade', 'nome', 'endereco', 'lat', 'lon']],
        use_container_width=True
    )

    # Detalhes com link para o Google Maps
    st.markdown("### 📍 Detalhes dos sites encontrados")
    for _, row in df_filtrado.iterrows():
        maps_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
        st.markdown(
            f"**{row['sigla']} - {row['nome']}**  \n"
            f"🏙️ **Cidade:** {row.get('cidade') or '—'}  \n"
            f"📌 **Endereço:** {row['endereco']}"
        )
        st.link_button("🗺️ Ver no Google Maps", maps_url, type="primary")
        st.markdown("---")




