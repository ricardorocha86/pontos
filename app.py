import streamlit as st
import streamlit.components.v1 as components
import os
from utils import preparar_base
from config import PALETA_CORES
from filters import renderizar_painel_filtros

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Consultoria Cultura Viva - V2',
    page_icon='assets/cor-cultura viva.svg',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Custom CSS
st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --cv-blue: {PALETA_CORES['principais'][1]};
            --cv-red: {PALETA_CORES['principais'][0]};
            --cv-yellow: {PALETA_CORES['principais'][2]};
            --cv-title: {PALETA_CORES['principais'][1]};
            --cv-h1: rgba(0,0,0,0.90);
            --cv-tab-start: {PALETA_CORES['principais'][1]};
            --cv-tab-end: #3e73bc;
            --cv-slate: #344054;
            --cv-border: #d9e2ef;
            --cv-surface: #ffffff;
            --cv-surface-soft: #f7f9fc;
        }}

        html, body, [class*="css"], .stApp {{
            font-family: 'Inter', Arial, Helvetica, sans-serif;
            font-size: 15px;
            color: var(--cv-slate);
        }}

        .stApp {{
            background:
                radial-gradient(1200px 320px at 90% -10%, rgba(65,122,189,0.10), transparent 65%),
                radial-gradient(900px 260px at 10% -20%, rgba(7,73,171,0.08), transparent 60%),
                linear-gradient(180deg, #fbfcff 0%, #f6f8fb 100%);
        }}

        [data-testid="stAppViewContainer"] > .main .block-container {{
            padding-top: 1.15rem;
        }}

        h1, h2, h3 {{
            color: var(--cv-title);
            letter-spacing: -0.015em;
            line-height: 1.12;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }}

        h1 {{
            font-size: clamp(1.95rem, 1.95vw, 2.45rem);
            font-weight: 800;
            color: var(--cv-h1);
        }}

        h2 {{
            font-size: clamp(1.5rem, 1.5vw, 2rem);
        }}

        h3 {{
            font-size: clamp(1.15rem, 1.12vw, 1.45rem);
        }}

        p {{
            line-height: 1.45;
        }}

        /* Tabs */
        [data-testid="stTabs"] [role="tablist"] {{
            gap: 0.45rem;
            padding-bottom: 0.35rem;
            border-bottom: 1px solid #dbe3ef;
        }}

        [data-testid="stTabs"] [role="tab"] {{
            background: #eef3fb;
            border: 1px solid #d3deef;
            border-radius: 10px 10px 0 0;
            border-bottom: none;
            color: #3b4a63;
            font-size: 1.05rem !important;
            font-weight: 400 !important;
            padding: 0.46rem 0.98rem 0.42rem 0.98rem;
            transition: all 0.18s ease;
        }}

        [data-testid="stTabs"] [data-baseweb="tab"] {{
            background: #eef3fb;
            border: 1px solid #d3deef;
            border-radius: 10px 10px 0 0;
            border-bottom: none;
            color: #3b4a63;
            font-size: 1.05rem !important;
            font-weight: 400 !important;
            padding: 0.46rem 0.98rem 0.42rem 0.98rem;
            transition: all 0.18s ease;
        }}

        [data-testid="stTabs"] [role="tab"] p,
        [data-testid="stTabs"] [role="tab"] span,
        [data-testid="stTabs"] [data-baseweb="tab"] p,
        [data-testid="stTabs"] [data-baseweb="tab"] span {{
            font-size: 1.05rem !important;
            font-weight: 400 !important;
        }}

        [data-testid="stTabs"] [role="tab"]:hover {{
            border-color: #94b4e0;
            color: var(--cv-blue);
            background: #f5f9ff;
        }}

        [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
            border-color: #94b4e0;
            color: var(--cv-blue);
            background: #f5f9ff;
        }}

        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
            color: #ffffff;
            border-color: var(--cv-blue);
            background: linear-gradient(135deg, var(--cv-tab-start) 0%, var(--cv-tab-end) 100%);
            box-shadow: 0 5px 12px rgba(7, 73, 171, 0.26);
            font-weight: 750 !important;
        }}

        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
            color: #ffffff;
            border-color: var(--cv-blue);
            background: linear-gradient(135deg, var(--cv-tab-start) 0%, var(--cv-tab-end) 100%);
            box-shadow: 0 5px 12px rgba(7, 73, 171, 0.26);
            font-weight: 750 !important;
        }}

        /* Metric cards */
        [data-testid="metric-container"],
        div[data-testid="stMetric"] {{
            background:
                linear-gradient(90deg, rgba(7,73,171,0.24), rgba(65,122,189,0.10), rgba(5,161,85,0.10)) top/100% 4px no-repeat,
                linear-gradient(162deg, #ffffff 0%, #f6f9ff 72%);
            border: 1px solid #b9cde8;
            border-radius: 18px;
            padding: 0.88rem 0.95rem 0.94rem 0.95rem;
            box-shadow:
                0 12px 28px rgba(15, 23, 42, 0.14),
                0 1px 0 rgba(255,255,255,0.65) inset;
            backdrop-filter: blur(2px);
            margin-bottom: 0.4rem;
        }}

        [data-testid="metric-container"] label,
        div[data-testid="stMetricLabel"] label,
        div[data-testid="stMetricLabel"] p {{
            color: #355078 !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.01em;
            text-transform: uppercase;
            margin-bottom: 0.15rem !important;
        }}

        [data-testid="metric-container"] [data-testid="stMetricValue"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] > div {{
            color: var(--cv-blue) !important;
            font-size: 2.08rem !important;
            font-weight: 800 !important;
            line-height: 1.08;
            letter-spacing: -0.01em;
        }}

        /* Expander (filtros) */
        [data-testid="stExpander"] {{
            border: 1px solid #cedbed !important;
            border-radius: 14px !important;
            background: var(--cv-surface) !important;
            box-shadow: 0 10px 24px rgba(16, 24, 40, 0.08) !important;
            overflow: hidden !important;
        }}

        [data-testid="stExpander"] > details > summary {{
            background: linear-gradient(135deg, var(--cv-tab-start) 0%, var(--cv-tab-end) 100%) !important;
            color: #ffffff !important;
            font-size: 1.10rem !important;
            font-weight: 600 !important;
            padding: 0.82rem 1.02rem !important;
        }}

        [data-testid="stExpander"] > details > summary p,
        [data-testid="stExpander"] > details > summary span {{
            font-size: 1.10rem !important;
            font-weight: 600 !important;
        }}

        [data-testid="stExpander"] > details > summary:hover {{
            filter: brightness(1.04);
        }}

        [data-testid="stExpander"] > details > summary svg {{
            fill: #ffffff !important;
        }}

        [data-testid="stExpander"] > details > div {{
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            padding: 1rem 1rem 1.2rem 1rem !important;
        }}

        /* Widgets de filtro */
        [data-baseweb="select"] > div {{
            border-radius: 12px !important;
            border: 1px solid #d6dfec !important;
            background: linear-gradient(180deg, #f9fbff 0%, #f1f6ff 100%) !important;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 0 rgba(255,255,255,0.7) inset;
            min-height: 40px;
        }}

        [data-baseweb="select"] > div:hover {{
            border-color: #95b7e6 !important;
        }}

        [data-baseweb="select"] > div:focus-within {{
            border-color: var(--cv-blue) !important;
            box-shadow: 0 0 0 3px rgba(7, 73, 171, 0.15) !important;
        }}

        [data-baseweb="tag"] {{
            border-radius: 999px !important;
            border: 1px solid #bdd0ec !important;
            background: #edf3ff !important;
            color: var(--cv-blue) !important;
            font-weight: 600 !important;
        }}

        [data-testid="stPills"] [role="radiogroup"] {{
            gap: 0.32rem !important;
        }}

        [data-testid="stPills"] [role="radio"] {{
            border-radius: 999px !important;
            border: 1px solid #d4deec !important;
            background: #ffffff !important;
            color: #41506b !important;
            font-weight: 600 !important;
            padding: 0.15rem 0.65rem !important;
        }}

        [data-testid="stPills"] [role="radio"][aria-checked="true"] {{
            background: var(--cv-blue) !important;
            border-color: var(--cv-blue) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 10px rgba(7, 73, 171, 0.25);
        }}

        /* Botões */
        .stButton > button {{
            border-radius: 10px;
            border: 1px solid #c8d6eb;
            background: #ffffff;
            color: var(--cv-blue);
            font-weight: 650;
            transition: all 0.16s ease;
        }}

        .stButton > button:hover {{
            border-color: var(--cv-blue);
            background: #f1f7ff;
            transform: translateY(-1px);
        }}

        .stButton > button:focus {{
            box-shadow: 0 0 0 3px rgba(7, 73, 171, 0.16);
        }}

        [data-testid="stSidebar"] .stButton > button {{
            border-radius: 11px;
            border: 1px solid #0a469f;
            color: #ffffff;
            background: linear-gradient(135deg, var(--cv-tab-start) 0%, var(--cv-tab-end) 100%);
            box-shadow: 0 6px 14px rgba(7, 73, 171, 0.30);
            font-weight: 700;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            filter: brightness(1.06);
            transform: translateY(-1px);
            border-color: #0a4ead;
        }}

        [data-testid="stSidebar"] .stButton > button:disabled {{
            background: #c7d2e3;
            border-color: #b7c3d8;
            color: #f6f8fb;
            box-shadow: none;
            cursor: not-allowed;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #fffde9 0%, #fff7d8 100%);
        }}

        [data-testid="stSidebar"] [data-testid="metric-container"],
        [data-testid="stSidebar"] div[data-testid="stMetric"] {{
            background:
                linear-gradient(90deg, rgba(7,73,171,0.18), rgba(65,122,189,0.08)) top/100% 3px no-repeat,
                linear-gradient(162deg, #fffef9 0%, #fffaf0 80%);
            border-color: #dfd3a6;
            box-shadow: 0 8px 16px rgba(74, 74, 74, 0.10);
        }}

        /* Cards customizados de status (sidebar) */
        .cv-status-card {{
            background: linear-gradient(162deg, #fffef9 0%, #fffaf0 82%);
            border: 1px solid #d9cea6;
            border-radius: 16px;
            padding: 0.72rem 0.78rem 0.7rem 0.78rem;
            box-shadow: 0 8px 16px rgba(74, 74, 74, 0.08);
            margin-bottom: 0.25rem;
        }}

        .cv-status-label {{
            font-size: 0.92rem;
            color: #2f3f59;
            font-weight: 600;
            line-height: 1.1;
            margin-bottom: 0.38rem;
        }}

        .cv-status-value {{
            font-size: 2.02rem;
            font-weight: 800;
            color: #0d469e;
            line-height: 1.05;
            letter-spacing: -0.01em;
            margin-bottom: 0.08rem;
        }}

        .cv-status-note {{
            font-size: 0.78rem;
            color: #5f6f86;
            font-weight: 500;
            line-height: 1.15;
        }}
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Global Elements
# -----------------------------------------------------------------------------

# Logo da barra lateral
logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'cor-cultura viva.svg')
st.logo(logo_path, size='large')

# Dados para filtros globais (exceto Início)
df = preparar_base()


# -----------------------------------------------------------------------------
# Navigation
# -----------------------------------------------------------------------------
home_page = st.Page("paginas/0_Home.py", title="🏠 Início")
pages = {
    "Apresentação": [home_page],
    "Diagnóstico Econômico": [
        st.Page("paginas/1_Identificacao.py", title="A) Identificação"),
        st.Page("paginas/2_Atuacao_Cultural.py", title="B) Atuação Cultural"),
        st.Page("paginas/3_Acesso_Recursos.py", title="C) Acesso a Recursos"),
        st.Page("paginas/4_Acesso_Mercados.py", title="D) Acesso a Mercados"),
        st.Page("paginas/5_Infraestrutura_Gestao.py", title="E) Infraestrutura e Gestão"),
        st.Page("paginas/6_Articulacao_Rede.py", title="F) Articulação em Rede"),
    ],
    "Análise Avançada": [
        st.Page("paginas/7_Cruzamentos_Estrategicos.py", title="G) Cruzamentos Estratégicos"),
    ]
}

pg = st.navigation(pages)
is_home = pg.title == home_page.title

# Cabeçalho global (somente páginas internas)
if not is_home:
    header_path = os.path.join(os.path.dirname(__file__), 'assets', 'cor-completa.svg')
    col_sq1, col_sq2, col_sq3 = st.columns([1, 2, 1])
    with col_sq2:
        st.image(header_path, use_container_width=True)

# Filtros globais no topo (exceto Início)
if not is_home:
    renderizar_painel_filtros(df)
# Sidebar (Only Actions like PDF)
st.sidebar.divider()
st.sidebar.markdown("### Exportar")
if st.sidebar.button("🖨️ Baixar como PDF"):
    components.html(
        """
        <script>
            window.parent.print();
        </script>
        """,
        height=0,
        width=0
    )
st.sidebar.caption("Use 'Salvar como PDF' na janela de impressão.")
st.sidebar.divider()

pg.run()

