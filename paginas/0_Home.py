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


def _render_card_material(titulo, descricao, url, icone):
    st.markdown(
        f"""
        <article class='cv-home-card'>
            <div class='cv-home-card-icon'>{icone}</div>
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
            background: linear-gradient(160deg, #ffffff 0%, #f3f7ff 55%, #eef4ff 100%);
            border: 1px solid #cfdcf1;
            border-radius: 18px;
            padding: 1rem 1rem 1.05rem 1rem;
            box-shadow: 0 14px 28px rgba(16, 24, 40, 0.10), 0 4px 8px rgba(16, 24, 40, 0.04);
            min-height: 220px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 0.6rem;
            margin-bottom: 0.85rem;
            position: relative;
            overflow: hidden;
        }

        .cv-home-card::before {
            content: "";
            position: absolute;
            top: -26px;
            right: -20px;
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(7, 73, 171, 0.14) 0%, rgba(7, 73, 171, 0.0) 70%);
            pointer-events: none;
        }

        .cv-home-card-icon {
            font-size: 2.45rem;
            line-height: 1;
            width: 68px;
            height: 68px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(145deg, #0b4ca8 0%, #3f78bf 100%);
            color: #fff;
            box-shadow: 0 10px 22px rgba(7, 73, 171, 0.32), 0 0 22px rgba(94, 160, 255, 0.52);
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 0.15rem;
            z-index: 1;
            position: relative;
        }

        .cv-home-card-icon::after {
            content: "";
            position: absolute;
            inset: -8px;
            border-radius: 18px;
            background: radial-gradient(circle, rgba(135, 189, 255, 0.45) 0%, rgba(135, 189, 255, 0.0) 72%);
            z-index: -1;
        }

        .cv-home-card h4 {
            margin: 0;
            font-size: 1.03rem;
            color: #0f2f5a;
            font-weight: 800;
            line-height: 1.25;
            z-index: 1;
            text-align: center;
        }

        .cv-home-card p {
            margin: 0;
            color: #4b5f7b;
            font-size: 0.91rem;
            line-height: 1.42;
            z-index: 1;
        }

        .cv-home-card-btn {
            display: block;
            text-decoration: none !important;
            background: linear-gradient(135deg, #0b4ca8 0%, #3f78bf 100%);
            color: #ffffff !important;
            font-weight: 700;
            font-size: 0.88rem;
            border-radius: 10px;
            padding: 0.5rem 0.78rem;
            width: 100%;
            text-align: center;
            box-shadow: 0 6px 14px rgba(7, 73, 171, 0.28);
            transition: transform 0.15s ease, filter 0.15s ease;
            z-index: 1;
        }

        .cv-home-card-btn:link,
        .cv-home-card-btn:visited,
        .cv-home-card-btn:hover,
        .cv-home-card-btn:active {
            text-decoration: none !important;
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

st.title('Diagnóstico Econômico da Cultura Viva')
st.markdown(
    f"""
Este painel integra o projeto **Diagnóstico Econômico da Cultura Viva**, realizado pelo **Consórcio Universitário Cultura Viva (UFBA, UFF e UFPR)** em parceria com a **Secretaria de Cidadania e Diversidade Cultural do Ministério da Cultura**. Sua finalidade é produzir evidências aplicadas sobre a situação econômica dos Pontos e Pontões de Cultura, com foco em condições reais de sustentabilidade, geração de renda e continuidade das ações culturais nos territórios.

A proposta responde a uma demanda histórica da Rede Cultura Viva: transformar informação dispersa em base estratégica para orientar políticas públicas mais estáveis, especialmente no enfrentamento da sazonalidade de editais, da descontinuidade de fomento e dos limites de circulação econômica entre iniciativas culturais. O dashboard existe para apoiar decisões concretas de gestão, pactuação federativa e fortalecimento de arranjos produtivos locais, solidários e criativos.

Nesta versão, o painel organiza uma base ativa de **{_fmt_int(n_total)} respostas válidas**, com cobertura em **{_fmt_int(n_municipios)} municípios em todos os estados do Brasil**. A análise dinâmica do dashboard permite combinar filtros, revelar padrões territoriais e institucionais, testar hipóteses e transformar evidências em decisões mais precisas para fomento, gestão e articulação da Rede Cultura Viva.
    """
)

st.markdown('#### Contexto e objetivos da pesquisa')
st.markdown(
    """
- Qualificar evidências sobre sustentabilidade econômica e funcionamento da Rede Cultura Viva.
- Subsidiar decisões de política pública para fomento, fortalecimento institucional e implementação da PNCV/PNAB.
- Integrar pesquisa e formação em abordagem participativa, com mobilização dos Pontões e apoio à coordenação federativa.
    """
)

st.markdown('#### Como usar o Dashboard')
st.markdown(
    """
- Comece pelos filtros estratégicos para definir o recorte territorial e temático da análise.
- Navegue pelas páginas A-G para comparar resultados por dimensão (identificação, recursos, mercados, gestão, redes e cruzamentos).
- Combine filtros para gerar recortes úteis e apoiar decisões, prioridades e monitoramento no Dashboard.
- Para melhor experiência visual, use preferencialmente desktop em tela Full HD (1920x1080) ou superior.
    """
)

st.divider()

st.markdown('### Distribuição amostral da pesquisa no Brasil')
st.markdown(
    'Este mapa apresenta a distribuição territorial da amostra coletada na pesquisa, em que os marcadores azuis representam Pontos de Cultura e os vermelhos representam Pontões de Cultura, evidenciando a capilaridade e a diversidade de presença da Rede Cultura Viva no país.'
)
fig_mapa = mapa_pontos_matplotlib(df, titulo='')
st.pyplot(fig_mapa, use_container_width=True)
plt.close(fig_mapa)

st.markdown('### Materiais completos da pesquisa')
st.markdown('Acesse os materiais oficiais de referência utilizados no painel.')

materiais = [
    {
        'titulo': 'Consórcio Cultura Viva',
        'descricao': 'Portal oficial da pesquisa com publicações, notícias e materiais institucionais.',
        'url': 'https://pesquisaculturaviva.org/',
        'icone': '🌐',
    },
    {
        'titulo': 'Projeto de Pesquisa',
        'descricao': 'Documento-base com justificativa, desenho metodológico e plano amostral.',
        'url': 'https://pesquisaculturaviva.org/wp-content/uploads/2025/08/Projeto-de-Pesquisa-Diagnostico-Economico-da-Cultura-Viva.pdf',
        'icone': '📘',
    },
    {
        'titulo': 'Formulário de Diagnóstico',
        'descricao': 'Instrumento completo de coleta aplicado aos Pontos e Pontões de Cultura.',
        'url': 'https://pesquisaculturaviva.org/wp-content/uploads/2025/08/FORMULARIO-DE-DIAGNOSTICO-ECONOMICO-DA-CULTURA-VIVA.pdf',
        'icone': '📝',
    },
    {
        'titulo': 'Relatório completo',
        'descricao': 'Relatório analítico completo da pesquisa, com visualizações e resultados detalhados.',
        'url': 'https://pesquisaculturaviva.netlify.app/',
        'icone': '📊',
    },
]

card_cols = st.columns(2, gap='small')
for i, material in enumerate(materiais):
    with card_cols[i % 2]:
        _render_card_material(
            titulo=material['titulo'],
            descricao=material['descricao'],
            url=material['url'],
            icone=material['icone'],
        )

st.divider()

