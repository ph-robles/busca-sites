import streamlit as st

st.set_page_config(page_title="Site Radar", page_icon="📡", layout="wide")

# OCULTAR SIDEBAR SÓ NA HOME
hide_menu_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="stAppViewContainer"] {margin-left: 0;}
        [data-testid="stHeader"] {margin-left: 0;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# LOGO (opcional)
st.image("logo.png", width=220)

st.title("📡 Localizar Site/ERB")
st.markdown("### Selecione uma opção abaixo:")

# CSS PREMIUM PARA BOTÕES DA HOME
button_style = """
<style>

div.stButton > button {
    background-color: #0084ff;
    color: white;
    border-radius: 14px;
    padding: 14px 24px;
    font-size: 1.2rem;
    font-weight: 600;
    border: none;
    width: 100%;
    transition: all 0.2s ease-in-out;
    box-shadow: 0px 3px 10px rgba(0, 132, 255, 0.3);
}

div.stButton > button:hover {
    background-color: #006ddb;
    transform: translateY(-3px);
    box-shadow: 0px 5px 18px rgba(0, 132, 255, 0.45);
}

div.stButton > button:active {
    transform: scale(0.97);
    background-color: #005bb8;
}

</style>
"""
st.markdown(button_style, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 Buscar por SIGLA", use_container_width=True):
        st.switch_page("pages/1_🔍_Busca_por_SIGLA.py")

with col2:
    if st.button("🧭 Buscar por ENDEREÇO", use_container_width=True):
        st.switch_page("pages/2_🧭_Busca_por_ENDEREÇO.py")


st.markdown("---")
st.markdown(
    '<div class="footer">❤️ Desenvolvido por Raphael Robles — © 2026 • Todos os direitos reservados 🚀</div>',
    unsafe_allow_html=True
)


