import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import matplotlib
matplotlib.use('Agg')          # back-end sem janela
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
# Folium Imports
import folium
from folium.plugins import MarkerCluster

from mpl_toolkits.axes_grid1 import make_axes_locatable

from config import (CORES_GRAFICOS, PALETA_CORES, CORES_DINAMICAS,
                    FONTE_FAMILIA, FONTE_TAMANHOS, REGIOES_POR_UF)

# ---------------------------------------------------------------------------
# Layout-base global que Ã© aplicado em TODOS os grÃ¡ficos
# ---------------------------------------------------------------------------
_FONT_GLOBAL = dict(
    family=FONTE_FAMILIA,
    size=FONTE_TAMANHOS['geral'],
    color=CORES_DINAMICAS['cinza_escuro']
)
_TITLE_COLOR = '#2E435F'


def _aplicar_titulo_mapa(ax, titulo):
    ax.set_title(
        titulo,
        fontsize=FONTE_TAMANHOS['titulo'],
        fontweight='bold',
        color=_TITLE_COLOR,
        pad=10,
        loc='center',
    )


def mostrar_grafico(fig, subtitulo, config_extra=None, nota_rodape=None):
    if fig is None:
        return

    # Aplica fonte global + padroniza tÃ­tulo / legenda
    fig.update_layout(
        title=dict(
            text=subtitulo,
            font=dict(
                family=FONTE_FAMILIA,
                size=FONTE_TAMANHOS['titulo'],
                color=_TITLE_COLOR,
            ),
            y=0.98
        ),
        legend=dict(
            font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['legenda']),
            title=dict(font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['legenda_titulo']))
        ),
        font=_FONT_GLOBAL
    )

    # Garante que ticks e eixos tambÃ©m usem a fonte
    fig.update_xaxes(tickfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['tick']),
                     title_font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['eixo']))
    fig.update_yaxes(tickfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['tick']),
                     title_font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['eixo']))

    config = {
        'displayModeBar': 'hover',
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'zoom2d', 'pan2d', 'select2d', 'lasso2d',
            'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d',
            'hoverClosestCartesian', 'hoverCompareCartesian',
            'toggleSpikelines',
            'zoom3d', 'pan3d', 'orbitRotation', 'tableRotation', 'resetCameraDefault3d', 'resetCameraLastSave3d',
            'zoomInGeo', 'zoomOutGeo', 'resetGeo', 'hoverClosestGeo',
            'hoverClosestGl2d', 'hoverClosestPie',
            'resetViewMapbox',
            'toggleHover',
        ]
    }
    if config_extra:
        config.update(config_extra)

    st.plotly_chart(fig, use_container_width=True, config=config)

    if nota_rodape:
        st.caption(nota_rodape)


def ajustar_layout(fig, titulo, altura=400):
    fig.update_layout(
        title=dict(
            text=titulo,
            font=dict(
                family=FONTE_FAMILIA,
                size=FONTE_TAMANHOS['titulo'],
                color=_TITLE_COLOR,
            )
        ),
        height=altura,
        margin=dict(l=10, r=40, t=60, b=40),
        legend_title_text='',
        bargap=0.2,
        font=_FONT_GLOBAL
    )
    return fig


def grafico_barras_series(serie, titulo, cor=None, horizontal=False, altura=400, mostrar_percentual=True):
    # Ensure descending order
    serie = serie.sort_values(ascending=True if horizontal else False)

    cor = cor or CORES_GRAFICOS[0]
    df = serie.reset_index()
    df.columns = ['categoria', 'valor']

    total = df['valor'].sum() if mostrar_percentual else None

    # Create Frequency + Percentage text
    if mostrar_percentual and total:
        df['texto'] = df['valor'].apply(lambda v: f'{int(v)}<br>({(v / total) * 100:.1f}%)')
    else:
        df['texto'] = df['valor'].apply(lambda v: str(int(v)))

    if horizontal:
        fig = px.bar(df, x='valor', y='categoria', orientation='h', color_discrete_sequence=[cor])
        fig.update_traces(text=df['texto'], textposition='outside', cliponaxis=False)
        fig.update_traces(textfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['dado']))
    else:
        fig = px.bar(df, x='categoria', y='valor', color_discrete_sequence=[cor])
        fig.update_traces(text=df['texto'], textposition='outside', cliponaxis=False)
        fig.update_traces(textfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['dado']))

    fig.update_yaxes(title='')
    fig.update_xaxes(title='')

    return ajustar_layout(fig, titulo, altura=altura)


