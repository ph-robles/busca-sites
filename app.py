import streamlit as st
import pandas as pd
import folium
from folium import Marker
from streamlit_folium import st_folium

# Carregar os dados da planilha
df = pd.read_excel("enderecos.xlsx", engine="openpyxl")

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
df['lat'] = df['lat'].astype(str).str.replace(',', '.').astype(float)
df['lon'] = df['lon'].astype(str).str.replace(',', '.').astype(float)

# Criar coluna de cidade extraída do nome da torre
df['cidade'] = df['nome'].str.extract(r'^([A-Z\\s]+?)(?:\\s*-\\s*|$)', expand=False).str.strip()

# Título da aplicação
st.title("📡 Endereços dos Sites RJ")

# Filtros
col1, col2, col3 = st.columns(3)

with col1:
    sigla_input = st.text_input("🔍 Buscar por sigla:")

with col2:
    cidade_opcao = st.selectbox("🏙️ Filtrar por Localidade:", options=["Todas"] + sorted(df['cidade'].dropna().unique().tolist()))

with col3:
    nome_opcao = st.selectbox("📍 Filtrar por nome da torre:", options=["Todas"] + sorted(df['nome'].dropna().unique().tolist()))

# Aplicar filtros
df_filtrado = df.copy()

if sigla_input:
    df_filtrado = df_filtrado[df_filtrado['sigla'].str.upper() == sigla_input.upper()]

if cidade_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado['cidade'] == cidade_opcao]

if nome_opcao != "Todas":
    df_filtrado = df_filtrado[df_filtrado['nome'] == nome_opcao]

# Verificar se há resultados
if df_filtrado.empty:
    st.warning("⚠️ Nenhuma torre encontrada com os filtros selecionados.")
else:
    st.success(f"🔎 {len(df_filtrado)} Site(s) encontrado(s).")

    # Mostrar tabela com resultados
    st.dataframe(df_filtrado[['sigla', 'nome', 'endereco', 'lat', 'lon']])

    # Criar mapa com marcadores
    mapa = folium.Map(location=[df_filtrado['lat'].mean(), df_filtrado['lon'].mean()], zoom_start=10)

    for _, row in df_filtrado.iterrows():
        Marker(
            location=[row['lat'], row['lon']],
            popup=f"{row['sigla']} - {row['nome']}",
            tooltip=row['endereco']
        ).add_to(mapa)

    st_folium(mapa, width=700, height=500)

    # Mostrar detalhes com link para Google Maps
    st.markdown("### 📍 Detalhes das torres encontradas")
    for _, row in df_filtrado.iterrows():
        maps_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
        st.markdown(f"**{row['sigla']} - {row['nome']}**")
        st.markdown(f"🗺️ Ver no Google Maps")
        st.markdown(f"📌 **Endereço:** {row['endereco']}")
        st.markdown("---")
