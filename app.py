
import re
import unicodedata
import streamlit as st
import pandas as pd

# ----------------------------------------
# Configuração de página
# ----------------------------------------
st.set_page_config(page_title="Endereços dos Sites RJ", page_icon="📡", layout="wide")

# ----------------------------------------
# Utilitários
# ----------------------------------------
def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

# ----------------------------------------
# Leitura do Excel - Planilha principal
# ----------------------------------------
@st.cache_data(show_spinner=False)
def carregar_dados_principais(caminho: str) -> pd.DataFrame:
    df = pd.read_excel(caminho, engine="openpyxl")

    # Padronizar nomes de colunas
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(
        columns={
            "sigla_da_torre": "sigla",
            "nome_da_torre": "nome",
            "endereço": "endereco",
            "latitude": "lat",
            "longitude": "lon",
            # variações possíveis para detentora
            "nome_da_detentora": "detentora",
            "operadora": "detentora",
            "proprietaria": "detentora",
        }
    )

    # Coordenadas: vírgula -> ponto e conversão
    df["lat"] = (
        df["lat"].astype(str).str.replace(",", ".", regex=False).str.strip().replace({"": pd.NA}).astype(float)
    )
    df["lon"] = (
        df["lon"].astype(str).str.replace(",", ".", regex=False).str.strip().replace({"": pd.NA}).astype(float)
    )

    # Colunas garantidas
    if "detentora" not in df.columns:
        df["detentora"] = pd.NA
    df["detentora"] = df["detentora"].astype("string").str.strip()

    # Normaliza campos-chave
    for col in ["sigla", "nome", "endereco"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    return df

# ----------------------------------------
# Leitura do Excel - Aba "acessos" (status == ok)
# ----------------------------------------
@st.cache_data(show_spinner=False)
def carregar_acessos_ok(caminho: str) -> pd.DataFrame | None:
    """
    Lê a aba 'acessos' e retorna somente linhas com status == 'ok',
    normalizando colunas ('sigla', 'tecnico', 'status').
    """
    try:
        xls = pd.ExcelFile(caminho, engine="openpyxl")
        sheet = next((s for s in xls.sheet_names if s.strip().lower() == "acessos"), None)
        if not sheet:
            return None

        acc = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
        acc.columns = acc.columns.str.strip().str.lower()

        # Normaliza colunas esperadas
        if "tecnico" not in acc.columns:
            for alt in ["técnico", "nome_tecnico", "nome do tecnico", "colaborador"]:
                if alt in acc.columns:
                    acc = acc.rename(columns={alt: "tecnico"})
                    break

        if "sigla" not in acc.columns:
            for alt in ["sigla_da_torre", "site", "torre"]:
                if alt in acc.columns:
                    acc = acc.rename(columns={alt: "sigla"})
                    break

        # Garantia mínima
        if "sigla" not in acc.columns or "tecnico" not in acc.columns:
            return None

        if "status" not in acc.columns:
            acc["status"] = "ok"

        # Tipos e limpeza
        for c in set(acc.columns) & {"sigla", "tecnico", "status"}:
            acc[c] = acc[c].astype("string").str.strip()

        # Filtra apenas status ok (case-insensitive e sem acento)
        def norm(x: str) -> str:
            return "".join(ch for ch in unicodedata.normalize("NFD", str(x)) if unicodedata.category(ch) != "Mn").lower()

        acc = acc[acc["status"].apply(norm) == "ok"]

        # Remove vazios
        acc = acc[
            acc["sigla"].notna()
            & (acc["sigla"] != "")
            & acc["tecnico"].notna()
            & (acc["tecnico"] != "")
        ]

        return acc.reset_index(drop=True)
    except Exception:
        return None

# ----------------------------------------
# Carregar dados
# ----------------------------------------
CAMINHO = "enderecos.xlsx"
df = carregar_dados_principais(CAMINHO)
ACESSOS_OK = carregar_acessos_ok(CAMINHO)

# ----------------------------------------
# Extração robusta de "cidade"
# ----------------------------------------
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
PREPOSICOES_PT = {"de", "da", "das", "do", "dos", "e", "d'", "d’"}
UF_PATTERN = r"(RJ|SP|MG|ES|PR|SC|RS|BA|PE|CE|PA|AM|GO|MT|MS|DF)"

def smart_title_pt(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return s
    tokens = re.split(r"(\s+|-|’|')", s.strip())
    out = []
    for i, tok in enumerate(tokens):
        if re.fullmatch(r"\s+|-|’|'", tok or ""):
            out.append(tok); continue
        if re.fullmatch(r"[A-Z]{2,3}", tok or ""):
            out.append(tok); continue
        low = tok.lower()
        if i != 0 and low in PREPOSICOES_PT:
            out.append(low); continue
        out.append(low.capitalize())
    s2 = "".join(out)
    s2 = re.sub(r"\bD'’", lambda m: "d’" + m.group(1).upper(), s2)
    s2 = re.sub(r"\s+", " ", s2).strip()
    s2 = re.sub(r"\s*-\s*", "-", s2)
    return s2

PALAVRAS_TIPO_LOGRADOURO = {
    "R", "R.", "RUA", "AV", "AV.", "AVENIDA", "AL", "AL.", "ALAMEDA", "TRAV", "TRAV.", "TRAVESSA",
    "ROD", "ROD.", "RODOVIA", "ESTR", "ESTR.", "ESTRADA", "LGO", "LARGO", "PÇA", "PCA", "PRAÇA",
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

def extrair_cidade(nome: str) -> str | None:
    if not isinstance(nome, str) or not nome.strip():
        return None
    s = nome.strip()

    # Prioriza "CIDADE - ..."
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
                return cand_norm

    # Evita logradouros
    if parece_logradouro(s):
        return None

    # Fallback: último município citado no texto
    s_key = strip_accents(s).lower()
    ultimo, pos = None, -1
    for key_norm, nome_mun in MUNICIPIOS_IDX.items():
        padrao = r"(?:^|\b|\s)" + re.escape(key_norm) + r"(?:$|\b|\s|,|-|/)"
        for m2 in re.finditer(padrao, s_key):
            if m2.start() > pos:
                pos = m2.start()
                ultimo = nome_mun
    return ultimo

df["cidade"] = df["nome"].apply(extrair_cidade)
ALIASES = {
    "Seropedica": "Seropédica",
    "Armacao dos Buzios": "Armação dos Búzios",
    "Niteroi": "Niterói",
    "Sao Goncalo": "São Gonçalo",
    "Rio De Janeiro": "Rio de Janeiro",
}
df["cidade"] = df["cidade"].replace(ALIASES)

# ----------------------------------------
# UI - Filtros
# ----------------------------------------
st.title("📡 Endereços dos Sites RJ")

col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

with col1:
    with st.form("form_sigla", clear_on_submit=False):
        sigla_input_val = st.text_input("🔍 Buscar por sigla:", value=st.session_state.get("sigla_input", ""))
        ok_busca = st.form_submit_button("OK")
        if ok_busca:
            st.session_state["sigla_commit"] = sigla_input_val
            st.session_state["sigla_input"] = sigla_input_val
    sigla_filtro = st.session_state.get("sigla_commit", "")

with col2:
    somente_reconhecida = st.checkbox("✅ Somente entradas com cidade reconhecida", value=True)
    cidades_unicas = sorted(df["cidade"].dropna().unique().tolist())
    cidade_opcao = st.selectbox("🏙️ Filtrar por Localidade:", options=["Todas"] + cidades_unicas)

with col3:
    nomes_unicos = sorted(df["nome"].dropna().unique().tolist())
    nome_opcao = st.selectbox("📍 Filtrar por nome da torre:", options=["Todas"] + nomes_unicos)

# ----------------------------------------
# Aplicar filtros
# ----------------------------------------
df_filtrado = df.copy()

if sigla_filtro:
    df_filtrado = df_filtrado[df_filtrado["sigla"].astype(str).str.upper() == str(sigla_filtro).upper()]

if somente_reconhecida:
    df_filtrado = df_filtrado[df_filtrado["cidade"].notna()]

if cidade_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado["cidade"] == cidade_opcao]

if nome_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado["nome"] == nome_opcao]

# ----------------------------------------
# Técnicos por SIGLA (usando ACESSOS_OK)
# ----------------------------------------
def tecnicos_por_sigla(sigla: str) -> list[str]:
    if ACESSOS_OK is None or ACESSOS_OK.empty:
        return []
    m = ACESSOS_OK[ACESSOS_OK["sigla"].str.upper() == str(sigla).upper()]
    nomes = m["tecnico"].dropna().unique().tolist()
    nomes = [n.strip() for n in nomes if isinstance(n, str) and n.strip()]
    return sorted(set(nomes))

# ----------------------------------------
# Resultados (sem mapa)
# ----------------------------------------
if df_filtrado.empty:
    st.warning("⚠️ Nenhum site encontrado com os filtros selecionados.")
else:
    st.success(f"🔎 {len(df_filtrado)} Site(s) encontrado(s).")

    st.dataframe(
        df_filtrado[["sigla", "cidade", "detentora", "nome", "endereco", "lat", "lon"]],
        use_container_width=True,
    )

    st.markdown("### 📍 Detalhes dos sites encontrados")
    for _, row in df_filtrado.iterrows():
        maps_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"

        detentora_txt = row.get("detentora")
        detentora_fmt = detentora_txt if (isinstance(detentora_txt, str) and detentora_txt.strip()) else "—"

        # Mostra técnicos somente quando houver detentora
        tecnicos_md = ""
        if detentora_fmt != "—":
            nomes = tecnicos_por_sigla(row["sigla"])
            tecnicos_md = "  \n**👤 Técnicos com acesso liberado:**  \n" + (
                "  \n".join(f"- {t}" for t in nomes) if nomes else "—"
            )

        st.markdown(
            f"**{row['sigla']} - {row['nome']}**  \n"
            f"🏙️ **Cidade:** {row.get('cidade') or '—'}  \n"
            f"🏢 **Detentora:** {detentora_fmt}{tecnicos_md}  \n"
            f"📌 **Endereço:** {row['endereco']}"
        )
        st.link_button("🗺️ Ver no Google Maps", maps_url, type="primary")
        st.markdown("---")