def grafico_donut(serie, titulo, altura=400):
    # Sort descending
    serie = serie.sort_values(ascending=False)

    df = serie.reset_index()
    df.columns = ['categoria', 'valor']

    fig = px.pie(
        df,
        names='categoria',
        values='valor',
        hole=0.6,
        color_discrete_sequence=CORES_GRAFICOS
    )

    total = df['valor'].sum()

    fig.update_traces(
        textposition='outside',
        textinfo='label+percent',
        insidetextorientation='horizontal',
        textfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['dado']),
        hovertemplate='%{label}<br>FrequÃªncia: %{value}<br>%{percent}'
    )

    fig.update_layout(showlegend=False)

    # Add total in center
    fig.add_annotation(
        text=f"Total<br>{int(total)}",
        x=0.5, y=0.5,
        font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['anotacao']),
        showarrow=False
    )

    return ajustar_layout(fig, titulo, altura=altura)


# ---------------------------------------------------------------------------
# Helpers para mapas matplotlib
# ---------------------------------------------------------------------------
_CAMINHO_GEOJSON = os.path.join(os.path.dirname(__file__), 'assets', 'br_states.json')

_CMAP_MAPA = LinearSegmentedColormap.from_list(
    'gradiente_mapa', ['#D6EAF8', '#042A68']
)

# UF para FK_macro  (mesmo esquema do GeoJSON)
_UF_PARA_MACRO = {
    'AC': 'N', 'AM': 'N', 'AP': 'N', 'PA': 'N', 'RO': 'N', 'RR': 'N', 'TO': 'N',
    'AL': 'NE', 'BA': 'NE', 'CE': 'NE', 'MA': 'NE', 'PB': 'NE',
    'PE': 'NE', 'PI': 'NE', 'RN': 'NE', 'SE': 'NE',
    'DF': 'CO', 'GO': 'CO', 'MT': 'CO', 'MS': 'CO',
    'ES': 'SE', 'MG': 'SE', 'RJ': 'SE', 'SP': 'SE',
    'PR': 'S', 'RS': 'S', 'SC': 'S'
}

_MACRO_PARA_NOME = {
    'N': 'Norte', 'NE': 'Nordeste', 'CO': 'Centro-Oeste',
    'SE': 'Sudeste', 'S': 'Sul'
}


@st.cache_data(show_spinner=False)
def _carregar_gdf_estados():
    """GeoDataFrame de estados a partir do GeoJSON local."""
    gdf = gpd.read_file(_CAMINHO_GEOJSON)
    gdf['SIGLA'] = gdf['SIGLA'].str.strip()
    return gdf


@st.cache_data(show_spinner=False)
def _carregar_gdf_municipios():
    """GeoDataFrame via geobr (cacheado)."""
    import geobr
    return geobr.read_municipality(year=2022)


# ---------------------------------------------------------------------------
# MAPA DE ESTADOS  (fiel ao referÃªncia)
# ---------------------------------------------------------------------------

# Ajustes de seta para estados pequenos (offsets em graus)
_AJUSTES_SETAS_ESTADOS = {
    'SE': (2.0, -1.0), 'AL': (2.2, -0.3),
    'PE': (3.0, 0.2),  'PB': (2.8, 1.0),
    'RN': (2.5, 1.8),  'ES': (2.2, -0.8),
    'RJ': (1.8, -1.5), 'DF': (1.5, -1.0),
    'SC': (1.2, -0.8)
}


