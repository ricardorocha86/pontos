import json
import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from config import ESTADO_NOME_PARA_SIGLA, REGIOES_POR_UF

FAIXAS_RECEITA = [
    'Não teve receita',
    'Menor que 15.000',
    '15.001 a 50.000',
    '50.001 a 100.000',
    '100.001 a 150.000',
    '150.001 a 200.000',
    '200.001 a 250.000',
    '250.001 a 300.000',
    '300.001 a 350.000',
    '350.001 a 400.000',
    'Maior que 400.000'
]

ACOES_ESTRUTURANTES = [
    'Sem ação estruturante',
    'Agente cultura viva',
    'Conhecimentos tradicionais',
    'Cultura Hip Hop',
    'Cultura Alimentar',
    'Cultura Circense',
    'Cultura Digital',
    'Cultura e Mulheres',
    'Cultura e Territórios Rurais',
    'Cultura e Direitos Humanos',
    'Cultura e Educação',
    'Cultura e Juventude',
    'Cultura e Meio Ambiente',
    'Cultura e Saúde',
    'Cultura Urbana e Direito à Cidade',
    'Cultura, Territórios de Fronteira e Integração Latino-americana',
    'Cultura, Comunicação e Mídia livre',
    'Cultura, Infância e Adolescência',
    'Culturas Populares',
    'Culturas Tradicionais',
    'Culturas de Matriz Africana',
    'Culturas Indígenas',
    'Economia criativa e solidária',
    'Gênero e Diversidade',
    'Intercâmbio e residências',
    'Linguagens Artísticas',
    'Livro, leitura e literatura',
    'Memória e Patrimônio cultural',
    'Mestres e Mestras das Culturas Tradicionais e Populares',
    'Acessibilidade Cultural e Equidade',
    'Outras ações estruturantes'
]


def normalizar_texto(texto):
    texto = '' if texto is None else str(texto)
    texto = texto.replace('\ufb01', 'fi').replace('\ufb02', 'fl').replace('�', ' ')
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'\s+', ' ', texto).strip().lower()
    return texto


def separar_marcacoes(texto):
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return []
    texto = str(texto)
    partes = [p.strip() for p in texto.split(',') if p.strip()]
    return partes


def corrigir_texto_quebra(texto):
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return texto
    texto = str(texto)
    try:
        texto = texto.encode('latin1').decode('utf-8')
    except Exception:
        texto = texto
    return texto


def encontrar_coluna(colunas, texto_alvo):
    alvo = normalizar_texto(texto_alvo)
    for coluna in colunas:
        if normalizar_texto(coluna) == alvo:
            return coluna
    for coluna in colunas:
        if alvo in normalizar_texto(coluna):
            return coluna
    return None


def para_bool(serie):
    if serie is None:
        return pd.Series(dtype=bool)
    if serie.dtype == bool:
        return serie.fillna(False)
    if serie.dtype == object:
        return serie.fillna('').astype(str).str.strip().str.lower().isin(['sim', 'true', '1', 'yes'])
    return serie.fillna(0).astype(float).astype(int).astype(bool)


def classificar_rural_urbano(populacao):
    if pd.isna(populacao):
        return 'Sem dado'
    return 'Urbano' if populacao > 50000 else 'Rural'


@st.cache_data(show_spinner=False)
def carregar_base():
    return pd.read_csv('base_final.csv', low_memory=False, encoding='utf-8-sig')


