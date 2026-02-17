import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from components import (
    grafico_barras_series,
    grafico_donut,
    mapa_estados_matplotlib,
    mapa_municipios_matplotlib,
    mapa_regioes_matplotlib,
    mostrar_grafico,
)
from config import ESTADO_NOME_PARA_SIGLA, PALETA_CORES
from utils import aplicar_filtros, encontrar_coluna, normalizar_texto, preparar_base

st.title("A) Identificação")

st.markdown(
    """
A cultura deve ser vista como recurso estratégico para desenvolvimento social e econômico.
Nesta página, apresentamos a distribuição territorial da rede e os principais sinais de estrutura institucional e comunicação digital.
"""
)

_df = preparar_base()
if 'filtros_globais' in st.session_state:
    _df = aplicar_filtros(_df, st.session_state['filtros_globais'])


def _serie_texto_normalizado(serie):
    return serie.fillna('').astype(str).str.lower().str.strip()


def _contagem_estado_para_mapa(df):
    if 'uf_api' in df.columns:
        uf = df['uf_api'].fillna('').astype(str).str.upper().str.strip()
    elif 'uf' in df.columns:
        uf = df['uf'].fillna('').astype(str).str.upper().str.strip()
    else:
        uf = pd.Series([''] * len(df), index=df.index)

    invalida = (uf.str.len() != 2) | (~uf.str.match(r'^[A-Z]{2}$'))
    if invalida.any() and 'estado' in df.columns:
        uf_estado = df.loc[invalida, 'estado'].map(
            lambda x: ESTADO_NOME_PARA_SIGLA.get(normalizar_texto(x), '')
        )
        uf.loc[invalida] = uf_estado.fillna('')

    uf = uf[uf.str.match(r'^[A-Z]{2}$', na=False)]
    contagem = uf.value_counts().reset_index()
    contagem.columns = ['uf', 'contagem']
    return contagem


def _serie_tipo_ponto(df):
    if 'tipo_ponto' not in df.columns or df.empty:
        return pd.Series(dtype=int)

    tipo = df['tipo_ponto'].fillna('Ponto').astype(str).str.lower().str.strip()
    eh_pontao = tipo.str.contains('pont') & (~tipo.str.fullmatch(r'ponto'))
    serie = pd.Series({'Ponto': int((~eh_pontao).sum()), 'Pontão': int(eh_pontao.sum())})
    return serie[serie > 0]


def _serie_registro(df):
    if 'registro' not in df.columns or df.empty:
        return pd.Series(dtype=int)

    reg = df['registro'].fillna('').astype(str).str.upper()
    serie = pd.Series(
        {
            'Pessoa Jurídica (CNPJ)': int(reg.str.contains('CNPJ').sum()),
            'Coletivo (CPF)': int(reg.str.contains('CPF').sum()),
        }
    )
    return serie[serie > 0]


def _classificar_presenca_digital(df, coluna_rede):
    texto = _serie_texto_normalizado(df[coluna_rede])

    padrao_endereco = (
        r'\b(?:alameda|travessa|rodovia|estrada|praca|pra\.|bloco|casa|edificio|'
        r'distrito|zona rural|andar|fundos|apartamento|vila|rua|avenida|av\.)\b'
    )

    mask_endereco = texto.str.contains(padrao_endereco, regex=True)
    mask_instagram = texto.str.contains(r'instagram|insta\b|instagr\.am', regex=True)
    mask_facebook = texto.str.contains(r'facebook|fb\.me|fb\.com', regex=True)
    mask_youtube = texto.str.contains(r'youtube|youtu\.be|\byt\b|canal', regex=True)
    mask_tiktok = texto.str.contains(r'tiktok|tik\s*tok', regex=True)
    mask_twitter = texto.str.contains(r'twitter|x\.com', regex=True)

    mask_arroba = texto.str.contains(r'(?<![\w\.-])@[a-z0-9_]{2,}(?![\w@\.-])', regex=True)
    mask_redes_especificas = mask_instagram | mask_facebook | mask_youtube | mask_tiktok | mask_twitter
    mask_arroba_isolado = mask_arroba & (~mask_redes_especificas)

    mask_qualquer = (
        mask_endereco
        | mask_instagram
        | mask_facebook
        | mask_youtube
        | mask_tiktok
        | mask_twitter
        | mask_arroba_isolado
    )
    mask_adversa = (texto != '') & (~mask_qualquer)

    contagens = pd.Series(
        {
            'Instagram': int(mask_instagram.sum()),
            'Menções a @': int(mask_arroba_isolado.sum()),
            'Facebook': int(mask_facebook.sum()),
            'Endereços físicos': int(mask_endereco.sum()),
            'Respostas adversas': int(mask_adversa.sum()),
            'YouTube': int(mask_youtube.sum()),
            'TikTok': int(mask_tiktok.sum()),
            'Twitter/X': int(mask_twitter.sum()),
        }
    )
    return contagens[contagens > 0]