def mapa_estados_matplotlib(df_contagem):
    """
    Mapa coroplÃ©tico de estados â€“ idÃªntico ao arquivo de referÃªncia.

    ParÃ¢metros
    ----------
    df_contagem : DataFrame com colunas ['uf', 'contagem'].
    """
    gdf = _carregar_gdf_estados().copy()

    total = df_contagem['contagem'].sum()
    df_contagem = df_contagem.copy()
    df_contagem['percentual'] = df_contagem['contagem'] / total

    mapa = gdf.merge(df_contagem, left_on='SIGLA', right_on='uf', how='left')

    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    ax.set_aspect('equal')

    # Barra de legenda curta e discreta (altura ~1/3 do mapa)
    cax = ax.inset_axes([1.01, 0.33, 0.02, 0.34])

    mapa.plot(
        column='percentual', cmap=_CMAP_MAPA, ax=ax, cax=cax,
        legend=True, edgecolor='gray', linewidth=0.5,
        vmin=0, vmax=max(0.16, mapa['percentual'].max() * 1.05),
        legend_kwds={'orientation': 'vertical',
                     'format': FuncFormatter(lambda x, _: f'{x*100:.0f}%')},
        missing_kwds={'color': '#F0F0F0', 'label': 'Sem dados'}
    )

    cax.tick_params(labelsize=10, length=2)
    _aplicar_titulo_mapa(ax, 'Distribuição dos Pontos de Cultura por Estado')
    ax.axis('off')

    # ---- rÃ³tulos ----
    mapa_proj = mapa.to_crs(epsg=5880)
    mapa['centroide'] = mapa_proj.geometry.centroid.to_crs(mapa.crs)

    for _, row in mapa.iterrows():
        if pd.isna(row.get('percentual')):
            continue
        sigla = row['SIGLA']
        pct = row['percentual']
        valor_fmt = f"{pct*100:.1f}%".replace('.', ',')
        x, y = row['centroide'].x, row['centroide'].y
        cor_texto = 'white' if pct > 0.09 else 'black'

        if sigla in _AJUSTES_SETAS_ESTADOS:
            off_x, off_y = _AJUSTES_SETAS_ESTADOS[sigla]
            ax.annotate(
                text=f"{sigla}\n{valor_fmt}",
                xy=(x, y), xytext=(x + off_x, y + off_y),
                arrowprops=dict(arrowstyle='-', color='black', linewidth=0.8),
                ha='center', va='center',
                fontsize=11, fontweight='bold', color='black'
            )
        else:
            ax.text(x, y, f"{sigla}\n{valor_fmt}",
                    ha='center', va='center',
                    fontsize=11, fontweight='bold', color=cor_texto)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# MAPA DE REGIÃ•ES  (fiel ao referÃªncia)
# ---------------------------------------------------------------------------
def mapa_regioes_matplotlib(df_contagem_regiao):
    """
    Mapa coroplÃ©tico por regiÃ£o â€“ dissolve estados.

    ParÃ¢metros
    ----------
    df_contagem_regiao : DataFrame com colunas ['regiao', 'contagem'].
    """
    gdf = _carregar_gdf_estados().copy()

    total = df_contagem_regiao['contagem'].sum()
    df_contagem_regiao = df_contagem_regiao.copy()
    df_contagem_regiao['percentual'] = df_contagem_regiao['contagem'] / total

    # mapear sigla â†’ nome da regiÃ£o
    gdf['regiao_nome'] = gdf['SIGLA'].map(
        {k: REGIOES_POR_UF.get(k, '') for k in gdf['SIGLA']}
    )

    # correÃ§Ã£o de topologia:  projetar â†’ buffer â†’ dissolve â†’ voltar
    gdf_temp = gdf.to_crs(epsg=5880)
    gdf_temp['geometry'] = gdf_temp.geometry.buffer(500)
    gdf_regioes = gdf_temp.dissolve(by='regiao_nome').reset_index()
    gdf_regioes = gdf_regioes.to_crs(epsg=4326)

    mapa = gdf_regioes.merge(df_contagem_regiao,
                              left_on='regiao_nome', right_on='regiao')

    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    ax.set_aspect('equal')

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='4%', pad=0.1)

    mapa.plot(
        column='percentual', cmap=_CMAP_MAPA, ax=ax, cax=cax,
        legend=True, edgecolor='gray', linewidth=1.2,
        legend_kwds={'orientation': 'vertical',
                     'format': FuncFormatter(lambda x, _: f'{x*100:.1f}%')}
    )

    cax.tick_params(labelsize=12)
    _aplicar_titulo_mapa(ax, 'Distribuição dos Pontos de Cultura por Região')
    ax.axis('off')

    # ---- rÃ³tulos ----
    mapa_proj = mapa.to_crs(epsg=5880)
    mapa['ponto_central'] = mapa_proj.geometry.representative_point().to_crs(mapa.crs)

    for _, row in mapa.iterrows():
        nome = row['regiao_nome'].upper()
        valor = f"{row['percentual']*100:.1f}%".replace('.', ',')
        cor = 'white' if row['percentual'] > 0.18 else 'black'

        ax.text(
            row['ponto_central'].x, row['ponto_central'].y,
            f"{nome}\n{valor}",
            ha='center', va='center',
            fontsize=14, fontweight='bold', color=cor
        )

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# MAPA DE MUNICÃPIOS  (fiel ao referÃªncia â€“ 3 camadas)
# ---------------------------------------------------------------------------
def mapa_municipios_matplotlib(df_contagem_cidades):
    """
    Mapa coroplÃ©tico por municÃ­pio â€“ 3 camadas (fundo estadual,
    municÃ­pios, bordas estaduais).

    ParÃ¢metros
    ----------
    df_contagem_cidades : DataFrame com colunas ['cidade', 'contagem'].
    """
    gdf_estados = _carregar_gdf_estados().copy()
    gdf_mun = _carregar_gdf_municipios().copy()

    total = df_contagem_cidades['contagem'].sum()
    df_contagem_cidades = df_contagem_cidades.copy()
    df_contagem_cidades['percentual'] = df_contagem_cidades['contagem'] / total

    mapa_mun = gdf_mun.merge(
        df_contagem_cidades,
        left_on='name_muni', right_on='cidade',
        how='left'
    )

    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    ax.set_aspect('equal')

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.1)

    formatter = FuncFormatter(lambda x, _: f'{x*100:.2f}%')

    # CAMADA 1 â€“ estados como fundo cinza
    gdf_estados.plot(ax=ax, color='#F0F0F0', edgecolor='gray',
                     linewidth=0.5, zorder=1)

    # CAMADA 2 â€“ municÃ­pios (dados)
    mapa_mun.plot(
        column='percentual', cmap=_CMAP_MAPA, ax=ax, cax=cax,
        legend=True, zorder=2,
        linewidth=0.01, edgecolor='white',
        legend_kwds={'orientation': 'vertical', 'format': formatter},
        missing_kwds={'color': 'white', 'edgecolor': 'black',
                      'label': 'Sem dados'}
    )

    cax.tick_params(labelsize=14)

    # CAMADA 3 â€“ bordas estaduais por cima
    gdf_estados.plot(ax=ax, facecolor='none', edgecolor='gray',
                     linewidth=1.0, zorder=3)

    _aplicar_titulo_mapa(ax, 'Pontos de Cultura por Município')
    ax.axis('off')

    plt.tight_layout()
    return fig


