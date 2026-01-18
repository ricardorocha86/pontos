import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import CORES_GRAFICOS, PALETA_CORES
from dados import carregar_geojson_estados


def ajustar_layout(fig, titulo, altura=320):
    fig.update_layout(
        title=titulo,
        height=altura,
        margin=dict(l=10, r=80, t=50, b=10),
        legend_title_text='',
        bargap=0.25,
        font=dict(color=PALETA_CORES['cinza_escuro'])
    )
    return fig


def grafico_barras_series(serie, titulo, cor=None, horizontal=False, altura=320, mostrar_percentual=True):
    cor = cor or CORES_GRAFICOS[0]
    df = serie.reset_index()
    df.columns = ['categoria', 'valor']
    total = df['valor'].sum() if mostrar_percentual else None
    if horizontal:
        fig = px.bar(df, x='valor', y='categoria', orientation='h', color_discrete_sequence=[cor])
    else:
        fig = px.bar(df, x='categoria', y='valor', color_discrete_sequence=[cor])
    if mostrar_percentual and total:
        df['texto'] = df['valor'].apply(lambda v: f'{int(v)} ({(v / total) * 100:.1f}%)')
        fig.update_traces(text=df['texto'], textposition='outside', cliponaxis=False)
    else:
        fig.update_traces(text=df['valor'], textposition='outside', cliponaxis=False)
    fig.update_yaxes(title='')
    fig.update_xaxes(title='')
    return ajustar_layout(fig, titulo, altura=altura)


def grafico_donut(serie, titulo, altura=300):
    df = serie.reset_index()
    df.columns = ['categoria', 'valor']
    fig = px.pie(df, names='categoria', values='valor', hole=0.5, color_discrete_sequence=CORES_GRAFICOS)
    fig.update_traces(textposition='inside', textinfo='label+percent+value', insidetextorientation='horizontal')
    fig.update_layout(showlegend=False)
    return ajustar_layout(fig, titulo, altura=altura)


def grafico_mapa_estados(df, coluna_uf, coluna_valor, titulo, altura=520):
    geojson = carregar_geojson_estados()
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations=coluna_uf,
        featureidkey='properties.SIGLA',
        color=coluna_valor,
        color_continuous_scale=[PALETA_CORES['cinza_claro'], PALETA_CORES['azul_principal']],
        mapbox_style='carto-positron',
        zoom=3.2,
        center={'lat': -15, 'lon': -55},
        opacity=0.8
    )
    fig.update_traces(marker_line_width=0.4, marker_line_color='white')
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=altura,
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(title='Contagem', thickness=12, len=0.7)
    )
    fig.update_layout(title=titulo)
    return fig


def grafico_barras_empilhadas(df, x, y, grupo, titulo, altura=320):
    fig = px.bar(df, x=x, y=y, color=grupo, barmode='stack', color_discrete_sequence=CORES_GRAFICOS)
    fig.update_yaxes(title='')
    fig.update_xaxes(title='')
    return ajustar_layout(fig, titulo, altura=altura)


def grafico_treemap(df, caminho, valores, titulo, altura=420):
    fig = px.treemap(df, path=caminho, values=valores, color_discrete_sequence=CORES_GRAFICOS)
    return ajustar_layout(fig, titulo, altura=altura)


def grafico_boxplot(df, x, y, titulo, altura=320):
    fig = px.box(df, x=x, y=y, color_discrete_sequence=[PALETA_CORES['azul_principal']])
    fig.update_yaxes(title='')
    fig.update_xaxes(title='')
    return ajustar_layout(fig, titulo, altura=altura)

