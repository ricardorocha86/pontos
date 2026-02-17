import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from components import mapa_pontos_matplotlib
from utils import preparar_base

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'assets'))


def _fmt_int(valor):
    return f'{int(valor):,}'.replace(',', '.')


def _render_card_material(titulo, descricao, url):
    st.markdown(
        f"""
        <article class='cv-home-card'>
            <h4>{titulo}</h4>
            <p>{descricao}</p>
            <a class='cv-home-card-btn' href='{url}' target='_blank' rel='noopener noreferrer'>Acessar material completo</a>
        </article>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
        .cv-home-card {
            background: linear-gradient(165deg, #ffffff 0%, #f6f9ff 100%);
            border: 1px solid #d5e0f0;
            border-radius: 14px;
            padding: 0.95rem 1rem 1rem 1rem;
            box-shadow: 0 10px 24px rgba(16, 24, 40, 0.08);
            min-height: 198px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 0.55rem;
            margin-bottom: 0.85rem;
        }

        .cv-home-card h4 {
            margin: 0;
            font-size: 1rem;
            color: #0f2f5a;
            font-weight: 800;
            line-height: 1.25;
        }

        .cv-home-card p {
            margin: 0;
            color: #4c607b;
            font-size: 0.92rem;
            line-height: 1.42;
        }

        .cv-home-card-btn {
            display: inline-block;
            text-decoration: none;
            background: linear-gradient(135deg, #0b4ca8 0%, #3f78bf 100%);
            color: #ffffff !important;
            font-weight: 700;
            font-size: 0.88rem;
            border-radius: 10px;
            padding: 0.5rem 0.78rem;
            width: fit-content;
            box-shadow: 0 6px 14px rgba(7, 73, 171, 0.28);
            transition: transform 0.15s ease, filter 0.15s ease;
        }

        .cv-home-card-btn:hover {
            filter: brightness(1.04);
            transform: translateY(-1px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Imagem principal da Home
cover_path = os.path.join(ASSETS_DIR, 'cover.webp')
if os.path.exists(cover_path):
    st.image(cover_path, use_container_width=True)

# Base completa (sem filtros)
df = preparar_base()

# Características amostrais
n_total = len(df)

cidade = df['cidade'].fillna('').astype(str).str.strip() if 'cidade' in df.columns else pd.Series(dtype=str)
n_municipios = cidade[cidade != ''].nunique()

if 'uf_api' in df.columns:
    uf = df['uf_api'].fillna('').astype(str).str.upper().str.strip()
elif 'uf' in df.columns:
    uf = df['uf'].fillna('').astype(str).str.upper().str.strip()
else:
    uf = pd.Series(dtype=str)
uf = uf[uf.str.match(r'^[A-Z]{2}$', na=False)]
n_ufs = uf.nunique()

regiao = df['regiao'].fillna('').astype(str).str.strip() if 'regiao' in df.columns else pd.Series(dtype=str)
n_regioes = regiao[regiao != ''].nunique()

if 'tipo_ponto' in df.columns:
    tipo = df['tipo_ponto'].fillna('Ponto').astype(str).str.lower().str.strip()
    eh_pontao = tipo.str.contains('pont') & (~tipo.str.fullmatch(r'ponto'))
    n_ponto = int((~eh_pontao).sum())
    n_pontao = int(eh_pontao.sum())
else:
    n_ponto = n_total
    n_pontao = 0

st.title('Diagnóstico Econômico da Rede Cultura Viva')
st.markdown(
    f"""
Esta plataforma apresenta os resultados da pesquisa nacional conduzida pelo **Consórcio Universitário Cultura Viva (UFBA, UFF e UFPR)**, em parceria com a **Secretaria de Cidadania e Diversidade Cultural do Ministério da Cultura**.

A amostra consolidada desta edição reúne **N = {_fmt_int(n_total)}** respostas válidas, distribuídas em **{_fmt_int(n_municipios)} municípios**, **{_fmt_int(n_ufs)} unidades da federação** e **{_fmt_int(n_regioes)} regiões do país**.

No conjunto analisado, observam-se **{_fmt_int(n_ponto)} Pontos de Cultura** e **{_fmt_int(n_pontao)} Pontões de Cultura**, permitindo uma leitura nacional da dimensão econômica, institucional e territorial da rede.
    """
)

st.markdown('#### Contexto e objetivos da pesquisa')
st.markdown(
    """
- Atualizar evidências sobre sustentabilidade econômica e dinâmica de funcionamento da Rede Cultura Viva.
- Subsidiar decisões de política pública para fomento, fortalecimento institucional e implementação da PNAB.
- Valorizar uma metodologia participativa e formativa, com envolvimento de Pontões no processo de mobilização e coleta.
    """
)

st.divider()

titulo_mapa = 'Distribuição Amostral da Pesquisa Cultura Viva no Brasil'

col_mapa, col_docs = st.columns([3, 2], gap='small')

with col_mapa:
    fig_mapa = mapa_pontos_matplotlib(df, titulo=titulo_mapa)
    st.pyplot(fig_mapa, use_container_width=True)
    plt.close(fig_mapa)

with col_docs:
    st.markdown('### Materiais completos da pesquisa')
    st.markdown('Acesse os materiais oficiais de referência utilizados no painel.')

    materiais = [
        {
            'titulo': 'Consórcio Cultura Viva',
            'descricao': 'Portal oficial da pesquisa com publicações, notícias e materiais institucionais.',
            'url': 'https://pesquisaculturaviva.org/',
        },
        {
            'titulo': 'Projeto de Pesquisa',
            'descricao': 'Documento-base com justificativa, desenho metodológico e plano amostral.',
            'url': 'https://pesquisaculturaviva.org/wp-content/uploads/2025/08/Projeto-de-Pesquisa-Diagnostico-Economico-da-Cultura-Viva.pdf',
        },
        {
            'titulo': 'Formulário de Diagnóstico',
            'descricao': 'Instrumento completo de coleta aplicado aos Pontos e Pontões de Cultura.',
            'url': 'https://pesquisaculturaviva.org/wp-content/uploads/2025/08/FORMULARIO-DE-DIAGNOSTICO-ECONOMICO-DA-CULTURA-VIVA.pdf',
        },
        {
            'titulo': 'Relatório completo',
            'descricao': 'Relatório analítico completo da pesquisa, com visualizações e resultados detalhados.',
            'url': 'https://relatorio-pontos.netlify.app/',
        },
    ]

    card_cols = st.columns(2, gap='small')
    for i, material in enumerate(materiais):
        with card_cols[i % 2]:
            _render_card_material(
                titulo=material['titulo'],
                descricao=material['descricao'],
                url=material['url'],
            )

st.divider()

# Cabeçalho institucional anterior movido para o final da página
header_path = os.path.join(ASSETS_DIR, 'cabeçalho.png')
if os.path.exists(header_path):
    col_h1, col_h2, col_h3 = st.columns([1, 2, 1])
    with col_h2:
        st.image(header_path, use_container_width=True)