def grafico_barras_empilhadas(df, x, y, grupo, titulo, altura=400):
    fig = px.bar(df, x=x, y=y, color=grupo, barmode='stack', color_discrete_sequence=CORES_GRAFICOS)
    fig.update_yaxes(title='')
    fig.update_xaxes(title='')
    fig.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['legenda'])
    ))
    return ajustar_layout(fig, titulo, altura=altura)


def grafico_boxplot(df, x, y, titulo, altura=400):
    fig = px.box(df, x=x, y=y, color_discrete_sequence=[CORES_DINAMICAS['azul_principal']])
    fig.update_yaxes(title='')
    fig.update_xaxes(title='')
    return ajustar_layout(fig, titulo, altura=altura)


def mapa_pontos_matplotlib(df_pontos, titulo='Distribuição nacional dos Pontos e Pontões de Cultura'):
    """
    Mapa estatico com o Brasil e marcadores de Pontos/Pontoes.
    """
    gdf_estados = _carregar_gdf_estados().copy()

    if 'latitude' in df_pontos.columns and 'longitude' in df_pontos.columns:
        df_valid = df_pontos.dropna(subset=['latitude', 'longitude']).copy()
        df_valid['latitude'] = pd.to_numeric(df_valid['latitude'], errors='coerce')
        df_valid['longitude'] = pd.to_numeric(df_valid['longitude'], errors='coerce')
        df_valid = df_valid.dropna(subset=['latitude', 'longitude'])
    else:
        df_valid = pd.DataFrame()

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_aspect('equal')
    ax.set_facecolor('#FBFDFF')

    gdf_estados.plot(ax=ax, color='#EEF3FA', edgecolor='#A9B8CC', linewidth=0.7, zorder=1)

    if not df_valid.empty:
        tipo_raw = df_valid.get('tipo_ponto', 'Ponto').fillna('Ponto').astype(str)
        tipo_norm = tipo_raw.str.lower().str.strip()
        eh_pontao = tipo_norm.str.contains('pont') & (~tipo_norm.str.fullmatch(r'ponto'))

        df_ponto = df_valid[~eh_pontao]
        df_pontao = df_valid[eh_pontao]

        cor_ponto = CORES_DINAMICAS['azul_principal']
        cor_pontao = CORES_DINAMICAS['vermelho_principal']

        if not df_ponto.empty:
            ax.scatter(
                df_ponto['longitude'],
                df_ponto['latitude'],
                s=110,
                c=cor_ponto,
                alpha=0.18,
                zorder=2,
                edgecolors='none'
            )
            ax.scatter(
                df_ponto['longitude'],
                df_ponto['latitude'],
                s=26,
                c=cor_ponto,
                alpha=0.95,
                zorder=4,
                edgecolors='white',
                linewidths=0.9
            )

        if not df_pontao.empty:
            ax.scatter(
                df_pontao['longitude'],
                df_pontao['latitude'],
                s=150,
                c=cor_pontao,
                alpha=0.18,
                zorder=3,
                edgecolors='none'
            )
            ax.scatter(
                df_pontao['longitude'],
                df_pontao['latitude'],
                s=78,
                marker='*',
                c=cor_pontao,
                alpha=0.98,
                zorder=5,
                edgecolors='white',
                linewidths=0.9
            )

    _aplicar_titulo_mapa(ax, titulo)
    ax.axis('off')

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Ponto de Cultura',
               markerfacecolor=CORES_DINAMICAS['azul_principal'],
               markeredgecolor='white', markeredgewidth=1.0, markersize=9),
        Line2D([0], [0], marker='*', color='w', label='Pontão de Cultura',
               markerfacecolor=CORES_DINAMICAS['vermelho_principal'],
               markeredgecolor='white', markeredgewidth=1.0, markersize=12)
    ]
    ax.legend(
        handles=legend_elements,
        loc='upper right',
        bbox_to_anchor=(0.99, 0.99),
        frameon=False,
        handlelength=1.2,
    )

    plt.tight_layout()
    return fig