if _df.empty:
    st.warning('Sem dados para os filtros selecionados.')
else:
    visao = st.radio(
        'visao_territorial',
        ['Por Estado', 'Por Região', 'Por Município'],
        horizontal=True,
        label_visibility='collapsed',
    )

    col_mapa, col_lateral = st.columns([1.6, 1.4])

    with col_mapa:
        if visao == 'Por Estado':
            contagem_estado = _contagem_estado_para_mapa(_df)
            if contagem_estado.empty:
                st.info('Sem UFs válidas para renderizar o mapa estadual.')
            else:
                fig_mapa = mapa_estados_matplotlib(contagem_estado)
                st.pyplot(fig_mapa, use_container_width=True)
                plt.close(fig_mapa)

        elif visao == 'Por Região':
            contagem_regiao = _df['regiao'].value_counts().reset_index()
            contagem_regiao.columns = ['regiao', 'contagem']
            fig_mapa = mapa_regioes_matplotlib(contagem_regiao)
            st.pyplot(fig_mapa, use_container_width=True)
            plt.close(fig_mapa)

        else:
            contagem_cidades = _df['cidade'].value_counts().reset_index()
            contagem_cidades.columns = ['cidade', 'contagem']
            fig_mapa = mapa_municipios_matplotlib(contagem_cidades)
            st.pyplot(fig_mapa, use_container_width=True)
            plt.close(fig_mapa)

    with col_lateral:
        p1, p2 = st.columns(2)

        with p1:
            serie_registro = _serie_registro(_df)
            if not serie_registro.empty:
                fig_registro = grafico_donut(serie_registro, 'CNPJ x CPF', altura=300)
                fig_registro.update_traces(textposition='inside', textinfo='percent')
                fig_registro.update_layout(
                    showlegend=True,
                    margin=dict(l=8, r=8, t=56, b=8),
                    legend=dict(orientation='h', y=-0.12, x=0.0),
                )
                mostrar_grafico(fig_registro, 'CNPJ x CPF')
            else:
                st.info('Sem dados de CNPJ/CPF.')

        with p2:
            serie_tipo = _serie_tipo_ponto(_df)
            if not serie_tipo.empty:
                fig_tipo = grafico_donut(serie_tipo, 'Ponto x Pontão', altura=300)
                fig_tipo.update_traces(textposition='inside', textinfo='percent')
                fig_tipo.update_layout(
                    showlegend=True,
                    margin=dict(l=8, r=8, t=56, b=8),
                    legend=dict(orientation='h', y=-0.12, x=0.0),
                )
                mostrar_grafico(fig_tipo, 'Ponto x Pontão')
            else:
                st.info('Sem dados de tipo de ponto.')

        col_rede = encontrar_coluna(_df.columns, 'Endereço da rede social do Ponto de Cultura')
        if col_rede:
            redes = _classificar_presenca_digital(_df, col_rede).sort_values(ascending=True)
            if not redes.empty:
                fig_redes = grafico_barras_series(
                    redes,
                    'Canais de Comunicação Declarados',
                    cor=PALETA_CORES['secundarias'][1],
                    horizontal=True,
                    altura=360,
                    mostrar_percentual=True,
                )
                mostrar_grafico(fig_redes, 'Canais de Comunicação Declarados')
            else:
                st.info('Nenhuma rede social identificada nos filtros atuais.')
        else:
            st.info('Coluna de presença digital não encontrada na base.')

