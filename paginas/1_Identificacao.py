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
from config import PALETA_CORES
from utils import aplicar_filtros, encontrar_coluna, preparar_base

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
    if 'uf_api' not in df.columns:
        return pd.DataFrame(columns=['uf', 'contagem'])
    uf = df['uf_api'].fillna('').astype(str).str.upper().str.strip()

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
    s = df[coluna_rede].fillna('').astype(str).str.lower()

    termos_endereco = [
        'rua', 'av', 'avenida', 'cep', 'quadra', 'lote', 'bairro', 'alameda',
        'travessa', 'rodovia', 'estrada', 'praça', 'bloco', 'casa', 'edifício',
        'distrito', 'zona rural', 'andar', 'fundos', 'apartamento', 'vila'
    ]
    regex_endereco = r'\b(?:' + '|'.join(termos_endereco) + r')\b'

    redes_regex = {
        'Instagram': r'instagram\.com|instagr\.am|\binstagram\b|\binsta\b|\big\b',
        'Facebook': r'facebook\.com|fb\.com|fb\.me|\bfacebook\b|\bface\b|\bfb\b',
        'YouTube': r'youtube\.com|youtu\.be|\byoutube\b|\byt\b|\bcanal\b',
        'TikTok': r'tiktok\.com|\btiktok\b|\btk\b',
        'Twitter/X': r'twitter\.com|x\.com|\btwitter\b|\bx\b',
    }

    regex_handle = r'(?<!\w)@[\w.]+(?!\w)'

    resultados = pd.DataFrame(index=df.index)
    resultados['Endereço_Fisico'] = s.str.contains(regex_endereco, regex=True)

    foi_capturado = resultados['Endereço_Fisico'].copy()

    for rede, padrao in redes_regex.items():
        match = s.str.contains(padrao, regex=True)
        resultados[rede] = match
        foi_capturado |= match

    resultados['Handle_Generico'] = s.str.contains(regex_handle, regex=True) & ~foi_capturado
    foi_capturado |= resultados['Handle_Generico']

    resultados['Respostas_Adversas'] = ~foi_capturado & (s != '')

    contagem = resultados.sum()
    contagens = pd.Series(
        {
            'Instagram': int(contagem.get('Instagram', 0)),
            'Menções a @': int(contagem.get('Handle_Generico', 0)),
            'Facebook': int(contagem.get('Facebook', 0)),
            'Endereços físicos': int(contagem.get('Endereço_Fisico', 0)),
            'Respostas adversas': int(contagem.get('Respostas_Adversas', 0)),
            'YouTube': int(contagem.get('YouTube', 0)),
            'TikTok': int(contagem.get('TikTok', 0)),
            'Twitter/X': int(contagem.get('Twitter/X', 0)),
        }
    )
    return contagens[contagens > 0]


def _aplicar_layout_donut_identificacao(fig):
    fig.update_traces(textposition='inside', textinfo='percent')
    fig.update_layout(
        showlegend=True,
        margin=dict(l=8, r=8, t=56, b=96),
        legend=dict(
            orientation='v',
            yanchor='top',
            y=-0.14,
            xanchor='left',
            x=0.0,
        ),
    )
    return fig


if _df.empty:
    st.warning('Sem dados para os filtros selecionados.')
else:
    opcoes_visao = ['Por Estado', 'Por Região', 'Por Município']
    chave_visao = 'visao_territorial_mapa_identificacao'

    if chave_visao not in st.session_state:
        visao_inicial = st.session_state.get('visao_territorial', opcoes_visao[0])
        st.session_state[chave_visao] = visao_inicial if visao_inicial in opcoes_visao else opcoes_visao[0]

    visao = st.session_state[chave_visao]

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
            with st.spinner('Montando mapa municipal...', show_time=True):
                contagem_cidades = _df['cidade'].value_counts().reset_index()
                contagem_cidades.columns = ['cidade', 'contagem']
                fig_mapa = mapa_municipios_matplotlib(contagem_cidades)
            st.pyplot(fig_mapa, use_container_width=True)
            plt.close(fig_mapa)

        st.radio(
            'Visualização territorial do mapa',
            opcoes_visao,
            key=chave_visao,
            horizontal=True,
            label_visibility='collapsed',
        )

    with col_lateral:
        p1, p2 = st.columns(2)

        with p1:
            serie_registro = _serie_registro(_df)
            if not serie_registro.empty:
                fig_registro = grafico_donut(serie_registro, 'CNPJ x CPF', altura=300)
                fig_registro = _aplicar_layout_donut_identificacao(fig_registro)
                mostrar_grafico(fig_registro, 'CNPJ x CPF')
            else:
                st.info('Sem dados de CNPJ/CPF.')

        with p2:
            serie_tipo = _serie_tipo_ponto(_df)
            if not serie_tipo.empty:
                fig_tipo = grafico_donut(serie_tipo, 'Ponto x Pontão', altura=300)
                fig_tipo = _aplicar_layout_donut_identificacao(fig_tipo)
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