def mapa_pontos_cluster_folium(df_pontos):
    """
    Mapa interativo com agrupamento (Cluster) usando Folium.
    Retorna o objeto Map.
    """
    # 1. Preparar Dados
    if 'latitude' in df_pontos.columns and 'longitude' in df_pontos.columns:
        df_valid = df_pontos.dropna(subset=['latitude', 'longitude']).copy()
        df_valid['latitude'] = pd.to_numeric(df_valid['latitude'], errors='coerce')
        df_valid['longitude'] = pd.to_numeric(df_valid['longitude'], errors='coerce')
        df_valid = df_valid.dropna(subset=['latitude', 'longitude'])
    else:
        return None

    # 2. Criar Mapa Base (Centro do Brasil)
    # Tiles: CartoDB positron (clean), OpenStreetMap, etc.
    m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4, tiles='CartoDB positron')

    # 3. Criar Cluster
    marker_cluster = MarkerCluster().add_to(m)

    # 4. Adicionar Marcadores
    # Cores personalizadas
    cor_ponto = CORES_DINAMICAS['azul_principal'] # '#0749AB'
    cor_pontao = CORES_DINAMICAS['vermelho_principal'] # '#E43C2F'

    for _, row in df_valid.iterrows():
        # ConteÃºdo do Popup e Tooltip
        # Tenta pegar o nome da coluna correta
        col_nome = '1.1 Nome do Ponto/PontÃ£o de Cultura:'
        nome = str(row.get(col_nome, row.get('Nome do Ponto de Cultura', 'Ponto Sem Nome')))
        cidade = str(row.get('cidade', ''))
        uf = str(row.get('uf', ''))
        tipo = str(row.get('tipo_ponto', 'Ponto'))
        
        # HTML Simples no Popup
        popup_html = f"<b>{nome}</b><br>{cidade}-{uf}<br><i>{tipo}</i>"
        
        # Estilo "BotÃ£o Bonito": CÃ­rculo SÃ³lido com Borda Branca
        # Usar cores HEX oficiais do projeto
        cor_hex = cor_pontao if tipo == 'PontÃ£o' else cor_ponto
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=nome,          # Exibe nome ao repousar mouse (hover)
            radius=8,              # Maior para parecer um botÃ£o
            color='#FFFFFF',       # Borda branca (destaque)
            weight=2,              # Largura da borda
            fill=True,
            fill_color=cor_hex,    # Cor interna oficial
            fill_opacity=1.0,      # SÃ³lido
        ).add_to(marker_cluster)

    return m