@st.cache_data(show_spinner=False)
def preparar_base(versao_cache='v2'):
    df = carregar_base().copy()
    df.columns = [str(c) for c in df.columns]

    col_estado = encontrar_coluna(df.columns, 'Estado')
    col_cidade = encontrar_coluna(df.columns, 'Cidade')
    col_cidade_api = encontrar_coluna(df.columns, 'cidade_api')
    col_pontao = encontrar_coluna(df.columns, 'Pontão')
    col_registro = encontrar_coluna(df.columns, 'Registro')
    col_regiao = encontrar_coluna(df.columns, 'regiao')
    col_linguagem = encontrar_coluna(df.columns, '11. Se o Ponto de Cultura trabalha com linguagens artísticas, indique qual a predominante:')
    col_receita = encontrar_coluna(df.columns, 'Receita anual')
    col_rec_federal = encontrar_coluna(df.columns, '14. 1. Se sim, quais? (Recursos Federais)')
    col_rec_estadual = encontrar_coluna(df.columns, '14. 1. Se sim, quais? (Recursos Estaduais)')
    col_rec_municipal = encontrar_coluna(df.columns, '14. 1. Se sim, quais? (Recursos Municipais)')
    col_rec_minc = encontrar_coluna(df.columns, 'Recursos federais (Editais Ministério da Cultura)')
    col_pnab_estadual = encontrar_coluna(df.columns, 'Recursos federais (Editais estaduais da PNAB (Política Nacional Aldir Blanc de Fomento à Cultura))')
    col_pnab_municipal = encontrar_coluna(df.columns, 'Recursos federais (Editais municipais da PNAB (Política Nacional Aldir Blanc de Fomento à Cultura))')
    col_tcc_est_ponto = encontrar_coluna(df.columns, 'RF-PNAB Indique qual modalidade: (Termo de Compromisso Cultural (TCC) de Ponto de Cultura)')
    col_tcc_est_pontao = encontrar_coluna(df.columns, 'RF-PNAB Indique qual modalidade: (Termo de Compromisso Cultural (TCC) de Pontão de Cultura)')
    col_tcc_mun_ponto = encontrar_coluna(df.columns, 'Indique qual modalidade de edital municipal da PNAB: (Termo de Compromisso Cultural (TCC) de Ponto de Cultura)')
    col_tcc_mun_pontao = encontrar_coluna(df.columns, 'Indique qual modalidade de edital municipal da PNAB: (Termo de Compromisso Cultural (TCC) de Pontão de Cultura)')

    df['estado'] = df[col_estado] if col_estado else np.nan
    df['cidade'] = df[col_cidade_api] if col_cidade_api else (df[col_cidade] if col_cidade else np.nan)
    df['regiao'] = df[col_regiao] if col_regiao else df['estado'].map(lambda x: REGIOES_POR_UF.get(ESTADO_NOME_PARA_SIGLA.get(normalizar_texto(x), ''), np.nan))
    df['uf'] = df['estado'].map(lambda x: ESTADO_NOME_PARA_SIGLA.get(normalizar_texto(x), x))
    df['tipo_ponto'] = df[col_pontao].apply(lambda x: 'Pontão' if str(x).strip().lower() == 'sim' else 'Ponto') if col_pontao else np.nan
    df['registro'] = df[col_registro] if col_registro else np.nan
    df['linguagem_artistica'] = df[col_linguagem] if col_linguagem else np.nan
    df['linguagens_lista'] = df['linguagem_artistica'].apply(separar_marcacoes)
    df['rec_federal'] = para_bool(df[col_rec_federal]) if col_rec_federal else False
    df['rec_estadual'] = para_bool(df[col_rec_estadual]) if col_rec_estadual else False
    df['rec_municipal'] = para_bool(df[col_rec_municipal]) if col_rec_municipal else False
    df['rec_minc'] = para_bool(df[col_rec_minc]) if col_rec_minc else False
    df['pnab_estadual'] = para_bool(df[col_pnab_estadual]) if col_pnab_estadual else False
    df['pnab_municipal'] = para_bool(df[col_pnab_municipal]) if col_pnab_municipal else False
    df['tcc_est_ponto'] = para_bool(df[col_tcc_est_ponto]) if col_tcc_est_ponto else False
    df['tcc_est_pontao'] = para_bool(df[col_tcc_est_pontao]) if col_tcc_est_pontao else False
    df['tcc_mun_ponto'] = para_bool(df[col_tcc_mun_ponto]) if col_tcc_mun_ponto else False
    df['tcc_mun_pontao'] = para_bool(df[col_tcc_mun_pontao]) if col_tcc_mun_pontao else False

    if col_receita:
        df['faixa_receita'] = df[col_receita].replace({'O Ponto de Cultura não teve receita em 2024': 'Não teve receita'})
    else:
        df['faixa_receita'] = np.nan

    df['populacao'] = pd.to_numeric(df.get('populacao'), errors='coerce')
    df['faixa_populacional'] = df.get('faixa_populacional').apply(corrigir_texto_quebra)
    df['classificacao_rural_urbana'] = df['populacao'].apply(classificar_rural_urbano)
    return df


def aplicar_filtros(df, filtros):
    filtrado = df.copy()
    if filtros.get('estado'):
        filtrado = filtrado[filtrado['estado'].isin(filtros['estado'])]
    if filtros.get('regiao'):
        filtrado = filtrado[filtrado['regiao'].isin(filtros['regiao'])]
    if filtros.get('faixa_populacional'):
        filtrado = filtrado[filtrado['faixa_populacional'].isin(filtros['faixa_populacional'])]
    if filtros.get('classificacao_rural_urbana'):
        filtrado = filtrado[filtrado['classificacao_rural_urbana'].isin(filtros['classificacao_rural_urbana'])]
    if filtros.get('tipo_ponto'):
        filtrado = filtrado[filtrado['tipo_ponto'].isin(filtros['tipo_ponto'])]
    if filtros.get('registro'):
        filtrado = filtrado[filtrado['registro'].isin(filtros['registro'])]
    if filtros.get('faixa_receita'):
        filtrado = filtrado[filtrado['faixa_receita'].isin(filtros['faixa_receita'])]
    if filtros.get('linguagem_artistica'):
        selecionadas = set(filtros['linguagem_artistica'])
        filtrado = filtrado[filtrado['linguagens_lista'].apply(lambda itens: any(i in selecionadas for i in itens))]

    if filtros.get('acoes_estruturantes'):
        colunas_acao = [c for c in ACOES_ESTRUTURANTES if c in filtrado.columns]
        if colunas_acao:
            selecionadas = filtros['acoes_estruturantes']
            mascara = False
            for coluna in colunas_acao:
                if coluna in selecionadas:
                    mascara = mascara | para_bool(filtrado[coluna])
            filtrado = filtrado[mascara]

    for chave, coluna in filtros.get('filtros_booleanos', {}).items():
        if coluna in filtrado.columns and filtros.get(chave) in ['Sim', 'Não']:
            valor = filtros[chave] == 'Sim'
            filtrado = filtrado[para_bool(filtrado[coluna]) == valor]
    return filtrado


@st.cache_data(show_spinner=False)
def carregar_geojson_estados():
    with open('assets/br_states.json', 'r', encoding='utf-8') as arquivo:
        return json.load(arquivo)

