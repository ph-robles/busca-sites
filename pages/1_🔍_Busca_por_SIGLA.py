import streamlit as st
import pandas as pd
from utils.data_loader import carregar_dados, carregar_acessos
from utils.helpers import normalizar_sigla, levenshtein

st.set_page_config(page_title="Buscar por SIGLA • Site Radar", page_icon="📡", layout="wide")

# ==============================
#   SIDEBAR PREMIUM COMPACTA (BLUR + MOBILE SAFE)
# ==============================
sidebar_style = """
<style>

/* Sidebar geral (desktop) */
[data-testid="stSidebar"] {
    background: rgba(20, 25, 35, 0.55) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 40px;
    width: 240px !important;
}

/* LOGO centralizada */
.sidebar-logo {
    display: flex;
    justify-content: center;
    margin-bottom: 250px;
}

/* ----------------------------
   MODO COMPACTO PARA CELULAR
----------------------------- */
@media (max-width: 760px) {

    /* Sidebar fica mais larga (apenas ajuste solicitado) */
    [data-testid="stSidebar"] {
        width: 280px !important;
        min-width: 136px !important;
        padding-top: 24px;
        padding-left: 6px;
        padding-right: 6px;
    }

    /* A logo se ajusta para 250px (pedido) */
    .sidebar-logo img {
        width: 80px !important;
    }

    /* Conteúdo oculto na sidebar compacta */
    .sidebar-content, .sidebar-text {
        display: none !important;
    }
}

/* ---------------------------------
   ESTILO DOS "CHIPS" DE SUGESTÕES
---------------------------------- */
#chips-scope { margin-top: .25rem; }
#chips-scope div[data-testid="stHorizontalBlock"] { row-gap: .5rem; }
#chips-scope div[data-testid="stButton"] > button {
  border-radius: 9999px;
  padding: .35rem .9rem;
  font-size: 0.92rem;
  line-height: 1rem;
  border: 1px solid rgba(49,51,63,0.25);
  background: rgba(49,51,63,0.04);
  color: inherit;
  cursor: pointer;
  transition: all .15s ease-in-out;
}
#chips-scope div[data-testid="stButton"] > button:hover {
  background: rgba(49,51,63,0.08);
  border-color: rgba(49,51,63,0.4);
  transform: translateY(-1px);
}
#chips-scope div[data-testid="stButton"] > button:active {
  transform: translateY(0px) scale(.98);
}
/* dark mode */
:root .st-dark #chips-scope div[data-testid="stButton"] > button {
  border-color: rgba(250, 250, 250, 0.18);
  background: rgba(250, 250, 250, 0.06);
}
:root .st-dark #chips-scope div[data-testid="stButton"] > button:hover {
  border-color: rgba(250, 250, 250, 0.35);
  background: rgba(250, 250, 250, 0.12);
}
</style>
"""
st.markdown(sidebar_style, unsafe_allow_html=True)

# Sidebar com logo
with st.sidebar:
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    st.image("logo.png", width=300)
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================
#   FUNÇÕES AUXILIARES (LOCAIS)
# ==============================
def _format_coord(x):
    try:
        if pd.isna(x):
            return "—"
        return f"{float(x):.6f}"
    except Exception:
        return "—"

def _gerar_sugestoes(busca_raw: str, candidatos: list[str], limite: int = 8) -> list[str]:
    """
    Gera sugestões "parecidas" para a sigla digitada:
      1) Começa com...
      2) Contém...
      3) Fuzzy (Levenshtein <= 1)
    """
    if not busca_raw:
        return []
    bnorm = normalizar_sigla(busca_raw)
    pares = [(s, normalizar_sigla(s)) for s in candidatos]

    # 1) Começa com...
    pref = [s for s, n in pares if n.startswith(bnorm)]
    seen = set(pref)

    # 2) Contém...
    if len(pref) < limite:
        cont = [s for s, n in pares if (bnorm in n) and (s not in seen)]
        pref.extend(cont)
        seen.update(cont)

    # 3) Fuzzy leve (<= 1 edição)
    if len(pref) < limite:
        fuzzy = []
        for s, n in pares:
            if s in seen:
                continue
            d = levenshtein(n, bnorm)
            if d <= 1:
                fuzzy.append((d, s))
        fuzzy = [s for _, s in sorted(fuzzy, key=lambda x: (x[0], x[1]))]
        pref.extend(fuzzy)

    # Limita e mantém ordem
    return pref[:limite]

def _select_sugestao(value: str):
    # Callback dos chips: salva em session_state e sinaliza auto-busca
    st.session_state["busca_sigla_pending"] = value
    st.session_state["do_busca_sigla"] = True
    # O clique no botão já dispara um rerun automaticamente.

# ==============================
#   CONTEÚDO — BUSCA POR SIGLA
# ==============================
st.title("🔍 Buscar por SIGLA")

df = carregar_dados()
acessos = carregar_acessos()

# Lista de siglas únicas (UPPER) para facilitar match
lista_siglas = sorted(df["sigla"].dropna().astype(str).str.upper().unique().tolist())

