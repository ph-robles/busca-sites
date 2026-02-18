import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Sobre • Site Radar", page_icon="📡", layout="wide")

# =========================
# ESTILO GLOBAL (mantém a identidade visual da home)
# =========================
global_style = """
<style>
/* Ajustes gerais */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0b1217; /* fundo escuro elegante */
    color: #e6edf3;
}

/* Títulos */
h1, h2, h3 {
    color: #e6edf3;
}

/* Cartões (containers) */
.block-container {
    padding-top: 2rem;
}

.card {
    background: #0f1621;
    border: 1px solid rgba(0, 132, 255, 0.15);
    border-radius: 16px;
    padding: 20px 22px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.28);
}

/* Links */
a { color: #4aa8ff; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Botões */
div.stButton > button {
    background-color: #0084ff;
    color: white;
    border-radius: 14px;
    padding: 10px 18px;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    transition: all 0.2s ease-in-out;
    box-shadow: 0px 3px 10px rgba(0, 132, 255, 0.3);
}
div.stButton > button:hover {
    background-color: #006ddb;
    transform: translateY(-2px);
    box-shadow: 0px 5px 18px rgba(0, 132, 255, 0.45);
}
div.stButton > button:active {
    transform: scale(0.98);
    background-color: #005bb8;
}

/* Footer */
.footer {
    text-align: center;
    margin-top: 36px;
    color: #91a4b7;
    font-size: 0.95rem;
}
</style>
"""
st.markdown(global_style, unsafe_allow_html=True)

# =========================
# CABEÇALHO
# =========================
cols = st.columns([1, 3])
with cols[0]:
    st.image("logo.png", width=140)  # usa o mesmo logo da home (opcional)
with cols[1]:
    st.title("ℹ️ Sobre o Site Radar")
    st.caption("Encontre Sites/ERBs de forma rápida, confiável e com links diretos para navegação.")

st.markdown("---")

# =========================
# CONTEÚDO
# =========================
with st.container():
    st.subheader("🎯 Propósito")
    st.markdown(
        """
O **Site Radar** foi criado para **agilizar a rotina de técnicos e equipes de campo** no Rio de Janeiro:
- Localize rapidamente **Sites/ERBs** por **SIGLA** ou **Endereço**;
- Obtenha **coordenadas geográficas**, **endereços padronizados** e **links diretos para o Google Maps/Waze**;
- Minimize retrabalho com **dados padronizados** e **busca rápida** na planilha interna.
        """
    )

st.markdown("")

colA, colB = st.columns(2)
with colA:
    st.subheader("🚀 Principais recursos")
    st.markdown(
        """
- **Busca por SIGLA** (rápida e objetiva)  
- **Busca por Endereço** com retorno das **3 ERBs mais próximas** *(quando disponível)*  
- **Link direto p/ navegação** (Google Maps)  
- **Layout responsivo** e botões com **alto contraste**  
- **Padronização de dados** para evitar divergências de campo
        """
    )

with colB:
    st.subheader("🧭 Como usar")
    st.markdown(
        """
1. Acesse a **Home** e escolha o tipo de busca: **SIGLA** ou **ENDEREÇO**.  
2. Digite o termo, confirme e visualize os resultados.  
3. Clique no **link de navegação** para abrir no **Google Maps**.  
4. Se necessário, copie **coordenadas** ou **endereço padronizado**.
        """
    )

st.markdown("")

with st.container():
    st.subheader("🔒 Privacidade & Dados")
    st.markdown(
        """
- Os dados utilizados são provenientes de **planilhas internas** da empresa.  
- **Nenhuma informação sensível** (senhas ou credenciais) é exibida nesta interface.  
- O app pode **registrar métricas de uso** (como buscas e cliques em links) para **melhoria contínua**.  
- Em caso de dúvidas sobre privacidade, fale com o responsável pelo app.
        """
    )

st.markdown("")

with st.container():
    st.subheader("🛠️ Roadmap (curto prazo)")
    st.markdown(
        """
- ⚙️ Melhoria da busca por endereço com **ranking por distância**  
- 🗺️ Exibição de **mapa interativo** com **marcadores das ERBs**  
- 📥 Importação/atualização de planilhas **via interface**  
- 🧩 Exportação dos resultados em **CSV/Excel**
        """
    )

st.markdown("")

with st.container():
    st.subheader("🤝 Contato & Suporte")
    st.markdown(
        """
- **Responsável:** Raphael Robles  
- **Canal interno:** e-mail/Teams  
- **Sugestões e correções:** envie a **SIGLA**/**print** do caso e descreva o problema.  
        """
    )

st.markdown("---")

# =========================
# AÇÕES
# =========================
c1, c2, c3 = st.columns([1.2, 1, 1.5])
with c1:
    if st.button("🏠 Voltar para a Home"):
        st.switch_page("app.py")  # ajuste o nome conforme seu arquivo principal

with c2:
    st.page_link("pages/1_🔍_Busca_por_SIGLA.py", label="Ir para: Buscar por SIGLA", icon="🔍")

with c3:
    st.page_link("pages/2_🧭_Busca_por_ENDEREÇO.py", label="Ir para: Buscar por ENDEREÇO", icon="🧭")

st.markdown("")

# =========================
# VERSÃO / RODAPÉ
# =========================
versao = "1.0.0"
build_date = datetime(2026, 2, 18)  # ajuste se desejar automatizar
st.info(f"**Versão:** {versao}  •  **Build:** {build_date.strftime('%d/%m/%Y')}  •  **Status:** estável")

st.markdown(
    '<div class="footer">❤️ Desenvolvido por Raphael Robles — © 2026 • Todos os direitos reservados 🚀</div>',
    unsafe_allow_html=True
)
