import streamlit as st

from config import PALETA_CORES
from paginas import (
    pagina_articulacao_rede,
    pagina_capacidade_infraestrutura,
    pagina_cruzamentos_estrategicos,
    pagina_economias_singulares,
    pagina_gestao_mundo_trabalho,
    pagina_mercados_comercializacao,
    pagina_perfil_institucional,
    pagina_sustentabilidade_economica,
    pagina_visao_geral_dados
)

st.set_page_config(page_title='Dashboard Cultura Viva', layout='wide')
st.logo('assets/logo.png')

st.markdown(
    f"""
    <style>
        .stMetric label {{ color: {PALETA_CORES['cinza_escuro']}; }}
    </style>
    """,
    unsafe_allow_html=True
)

paginas = [
    st.Page(pagina_visao_geral_dados, title='1. Visão Geral dos Dados'),
    st.Page(pagina_perfil_institucional, title='2. Perfil Institucional e Identidade'),
    st.Page(pagina_capacidade_infraestrutura, title='3. Capacidade de Atendimento e Infraestrutura'),
    st.Page(pagina_sustentabilidade_economica, title='4. Sustentabilidade Econômica (O Dinheiro)'),
    st.Page(pagina_mercados_comercializacao, title='5. Mercados e Comercialização'),
    st.Page(pagina_economias_singulares, title='6. Economias Singulares (Solidariedade)'),
    st.Page(pagina_gestao_mundo_trabalho, title='7. Gestão e Mundo do Trabalho'),
    st.Page(pagina_articulacao_rede, title='8. Articulação em Rede'),
    st.Page(pagina_cruzamentos_estrategicos, title='9. Cruzamentos Estratégicos (Análise Avançada)')
]

st.navigation(paginas).run()

