import streamlit as st
import pandas as pd
from utils.data_loader import carregar_dados, carregar_capacitados_lista
from utils.geocode import geocode_address
from utils.helpers import haversine_km
from utils.osrm_tools import osrm_table

st.set_page_config(page_title="Buscar por ENDEREÇO • Site Radar", page_icon="📡", layout="wide")

# ==============================
#   SIDEBAR PREMIUM COMPACTA (BLUR + MOBILE SAFE)
# ==============================

sidebar_style = """
<style>

/* Sidebar geral */
[data-testid="stSidebar"] {
    background: rgba(20, 25, 35, 0.55) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-right: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 40px;
    width: 240px !important;
}

/* Logo centralizada */
.sidebar-logo {
    display: flex;
    justify-content: center;
    margin-bottom: 250px;
}

/* Sidebar compacta no celular (ajustada) */
@media (max-width: 760px) {
    [data-testid="stSidebar"] {
        width: 300px !important;       /* largura aumentada */
        min-width: 136px !important;
        padding-top: 24px;
        padding-left: 6px;
        padding-right: 6px;
    }

    .sidebar-logo img {
        width: 250px !important;        /* logo aumentada */
    }

    .sidebar-content, .sidebar-text {
        display: none !important;
    }
}

/* Badge de capacitado */
.cap-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #0b5;
    background: rgba(0,187,85,.12);
    border: 1px solid rgba(0,187,85,.35);
    margin-left: 8px;
}

/* Badge de destaque (primeiro capacitado) */
.first-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #0057d9;
    background: rgba(0, 87, 217, .08);
    border: 1px solid rgba(0, 87, 217, .18);
    margin-left: 8px;
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
#   AUXILIARES LOCAIS
# ==============================

YES = {"sim","s","yes","y","1","true","verdadeiro","ok","ativo","habilitado","cap","capacitado"}
def _is_yes(val) -> bool:
    try:
        return str(val).strip().lower() in YES
    except Exception:
        return False

def _cap_badge(is_cap: bool) -> str:
    return ' <span class="cap-badge">Capacitado</span>' if is_cap else ""

# ==============================
#   CONTEÚDO — BUSCA POR ENDEREÇO
# ==============================

st.title("🧭 Buscar por ENDEREÇO")

df = carregar_dados()

# Unifica status de capacitado:
# - Se houver coluna 'capacitado', interpreta SIM/NÃO
# - Se houver aba separada (carregar_capacitados_lista), une com OR
siglas_cap_set = carregar_capacitados_lista()  # pode ser None
siglas_upper = df["sigla"].astype(str).str.upper()
col_cap_bool = df["capacitado"].apply(_is_yes) if "capacitado" in df.columns else pd.Series([False]*len(df))
in_set_bool = siglas_upper.isin(siglas_cap_set) if siglas_cap_set else pd.Series([False]*len(df))
df["_is_capacitado"] = (col_cap_bool | in_set_bool)

# Criamos um container para os resultados
result_ct = st.container()

# ============= FORMULÁRIO COM BOTÃO OK =============
with st.form("form_endereco", clear_on_submit=False):
    endereco_cliente = st.text_input(
        "Digite o endereço completo (rua, número, bairro, cidade)"
    )
    submitted = st.form_submit_button("OK")  # <= Botão OK

# Se não clicou OK, não faz nada ainda
if not submitted:
    st.caption("Dica: digite um endereço e clique em **OK**.")
    st.stop()

# ==============================
#   PROCESSAR BUSCA APÓS OK
# ==============================

with result_ct:
    if not endereco_cliente.strip():
        st.error("❌ Digite um endereço válido antes de continuar.")
        st.stop()

    with st.spinner("🔎 Localizando endereço..."):
        geo = geocode_address(endereco_cliente)

    if not geo:
        st.error("❌ Não foi possível localizar o endereço informado.")
        st.stop()

    lat_cli, lon_cli, form = geo
    st.success(f"Endereço encontrado:\n\n**{form}**")
    st.write(f"🧭 **Coordenadas:** {lat_cli:.6f}, {lon_cli:.6f}")

    # Garantir que existam ERBs válidas
    base = df.dropna(subset=["lat", "lon"]).copy()
    if base.empty:
        st.error("⚠ Nenhuma ERB possui coordenadas válidas na planilha.")
        st.stop()

    # Calcular distâncias em linha reta
    base["dist_km"] = haversine_km(lat_cli, lon_cli, base["lat"], base["lon"])

    # ================= LÓGICA QUE VOCÊ PEDIU =================
    # 1) Escolher SEMPRE o capacitado mais próximo (se existir), mesmo que esteja longe
    base_cap = base[base["_is_capacitado"] == True].copy()
    forced_cap_row = None
    if not base_cap.empty:
        idx_min_cap = base_cap["dist_km"].idxmin()
        forced_cap_row = base_cap.loc[[idx_min_cap]].copy()  # 1 linha (DataFrame)

    # 2) Pegar os 2 mais próximos (excluindo o capacitado escolhido, se houver)
    if forced_cap_row is not None:
        excl_index = forced_cap_row.index[0]
        restantes = base.drop(index=excl_index).copy()
        outros2 = restantes.nsmallest(2, "dist_km").copy()
        # Combinar: capacitado escolhido (primeiro) + dois mais próximos
        final = pd.concat([forced_cap_row, outros2], ignore_index=True)
        # Marcar coluna auxiliar para destacar o primeiro capacitado
        final["_is_forced_cap"] = [True] + [False] * (len(final) - 1)
    else:
        # Se não houver capacitado, fica apenas o top-3 normal
        final = base.nsmallest(3, "dist_km").copy()
        final["_is_forced_cap"] = [False] * len(final)

    # ==========================================================

    # Distância via rota (OSRM)
    destinos = [(float(r["lat"]), float(r["lon"])) for _, r in final.iterrows()]
    osrm_out = osrm_table(lat_cli, lon_cli, destinos)

    if osrm_out and len(osrm_out) == len(final):
        final["dist_rota_km"] = [x["distance_km"] for x in osrm_out]
        final["tempo_min"]    = [x["duration_min"] for x in osrm_out]
    else:
        final["dist_rota_km"] = None
        final["tempo_min"]    = None

    # Tabela resumida com info útil
    mostrar_cols = [c for c in ["sigla","nome","detentora","endereco","lat","lon","capacitado","_is_capacitado","dist_km","dist_rota_km","tempo_min"] if c in final.columns]
    st.markdown("### 📌 Resultado (sempre inclui o capacitado mais próximo, se existir)")
    st.dataframe(final[mostrar_cols], use_container_width=True)

    # ======= CARTÕES DETALHADOS =======
    for _, row in final.iterrows():
        erb_lat = float(row["lat"])
        erb_lon = float(row["lon"])
        sigla   = str(row.get("sigla", "—"))
        nome    = str(row.get("nome", "—"))
        is_cap  = bool(row.get("_is_capacitado", False))
        cap_md  = _cap_badge(is_cap)
        is_first = bool(row.get("_is_forced_cap", False))
        first_md = ' <span class="first-badge">Capacitado mais próximo</span>' if is_first and is_cap else ""

        rota    = f"https://www.google.com/maps/dir/?api=1&origin={lat_cli},{lon_cli}&destination={erb_lat},{erb_lon}&travelmode=driving"
        maps    = f"https://www.google.com/maps/search/?api=1&query={erb_lat},{erb_lon}"

        st.markdown(f"### **{sigla} — {nome}**{cap_md}{first_md}", unsafe_allow_html=True)
        st.markdown(
            f"🗺️ **Linha reta:** {row['dist_km']:.3f} km  \n"
            f"🚗 **Distância por rota:** {row.get('dist_rota_km', '—')} km  \n"
            f"⏱ **Tempo estimado:** {row.get('tempo_min', '—')} min"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.link_button("🗺️ Ver no Maps", maps)
        with col2:
            st.link_button("🚗 Traçar rota", rota)

        st.markdown("---")