# ---------- Estado inicial & hidratação ----------
if "busca_sigla_input" not in st.session_state:
    st.session_state["busca_sigla_input"] = ""

# Se um chip foi clicado, no ciclo anterior guardamos em 'pending':
if "busca_sigla_pending" in st.session_state:
    st.session_state["busca_sigla_input"] = st.session_state.pop("busca_sigla_pending")

# Se foi solicitado auto-executar a busca (por clique no chip), consome o flag aqui
auto_trigger = st.session_state.pop("do_busca_sigla", False)

# ---------- Container para resultados ----------
result_ct = st.container()

# ---------- Formulário com botão OK logo abaixo ----------
with st.form("form_sigla", clear_on_submit=False):
    st.session_state["busca_sigla_input"] = st.text_input(
        "Digite a SIGLA do site/ERB",
        value=st.session_state.get("busca_sigla_input", "")
    )
    submitted = st.form_submit_button("OK")  # <= Botão OK

busca_val = st.session_state.get("busca_sigla_input", "").strip()

# ---------- Sugestões (chips) ----------
if busca_val:
    sugestoes = _gerar_sugestoes(busca_val, lista_siglas, limite=8)
    if sugestoes:
        st.markdown("### 🔎 Sugestões (clique para buscar)")
        st.markdown('<div id="chips-scope">', unsafe_allow_html=True)
        cols = st.columns(max(2, min(6, len(sugestoes))))
        for i, s in enumerate(sugestoes):
            with cols[i % len(cols)]:
                st.button(
                    s,
                    key=f"sug_{s}",
                    on_click=_select_sugestao,
                    args=(s,),
                )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("Nenhuma sugestão encontrada para a sigla digitada.")

# ---------- Executa busca se OK foi clicado OU se veio de um chip ----------
do_search = (submitted or auto_trigger) and bool(busca_val)

if do_search:
    busca_norm = normalizar_sigla(busca_val)

    # 1) Match exato (normalizado)
    achada = None
    for s in lista_siglas:
        if normalizar_sigla(s) == busca_norm:
            achada = s
            break

    # 2) Fuzzy leve (menor distância; <=1 geralmente cobre "faltando 1 letra")
    if not achada and lista_siglas:
        dists = [(s, levenshtein(normalizar_sigla(s), busca_norm)) for s in lista_siglas]
        # Ordena por distância e depois por ordem alfabética
        dists.sort(key=lambda x: (x[1], x[0]))
        achada = dists[0][0] if dists else None

    with result_ct:
        if achada:
            st.success(f"SIGLA encontrada: **{achada}**")

            dados = df[df["sigla"].astype(str).str.upper() == achada].copy()

            # Tabela resumida
            cols_show = [c for c in ["sigla", "nome", "detentora", "endereco", "lat", "lon", "capacitado"] if c in dados.columns]
            if cols_show:
                st.dataframe(dados[cols_show], use_container_width=True)
            else:
                st.dataframe(dados, use_container_width=True)

            # Cartões de detalhes (um por linha)
            st.markdown("### 📍 Detalhes")
            for _, row in dados.iterrows():
                sigla_row = str(row.get("sigla", "—"))
                nome_row = str(row.get("nome", "—"))
                det_row  = str(row.get("detentora", "—")) if pd.notna(row.get("detentora")) else "—"
                end_row  = str(row.get("endereco", "—"))
                lat_val  = row.get("lat")
                lon_val  = row.get("lon")
                cap_row  = str(row.get("capacitado", "—")) if pd.notna(row.get("capacitado")) else "—"

                st.markdown(f"**{sigla_row} — {nome_row}**")
                st.markdown(
                    f"🏢 **Detentora:** {det_row}  \n"
                    f"📌 **Endereço:** {end_row}  \n"
                    f"🧰 **Capacitado:** {cap_row}  \n"
                    f"🧭 **Coordenadas:** {_format_coord(lat_val)}, {_format_coord(lon_val)}"
                )

                # Botão Google Maps (se coordenadas válidas)
                try:
                    if pd.notna(lat_val) and pd.notna(lon_val):
                        lat_f = float(lat_val)
                        lon_f = float(lon_val)
                        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
                        st.link_button("🗺️ Ver no Google Maps", maps_url, type="primary")
                except Exception:
                    pass

                # Técnicos com acesso liberado (se houver aba acessos)
                if acessos is not None and not acessos.empty:
                    tecs = (
                        acessos[acessos["sigla"].astype(str).str.upper() == sigla_row.upper()]
                        .get("tecnico", pd.Series(dtype="string"))
                        .dropna()
                        .unique()
                        .tolist()
                    )
                    if tecs:
                        st.info("👷 **Técnicos com acesso:**\n" + "\n".join([f"- {t}" for t in tecs]))
                    else:
                        st.info("👷 Nenhum técnico com acesso cadastrado para esta SIGLA.")
                else:
                    st.caption("ℹ️ Aba `acessos` não encontrada ou sem dados.")

                st.markdown("---")
        else:
            st.error("Nenhuma SIGLA compatível encontrada.")
else:
    st.caption("Dica: digite parte da sigla e use as sugestões para agilizar a busca.")
