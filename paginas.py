import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb, n_colors

from config import CORES_GRAFICOS, ORDEM_FAIXA_POPULACIONAL, PALETA_CORES
from dados import (
    ACOES_ESTRUTURANTES,
    FAIXAS_RECEITA,
    aplicar_filtros,
    encontrar_coluna,
    normalizar_texto,
    para_bool,
    preparar_base
)
from graficos import grafico_barras_series, grafico_boxplot, grafico_donut, grafico_mapa_estados

CAMINHO_CABECALHO = 'assets/cabeçalho.png'


def mostrar_cabecalho():
    st.image(CAMINHO_CABECALHO, width=720)


def mostrar_grafico(fig, subtitulo, config_extra=None):
    if subtitulo and (not fig.layout.title or not fig.layout.title.text):
        fig.update_layout(title=dict(text=subtitulo, y=0.98))
    config = {'displayModeBar': True, 'displaylogo': False}
    if config_extra:
        config.update(config_extra)
    st.plotly_chart(fig, use_container_width=True, config=config)


def grafico_abrangencia_empilhado(filtrado):
    dicionario = {
        '9. Municipal': 'Municipal',
        '9. Regional intermunicipal': 'Regional intermunicipal',
        '9. Regional interestadual': 'Regional interestadual',
        '9. Estadual': 'Estadual',
        '9. Nacional': 'Nacional',
        '9. Virtual/Online': 'Virtual/Online'
    }
    colunas = [c for c in dicionario if c in filtrado.columns]
    if not colunas:
        return None
    dados = filtrado[colunas].rename(columns=dicionario)
    ordem = ['Sempre', 'Regularmente', 'Raramente', 'Nunca']
    contagens = {col: dados[col].value_counts().reindex(ordem, fill_value=0).to_list() for col in dados.columns}
    df_final = pd.DataFrame({'Frequência': ordem, **contagens})
    df_contagens = df_final.set_index('Frequência').reindex(ordem)
    totais = df_contagens.sum(axis=0).replace(0, 1)
    df_proporcoes = df_contagens.div(totais, axis=1)
    variaveis = df_proporcoes.columns
    cor_inicial = f"rgb{hex_to_rgb('#042A68')}"
    cor_final = f"rgb{hex_to_rgb('#EBF5FF')}"
    cores = n_colors(cor_inicial, cor_final, len(df_proporcoes.index), colortype='rgb')
    fig = go.Figure()
    for i, categoria in enumerate(df_proporcoes.index):
        proporcoes = df_proporcoes.loc[categoria].tolist()
        contagens = df_contagens.loc[categoria].tolist()
        texto = [f'{c} ({v:.1%})' if v > 0.01 else '' for c, v in zip(contagens, proporcoes)]
        cor_texto = 'white' if i == 0 else 'black'
        fig.add_trace(go.Bar(x=variaveis, y=proporcoes, name=categoria, marker_color=cores[i], text=texto, textposition='inside', textfont_color=cor_texto))
    fig.update_layout(
        title='Composição dos Pontos de Cultura por Abrangência Territorial',
        barmode='stack',
        yaxis=dict(tickformat='.0%'),
        legend_title_text='Frequência de atuação',
        margin=dict(l=10, r=80, t=50, b=10)
    )
    fig.update_xaxes(title='', categoryorder='array', categoryarray=list(variaveis))
    fig.update_yaxes(title='', range=[0, 1])
    return fig


CAMINHO_CEPS_GEO = 'assets/ceps_geocodificados.csv'


@st.cache_data(show_spinner=False)
def carregar_ceps_geocodificados():
    if not os.path.exists(CAMINHO_CEPS_GEO):
        return pd.DataFrame(columns=['cep', 'latitude', 'longitude'])
    df = pd.read_csv(CAMINHO_CEPS_GEO, encoding='utf-8-sig')
    df['cep'] = df['cep'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    return df.dropna(subset=['latitude', 'longitude'])


@st.cache_data(show_spinner=False)
def geocodificar_ceps(ceps):
    serie = pd.Series(ceps).dropna().astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
    if serie.empty:
        return pd.DataFrame(columns=['cep', 'latitude', 'longitude'])
    dados = carregar_ceps_geocodificados()
    if dados.empty:
        return pd.DataFrame(columns=['cep', 'latitude', 'longitude'])
    df = pd.DataFrame({'cep': serie}).merge(dados, on='cep', how='left')
    df = df.dropna(subset=['latitude', 'longitude'])
    return df.drop_duplicates(subset=['cep', 'latitude', 'longitude'])


def serie_multiselecionada(filtrado, dicionario):
    dados = {rotulo: int(para_bool(filtrado[coluna]).sum()) for coluna, rotulo in dicionario.items() if coluna in filtrado.columns}
    return pd.Series(dados).sort_values(ascending=True)


def serie_tem_nao(filtrado, coluna_sem, rotulo_sim, rotulo_nao):
    if coluna_sem not in filtrado.columns:
        return pd.Series(dtype=int)
    sem = int(para_bool(filtrado[coluna_sem]).sum())
    com = max(len(filtrado) - sem, 0)
    return pd.Series({rotulo_sim: com, rotulo_nao: sem})


def pagina_visao_geral_dados():
    mostrar_cabecalho()
    st.title('Visão Geral dos Dados')
    st.markdown('A coleta de dados foi realizada por meio de formulário online na plataforma Meu Ponto Movimenta, com período de referência de março de 2023 a fevereiro de 2025. A pesquisa obteve mais de 2.400 respostas, abrangendo Pontos de Cultura em todas as Unidades da Federação, formando uma amostra de conveniência com cobertura nacional suficiente para um panorama robusto.')
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'visao_geral')
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
    total_registros = len(filtrado)
    total_colunas = len(df.columns)
    colunas_com_dados = int(filtrado.notna().any().sum()) if not filtrado.empty else 0
    taxa_preenchimento = float(filtrado.notna().mean().mean() * 100) if not filtrado.empty else 0.0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Registros filtrados', f'{total_registros:,}'.replace(',', '.'))
    k2.metric('Colunas na base', f'{total_colunas}')
    k3.metric('Colunas com dados', f'{colunas_com_dados}')
    k4.metric('Preenchimento médio', f'{taxa_preenchimento:.1f}%')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    colunas = [c for c in [
        '1. Nome do Ponto ou Pontão de Cultura:',
        '2. Nome da Instituição Proponente do Ponto de Cultura:',
        'Email:',
        'Registro',
        'Pontão',
        'estado',
        'regiao',
        'cidade_api'
    ] if c in filtrado.columns]
    st.dataframe(filtrado[colunas], use_container_width=True)


def painel_filtros(df, chave_pagina):
    def rotulo_acao(coluna):
        texto = str(coluna)
        if '(' in texto and ')' in texto:
            return texto.split('(', 1)[1].rsplit(')', 1)[0].strip()
        return texto.replace('10. As atividades do Ponto de Cultura estão relacionadas diretamente com quais ações estruturante da Política Nacional de Cultura Viva?', '').strip(' -')

    colunas_acao = []
    for coluna in df.columns:
        texto = str(coluna)
        if texto in ACOES_ESTRUTURANTES or 'ações estruturante' in texto or 'acoes estruturante' in texto:
            if texto.strip() == '10. As atividades do Ponto de Cultura estão relacionadas diretamente com quais ações estruturante da Política Nacional de Cultura Viva?':
                continue
            colunas_acao.append(coluna)

    if 'filtros_compartilhados' not in st.session_state:
        st.session_state['filtros_compartilhados'] = {
            'filtro_estado': [],
            'filtro_faixa_pop': [],
            'filtro_rural_urbano': [],
            'filtro_acao': [],
            'filtro_linguagem': [],
            'filtro_receita': [],
            'filtro_regiao': [],
            'filtro_tipo_ponto': None,
            'filtro_registro': None,
            'filtro_rec_federal': None,
            'filtro_rec_minc': None,
            'filtro_rec_estadual': None,
            'filtro_rec_municipal': None,
            'filtro_pnab_estadual': None,
            'filtro_pnab_municipal': None,
            'filtro_tcc_est_ponto': None,
            'filtro_tcc_est_pontao': None,
            'filtro_tcc_mun_ponto': None,
            'filtro_tcc_mun_pontao': None
        }

    def chave_widget(base):
        return f'{chave_pagina}_{base}'

    def preparar_chave(base):
        chave = chave_widget(base)
        if chave not in st.session_state:
            st.session_state[chave] = st.session_state['filtros_compartilhados'].get(base)
        return chave

    with st.expander('Filtros', expanded=False):
        if 'linguagens_lista' in df.columns:
            contagem_linguagens = df['linguagens_lista'].explode().value_counts()
            opcoes_linguagens = sorted(contagem_linguagens[contagem_linguagens >= 10].index.tolist())
        else:
            opcoes_linguagens = []

        col1, col2, col3 = st.columns(3)
        estado = col1.multiselect('Estado', options=sorted(df['estado'].dropna().unique()), placeholder='Selecione', key=preparar_chave('filtro_estado'))
        opcoes_faixa_pop = [f for f in ORDEM_FAIXA_POPULACIONAL if f in df['faixa_populacional'].dropna().unique()]
        faixa_pop = col1.multiselect('Faixa populacional', options=opcoes_faixa_pop, placeholder='Selecione', key=preparar_chave('filtro_faixa_pop'))
        rural_urbano = col1.multiselect('Classificação rural/urbana', options=['Rural', 'Urbano'], placeholder='Selecione', help='Definida como Rural até 50 mil habitantes e Urbano acima de 50 mil.', key=preparar_chave('filtro_rural_urbano'))

        acao = col2.multiselect('Ação estruturante', options=colunas_acao, format_func=rotulo_acao, placeholder='Selecione', key=preparar_chave('filtro_acao'))
        linguagem = col2.multiselect('Linguagem artística', options=opcoes_linguagens, placeholder='Selecione', key=preparar_chave('filtro_linguagem'))
        receita = col2.multiselect('Faixa de receita anual', options=FAIXAS_RECEITA, placeholder='Selecione', key=preparar_chave('filtro_receita'))

        regiao = col3.segmented_control('Região', options=sorted(df['regiao'].dropna().unique()), selection_mode='multi', key=preparar_chave('filtro_regiao'))
        tipo_ponto = col3.pills('Tipo de reconhecimento', options=sorted(df['tipo_ponto'].dropna().unique()), selection_mode='single', key=preparar_chave('filtro_tipo_ponto'))
        registro = col3.pills('Cadastro jurídico', options=sorted(df['registro'].dropna().unique()), selection_mode='single', key=preparar_chave('filtro_registro'))

        p1, p2, p3, p4, p5, p6, p7, p8, p9, p10 = st.columns(10)
        rec_federal = p1.pills('Recursos federais', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_rec_federal'))
        rec_minc = p2.pills('Recursos MinC', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_rec_minc'))
        rec_estadual = p3.pills('Recursos estaduais', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_rec_estadual'))
        rec_municipal = p4.pills('Recursos municipais', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_rec_municipal'))
        pnab_estadual = p5.pills('PNAB estadual', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_pnab_estadual'))
        pnab_municipal = p6.pills('PNAB municipal', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_pnab_municipal'))
        tcc_est_ponto = p7.pills('TCC est. Ponto', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_tcc_est_ponto'))
        tcc_est_pontao = p8.pills('TCC est. Pontão', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_tcc_est_pontao'))
        tcc_mun_ponto = p9.pills('TCC mun. Ponto', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_tcc_mun_ponto'))
        tcc_mun_pontao = p10.pills('TCC mun. Pontão', options=['Sim', 'Não'], selection_mode='single', key=preparar_chave('filtro_tcc_mun_pontao'))

        rec_federal = rec_federal or ''
        rec_minc = rec_minc or ''
        rec_estadual = rec_estadual or ''
        rec_municipal = rec_municipal or ''
        pnab_estadual = pnab_estadual or ''
        pnab_municipal = pnab_municipal or ''
        tcc_est_ponto = tcc_est_ponto or ''
        tcc_est_pontao = tcc_est_pontao or ''
        tcc_mun_ponto = tcc_mun_ponto or ''
        tcc_mun_pontao = tcc_mun_pontao or ''

        st.session_state['filtros_compartilhados'].update({
            'filtro_estado': estado,
            'filtro_faixa_pop': faixa_pop,
            'filtro_rural_urbano': rural_urbano,
            'filtro_acao': acao,
            'filtro_linguagem': linguagem,
            'filtro_receita': receita,
            'filtro_regiao': regiao or [],
            'filtro_tipo_ponto': tipo_ponto or None,
            'filtro_registro': registro or None,
            'filtro_rec_federal': rec_federal or None,
            'filtro_rec_minc': rec_minc or None,
            'filtro_rec_estadual': rec_estadual or None,
            'filtro_rec_municipal': rec_municipal or None,
            'filtro_pnab_estadual': pnab_estadual or None,
            'filtro_pnab_municipal': pnab_municipal or None,
            'filtro_tcc_est_ponto': tcc_est_ponto or None,
            'filtro_tcc_est_pontao': tcc_est_pontao or None,
            'filtro_tcc_mun_ponto': tcc_mun_ponto or None,
            'filtro_tcc_mun_pontao': tcc_mun_pontao or None
        })

        regiao = regiao or []
        tipo_ponto = [tipo_ponto] if tipo_ponto else []
        registro = [registro] if registro else []

    filtros = {
        'estado': estado,
        'regiao': regiao,
        'faixa_populacional': faixa_pop,
        'classificacao_rural_urbana': rural_urbano,
        'tipo_ponto': tipo_ponto,
        'registro': registro,
        'acoes_estruturantes': acao,
        'linguagem_artistica': linguagem,
        'faixa_receita': receita,
        'filtros_booleanos': {
            'rec_federal': 'rec_federal',
            'rec_minc': 'rec_minc',
            'rec_estadual': 'rec_estadual',
            'rec_municipal': 'rec_municipal',
            'pnab_estadual': 'pnab_estadual',
            'pnab_municipal': 'pnab_municipal',
            'tcc_est_ponto': 'tcc_est_ponto',
            'tcc_est_pontao': 'tcc_est_pontao',
            'tcc_mun_ponto': 'tcc_mun_ponto',
            'tcc_mun_pontao': 'tcc_mun_pontao'
        },
        'rec_federal': rec_federal,
        'rec_minc': rec_minc,
        'rec_estadual': rec_estadual,
        'rec_municipal': rec_municipal,
        'pnab_estadual': pnab_estadual,
        'pnab_municipal': pnab_municipal,
        'tcc_est_ponto': tcc_est_ponto,
        'tcc_est_pontao': tcc_est_pontao,
        'tcc_mun_ponto': tcc_mun_ponto,
        'tcc_mun_pontao': tcc_mun_pontao
    }

    partes = []
    if estado:
        partes.append(f"Estado: **{', '.join(estado)}**")
    if regiao:
        partes.append(f"Região: **{', '.join(regiao)}**")
    if faixa_pop:
        partes.append(f"Faixa populacional: **{', '.join(faixa_pop)}**")
    if rural_urbano:
        partes.append(f"Rural/urbano: **{', '.join(rural_urbano)}**")
    if tipo_ponto:
        partes.append(f"Tipo: **{', '.join(tipo_ponto)}**")
    if registro:
        partes.append(f"Cadastro: **{', '.join(registro)}**")
    if acao:
        partes.append(f"Ação: **{', '.join([rotulo_acao(a) for a in acao])}**")
    if linguagem:
        partes.append(f"Linguagem: **{', '.join(linguagem)}**")
    if receita:
        partes.append(f"Receita: **{', '.join(receita)}**")

    binarios = []
    for rotulo, valor in [
        ('Recursos federais', rec_federal),
        ('Recursos MinC', rec_minc),
        ('Recursos estaduais', rec_estadual),
        ('Recursos municipais', rec_municipal),
        ('PNAB estadual', pnab_estadual),
        ('PNAB municipal', pnab_municipal),
        ('TCC est. Ponto', tcc_est_ponto),
        ('TCC est. Pontão', tcc_est_pontao),
        ('TCC mun. Ponto', tcc_mun_ponto),
        ('TCC mun. Pontão', tcc_mun_pontao)
    ]:
        if valor in ['Sim', 'Não']:
            binarios.append(f"{rotulo}: **{valor}**")

    resumo = ' • '.join(partes + binarios) if (partes or binarios) else 'Nenhum filtro aplicado'
    filtrado = aplicar_filtros(df, filtros)
    return filtrado, resumo


def pagina_perfil_institucional():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'perfil')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    contagem_estado = filtrado['uf'].value_counts().reset_index()
    contagem_estado.columns = ['uf', 'contagem']
    contagem_cidades = filtrado['cidade'].value_counts().head(5).sort_values(ascending=True)

    aba1, aba2, aba3 = st.tabs(['Mapa e perfil', 'Abrangência e infraestrutura', 'Linguagens e ações'])
    with aba1:
        st.title('Distribuição dos Pontos de Cultura e características institucionais')
        st.markdown('Aqui você vê a distribuição territorial dos Pontos, o perfil jurídico e o tipo de reconhecimento, além dos municípios com maior concentração e dos canais digitais mais usados. Este painel ajuda a entender onde a rede está mais presente e como se organiza institucionalmente.')
        col_esq, col_dir = st.columns([1.2, 0.8])
        with col_esq:
            fig_mapa = grafico_mapa_estados(contagem_estado, 'uf', 'contagem', 'Distribuição por Estado', altura=777)
            mostrar_grafico(fig_mapa, 'Distribuição por Estado')
        with col_dir:
            def limpar_rotulo(texto):
                return str(texto).split(' (', 1)[0].strip()
            registro_counts = filtrado['registro'].value_counts()
            tipo_counts = filtrado['tipo_ponto'].value_counts()
            if not registro_counts.empty:
                registro_counts.index = [limpar_rotulo(v) for v in registro_counts.index]
            if not tipo_counts.empty:
                tipo_counts.index = [limpar_rotulo(v) for v in tipo_counts.index]
            g1, g2 = st.columns(2)
            with g1:
                if not registro_counts.empty:
                    mostrar_grafico(grafico_donut(registro_counts, 'Cadastro jurídico', altura=270), 'Cadastro jurídico')
            with g2:
                if not tipo_counts.empty:
                    mostrar_grafico(grafico_donut(tipo_counts, 'Ponto vs Pontão', altura=270), 'Ponto vs Pontão')

            fig_cidades = grafico_barras_series(contagem_cidades, 'Top 5 Municípios', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=264)
            fig_cidades.update_layout(margin=dict(l=10, r=80, t=30, b=0), title_y=0.98)
            mostrar_grafico(fig_cidades, 'Top 5 Municípios')
            redes = pd.Series(dtype=int)
            col_rede = encontrar_coluna(filtrado.columns, 'Endereço da rede social do Ponto de Cultura')
            if col_rede:
                texto = filtrado[col_rede].fillna('').astype(str).str.lower()
                redes = pd.Series({
                    'Instagram': texto.str.contains('insta').sum(),
                    'Facebook': texto.str.contains('face').sum(),
                    'Twitter/X': texto.str.contains('twitter|x.com|@x|\\bx\\b').sum(),
                    'YouTube': texto.str.contains('youtube|youtu.be').sum(),
                    'TikTok': texto.str.contains('tiktok|tik tok|tt').sum()
                })
                redes = redes[redes > 0].sort_values(ascending=True)
            if not redes.empty:
                    fig_redes = grafico_barras_series(redes, 'Presença digital', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=264)
                    fig_redes.update_layout(margin=dict(l=10, r=80, t=28, b=0), title_y=0.98)
                    mostrar_grafico(fig_redes, 'Presença digital')
            else:
                colunas_abrangencia = [
                    '9. Municipal',
                    '9. Regional intermunicipal',
                    '9. Regional interestadual',
                    '9. Estadual',
                    '9. Nacional',
                    '9. Virtual/Online'
                ]
                dados_abrangencia = {}
                for coluna in colunas_abrangencia:
                    if coluna in filtrado.columns:
                        dados_abrangencia[coluna.replace('9. ', '')] = (filtrado[coluna].astype(str).str.strip().str.lower() == 'sempre').sum()
                if dados_abrangencia:
                    serie_abrangencia = pd.Series(dados_abrangencia).sort_values(ascending=True)
                    fig_abrangencia = grafico_barras_series(serie_abrangencia, 'Abrangência prioritária (Sempre)', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=264)
                    fig_abrangencia.update_layout(margin=dict(l=10, r=80, t=28, b=0), title_y=0.98)
                    mostrar_grafico(fig_abrangencia, 'Abrangência prioritária (Sempre)')

    with aba2:
        st.title('Abrangência territorial e infraestrutura comunitária')
        fig_abrangencia = grafico_abrangencia_empilhado(filtrado)
        if fig_abrangencia:
            mostrar_grafico(fig_abrangencia, 'Composição dos Pontos de Cultura por Abrangência Territorial')

    with aba3:
        st.title('Linguagens artísticas, ações estruturantes e visão micro')
        col1, col2, col3 = st.columns(3)
        with col1:
            colunas_acao = [c for c in ACOES_ESTRUTURANTES if c in filtrado.columns]
            if colunas_acao:
                contagens = {c: int(para_bool(filtrado[c]).sum()) for c in colunas_acao if c != 'Sem ação estruturante'}
                serie_acoes = pd.Series(contagens).sort_values(ascending=True).tail(10)
                rotulos_completos = serie_acoes.index.tolist()
                rotulos_curto = [r if len(r) <= 30 else f"{r[:27]}..." for r in rotulos_completos]
                serie_acoes_plot = serie_acoes.copy()
                serie_acoes_plot.index = rotulos_curto
                fig_acoes = grafico_barras_series(serie_acoes_plot, 'Top 10 ações estruturantes', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=520, mostrar_percentual=False)
                total_registros = max(len(filtrado), 1)
                textos = [f'{v} ({(v / total_registros):.1%})' for v in serie_acoes.tolist()]
                fig_acoes.update_traces(text=textos, textposition='outside', cliponaxis=False, hovertext=rotulos_completos, hovertemplate='%{hovertext}<br>%{x}<extra></extra>')
                mostrar_grafico(fig_acoes, 'Top 10 ações estruturantes')
        with col2:
            termos = filtrado['linguagem_artistica'].fillna('').astype(str).str.split(',').explode().str.strip()
            termos = termos.replace({'O Ponto de Cultura não trabalha com linguagens artísticas': 'Sem linguagens artísticas'})
            termos = termos[termos != '']
            top_linguagens = termos.value_counts().head(12).sort_values(ascending=True)
            mostrar_grafico(grafico_donut(top_linguagens, 'Linguagens artísticas predominantes', altura=520), 'Linguagens artísticas predominantes')

        dicionario_micro = {
            'Artes visuais (Pintura)': 'Pintura',
            'Artes visuais (Escultura)': 'Escultura',
            'Artes visuais (Desenho)': 'Desenho',
            'Artes visuais (Gravura)': 'Gravura',
            'Artes visuais (Fotografia)': 'Fotografia',
            'Artes visuais (Instalação)': 'Instalação',
            'Artes visuais (Digital)': 'Arte digital',
            'Artes visuais (Gráficas)': 'Artes gráficas',
            'Artes visuais (Urbana)': 'Arte urbana',
            'Artes visuais (Grafite)': 'Grafite',
            'Artes visuais (Perfomance)': 'Perfomance',
            'Artes visuais (Outras)': 'Outras expressões de arte visual',
            'Audiovisual (Cinema)': 'Cinema',
            'Audiovisual (Vídeo)': 'Vídeo',
            'Audiovisual (Televisão)': 'Televisão',
            'Audiovisual (Animação)': 'Animação',
            'Audiovisual (Mapping)': 'Mapping',
            'Audiovisual (Audiovisual expandido)': 'Audiovisual expandido',
            'Audiovisual (Experimentações audiovisuais)': 'Experimentações audiovisuais',
            'Audiovisual (Outras:)': 'Outras expressões audiovisuais',
            'Dança (Dança clássica)': 'Dança clássica',
            'Dança (Dança moderna)': 'Dança moderna',
            'Dança (Dança contemporânea)': 'Dança contemporânea',
            'Dança (Dança tradicional / folclórica)': 'Dança tradicional / folclórica',
            'Dança (Dança urbana)': 'Dança urbana',
            'Dança (Outros gêneros coreográficos)': 'Outros gêneros coreográficos',
            'Dança (Outras:)': 'Outros tipos de Dança',
            'Teatro (Teatro de palco)': 'Teatro de palco',
            'Teatro (Teatro de rua)': 'Teatro de rua',
            'Teatro (Performance teatral)': 'Performance teatral',
            'Teatro (Performance cênica)': 'Performance cênica',
            'Teatro (Intervenções cênicas)': 'Intervenções cênicas',
            'Teatro (Outras:)': 'Outras expressões teatrais',
            'Música (Música popular)': 'Música popular',
            'Música (Música tradicional)': 'Música tradicional',
            'Música (Música contemporânea)': 'Música contemporânea',
            'Música (Música instrumental)': 'Música instrumental',
            'Música (Canto)': 'Canto',
            'Música (Composição musical)': 'Composição musical',
            'Música (Orquestra filarmônica)': 'Orquestra filarmônica',
            'Música (Fanfarra)': 'Fanfarra',
            'Música (Orquestra)': 'Orquestra',
            'Música (Outras:)': 'Outras expressões musicais',
            'Literatura (Contação de história)': 'Contação de história',
            'Literatura (Sarau)': 'Sarau',
            'Literatura (Slam)': 'Slam',
            'Literatura (Cordel)': 'Cordel',
            'Literatura (Poesia)': 'Poesia',
            'Literatura (Prosa literária)': 'Prosa literária',
            'Literatura (Conto)': 'Conto',
            'Literatura (Romance)': 'Romance',
            'Literatura (Literatura infantojuvenil)': 'Literatura infantojuvenil',
            'Literatura (Literatura Oral)': 'Literatura Oral',
            'Literatura (Performance literária)': 'Performance literária',
            'Literatura (Outras:)': 'Outras expressões literárias',
            'Circo (Artes circenses tradicionais)': 'Artes circenses tradicionais',
            'Circo (Circo contemporâneo)': 'Circo contemporâneo',
            'Circo (Palhaçaria)': 'Palhaçaria',
            'Circo (Acrobacias)': 'Acrobacias',
            'Circo (Malabarismo)': 'Malabarismo',
            'Circo (Ilusionismo)': 'Ilusionismo',
            'Circo (Outras:)': 'Outras expressões circenses',
            'Hip Hop (Rap)': 'Rap',
            'Hip Hop (DJ)': 'DJ',
            'Hip Hop (Breakdance)': 'Breakdance',
            'Hip Hop (Grafite)': 'Grafite (Hip Hop)',
            'Hip Hop (MC)': 'MC',
            'Hip Hop (Outras:)': 'Outras expressões da cultura Hip Hop'
        }
        dados_micro = filtrado.rename(columns=dicionario_micro)
        grupos_micro = [
            ('Artes Visuais', ['Pintura', 'Escultura', 'Desenho', 'Gravura', 'Fotografia', 'Instalação', 'Arte digital', 'Artes gráficas', 'Arte urbana', 'Grafite', 'Perfomance', 'Outras expressões de arte visual']),
            ('Audiovisual', ['Cinema', 'Vídeo', 'Televisão', 'Animação', 'Mapping', 'Audiovisual expandido', 'Experimentações audiovisuais', 'Outras expressões audiovisuais']),
            ('Dança', ['Dança clássica', 'Dança moderna', 'Dança contemporânea', 'Dança tradicional / folclórica', 'Dança urbana', 'Outros gêneros coreográficos', 'Outros tipos de Dança']),
            ('Teatro', ['Teatro de palco', 'Teatro de rua', 'Performance teatral', 'Performance cênica', 'Intervenções cênicas', 'Outras expressões teatrais']),
            ('Música', ['Música popular', 'Música tradicional', 'Música contemporânea', 'Música instrumental', 'Canto', 'Composição musical', 'Orquestra filarmônica', 'Fanfarra', 'Orquestra', 'Outras expressões musicais']),
            ('Literatura', ['Contação de história', 'Sarau', 'Slam', 'Cordel', 'Poesia', 'Prosa literária', 'Conto', 'Romance', 'Literatura infantojuvenil', 'Literatura Oral', 'Performance literária', 'Outras expressões literárias']),
            ('Circo', ['Artes circenses tradicionais', 'Circo contemporâneo', 'Palhaçaria', 'Acrobacias', 'Malabarismo', 'Ilusionismo', 'Outras expressões circenses']),
            ('Hip Hop', ['Rap', 'DJ', 'Breakdance', 'Grafite (Hip Hop)', 'MC', 'Outras expressões da cultura Hip Hop'])
        ]
        contagens_macro = {}
        total_registros = max(len(dados_micro), 1)
        for titulo, colunas in grupos_micro:
            colunas_validas = [c for c in colunas if c in dados_micro.columns]
            if colunas_validas:
                base = pd.concat([para_bool(dados_micro[c]) for c in colunas_validas], axis=1)
                contagens_macro[titulo] = int(base.any(axis=1).sum())
        with col3:
            opcoes = [t for t, _ in grupos_micro if t in contagens_macro]
            if opcoes:
                escolha = st.selectbox('Selecione a linguagem para visão micro', opcoes, index=0)
                colunas = dict(grupos_micro).get(escolha, [])
                colunas_validas = [c for c in colunas if c in dados_micro.columns]
                if colunas_validas:
                    contagens = {c: int(para_bool(dados_micro[c]).sum()) for c in colunas_validas}
                    serie = pd.Series(contagens).sort_values(ascending=True)
                    fig_micro = grafico_barras_series(serie, f'Visão micro: {escolha}', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=460, mostrar_percentual=False)
                    textos = [f'{v} ({(v / total_registros):.1%})' for v in serie.tolist()]
                    fig_micro.update_traces(text=textos, textposition='outside', cliponaxis=False)
                    mostrar_grafico(fig_micro, f'Visão micro: {escolha}')

    st.divider()
    st.subheader('Pins por CEP (teste)')
    st.caption('Teste de pontos geolocalizados por CEP para validar a dispersão territorial dos Pontos de Cultura.')
    if 'cep_corrigido' in filtrado.columns:
        if not os.path.exists(CAMINHO_CEPS_GEO):
            st.info('Arquivo de CEPs geocodificados não encontrado. Rode o script para gerar.')
        else:
            df_pins = geocodificar_ceps(filtrado['cep_corrigido'])
            if not df_pins.empty:
                fig_ceps = px.scatter_mapbox(df_pins, lat='latitude', lon='longitude', hover_name='cep', zoom=3.2, center={'lat': -15, 'lon': -55}, height=620)
                fig_ceps.update_traces(marker=dict(size=6, color=PALETA_CORES['azul_principal']))
                fig_ceps.update_layout(mapbox_style='carto-positron', margin=dict(l=0, r=0, t=40, b=0))
                mostrar_grafico(fig_ceps, 'Pins por CEP (teste)')
            else:
                st.info('Não foi possível localizar CEPs válidos para o mapa.')
    else:
        st.info('Coluna de CEP não encontrada.')


def pagina_capacidade_infraestrutura():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'capacidade')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Capacidade e Infraestrutura')
    st.markdown('Apresenta as principais atividades realizadas e a estrutura disponível para sustentar essas ações.')

    dicionario_infraestrutura = {
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (O Ponto de Cultura não disponibiliza espaço/infraestrutura para a comunidade)': 'Sem espaço/infraestrutura para comunidade',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Biblioteca)': 'Biblioteca',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Cineclube)': 'Cineclube',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Cozinha)': 'Cozinha',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Equipamentos de som e audiovisual (microfone, câmeras, ﬁlmadoras, caixas de som, mesa de som, mesa de iluminação))': 'Equipamentos de som e audiovisual',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Espaço para apresentações (auditório, teatro de bolso, lona de circo e outros))': 'Espaço para apresentações',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Espaço para armazenamento de conteúdos digitais (discos e drives virtuais))': 'Espaço para armazenamento de conteúdos digitais',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Estúdio de gravação e ensaio)': 'Estúdio de gravação e ensaio',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Horta Comunitária)': 'Horta Comunitária',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Lona pré-moldada)': 'Lona pré-moldada',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Sala de exposição (galeria))': 'Sala de exposição (galeria)',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Sala para oﬁcinas artísticas e culturais (trabalhos com corpo, artes, leitura e outros))': 'Sala para oficinas artísticas e culturais',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Rádio comunitária)': 'Rádio comunitária',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Sala de Informática)': 'Sala de Informática',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Sala de reuniões (espaço com cadeiras e mesas))': 'Sala de reuniões',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Software/Plataforma pagos (Google, Zoom, Microsoft e outros))': 'Software/Plataforma pagos',
        '25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário (Outros)': 'Outros tipos de infraestrutura'
    }
    dicionario_servicos = {
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Ações de assistência social)': 'Ações de assistência social',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Ações de promoção à saúde e ao bem-estar)': 'Promoção à saúde e bem-estar',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Ações culturais de fortalecimento dos laços de pertencimento da população)': 'Fortalecimento de pertencimento',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Ajuda emergencial (arrecadação de recursos, doação de cestas básicas, kit segurança, etc))': 'Ajuda emergencial',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Educação artística nas escolas)': 'Educação artística nas escolas',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Educação patrimonial)': 'Educação patrimonial',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Espiritualidade)': 'Espiritualidade',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Formação artística e cultural)': 'Formação artística e cultural',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Formação cidadã)': 'Formação cidadã',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Iniciativas de promoção da qualidade de vida da população)': 'Qualidade de vida',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Inserção produtiva de jovens)': 'Inserção produtiva de jovens',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Mediação de leitura e formação de leitores)': 'Mediação de leitura',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Preservação e valorização das memórias e identidades do território)': 'Memórias e identidades do território',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Preservação e responsabilidade ambiental)': 'Responsabilidade ambiental',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Projetos voltados ao desenvolvimento local)': 'Desenvolvimento local',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Promoção à participação de grupos em feiras, festivais e outros eventos.)': 'Participação em eventos',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Promoção do turismo de base comunitária)': 'Turismo de base comunitária',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (Outros)': 'Outros',
        '26. Quais serviços são prestados pelo Ponto de Cultura à comunidade? (O Ponto de Cultura não presta serviços à comunidade)': 'Não presta serviços à comunidade'
    }
    lista_nomes_atividades = {
        'Descreva as ações realizadas': 'Formação e educação',
        'Descreva as ações realizadas (2)': 'Cultura e saúde',
        'Descreva as ações realizadas (3)': 'Desenvolvimento social e comunitário',
        'Descreva as ações realizadas (4)': 'Economia e trabalho',
        'Descreva as ações realizadas (5)': 'Meio ambiente e sustentabilidade',
        'Descreva as ações realizadas (6)': 'Outros tipos de atividades'
    }

    serie_infra = serie_multiselecionada(filtrado, dicionario_infraestrutura)
    dados_atividades = filtrado.rename(columns=lista_nomes_atividades)
    colunas_atividades = list(lista_nomes_atividades.values())
    base_atividades = dados_atividades[colunas_atividades].apply(pd.to_numeric, errors='coerce')
    medianas = base_atividades.median().reindex(colunas_atividades)
    st.subheader('Quantidade esperada de atividades gratuitas por eixo')
    colunas_kpi = st.columns(6)
    for coluna, nome in zip(colunas_kpi, colunas_atividades):
        valor = medianas.get(nome)
        texto = f'{int(valor)}' if pd.notna(valor) else 'Sem dado'
        coluna.metric(nome, texto)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Infraestrutura disponível')
        st.caption('Importante para analisar transcrições e reconhecer gargalos de infraestrutura no território.')
        if not serie_infra.empty:
            mostrar_grafico(
                grafico_barras_series(serie_infra, '', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=525),
                ''
            )
        else:
            st.info('Sem dados suficientes para infraestrutura.')
    with col2:
        st.subheader('Serviços prestados à comunidade')
        st.caption('Importante para analisar transcrições das respostas e identificar o perfil de serviço comunitário.')
        serie_servicos = serie_multiselecionada(filtrado, dicionario_servicos)
        serie_servicos = serie_servicos.sort_values(ascending=True).tail(16)
        if not serie_servicos.empty:
            mostrar_grafico(
                grafico_barras_series(serie_servicos, '', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=525),
                ''
            )
        else:
            st.info('Sem dados suficientes para serviços prestados.')


def pagina_sustentabilidade_economica():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'sustentabilidade')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Sustentabilidade Econômica')
    st.markdown('Painel crítico para gestores: revela fragilidades, dependências e a base real de financiamento.')

    total_registros = max(len(filtrado), 1)
    sem_receita = int((filtrado['faixa_receita'] == 'Não teve receita').sum()) if 'faixa_receita' in filtrado.columns else 0
    col_publico = encontrar_coluna(filtrado.columns, '14. O Ponto de Cultura acessou recursos públicos nos últimos 24 meses?')
    col_privado = encontrar_coluna(filtrado.columns, '15. O Ponto de Cultura acessou recursos financeiros privados nos últimos 24 meses?')
    col_cultura_viva = encontrar_coluna(filtrado.columns, '13. O Projeto do Ponto de Cultura representa a principal fonte de renda da entidade/coletivo/pessoa física?')
    col_credito = encontrar_coluna(filtrado.columns, '18. O Ponto de Cultura acessou linha de crédito para a realização de suas ações?')

    perc_publico = para_bool(filtrado[col_publico]).mean() if col_publico else 0
    perc_privado = para_bool(filtrado[col_privado]).mean() if col_privado else 0
    perc_cultura_viva = para_bool(filtrado[col_cultura_viva]).mean() if col_cultura_viva else 0
    perc_credito = para_bool(filtrado[col_credito]).mean() if col_credito else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric('Sem Receita em 2024', f"{(sem_receita / total_registros) * 100:.2f}%")
    col2.metric('Acessaram Recurso Público', f"{perc_publico * 100:.2f}%")
    col3.metric('Acessaram Recurso Privado', f"{perc_privado * 100:.2f}%")
    col4.metric('Cultura Viva é fonte principal', f"{perc_cultura_viva * 100:.2f}%")
    col5.metric('Acessaram linha de crédito', f"{perc_credito * 100:.2f}%")

    col1, col2 = st.columns([4, 2])
    with col1:
        st.subheader('Distribuição das Faixas de Receita Anual')
        st.caption('Importante para analisar transcrições das respostas e identificar concentração de receita nas faixas mais baixas.')
        serie_receita = filtrado['faixa_receita'].value_counts().reindex(FAIXAS_RECEITA).fillna(0).astype(int) if 'faixa_receita' in filtrado.columns else pd.Series(dtype=int)
        if not serie_receita.empty:
            fig_receita = grafico_barras_series(serie_receita, 'Distribuição das Faixas de Receita Anual', cor=PALETA_CORES['azul_principal'], altura=420)
            fig_receita.update_xaxes(tickangle=-25)
            fig_receita.update_layout(title='')
            mostrar_grafico(fig_receita, '')
        else:
            st.info('Sem dados suficientes para a distribuição de receita.')

    with col2:
        st.subheader('Origem do Recurso Público')
        st.caption('Importante para analisar transcrições das respostas e entender o peso por esfera de governo.')
        total_federal = int(para_bool(filtrado['rec_federal']).sum()) if 'rec_federal' in filtrado.columns else 0
        total_estadual = int(para_bool(filtrado['rec_estadual']).sum()) if 'rec_estadual' in filtrado.columns else 0
        total_municipal = int(para_bool(filtrado['rec_municipal']).sum()) if 'rec_municipal' in filtrado.columns else 0
        serie_origem = pd.Series({'Federal': total_federal, 'Estadual': total_estadual, 'Municipal': total_municipal}).sort_values(ascending=True)
        if serie_origem.sum() > 0:
            fig_origem = grafico_barras_series(serie_origem, '', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=420, mostrar_percentual=False)
            textos = [f'{int(v)} ({(v / total_registros) * 100:.1f}%)' for v in serie_origem.values]
            fig_origem.update_traces(text=textos, textposition='outside', cliponaxis=False)
            mostrar_grafico(fig_origem, '')
        else:
            st.info('Sem dados suficientes para a origem do recurso público.')

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader('Top 3 motivos para não acessar linha de crédito')
        col_motivo = encontrar_coluna(filtrado.columns, '18. 2. Se não, sinalize o motivo')
        motivos_texto = filtrado[col_motivo].fillna('').astype(str) if col_motivo else pd.Series(dtype=str)
        motivos_lista = motivos_texto.apply(lambda t: [p.strip() for p in t.split(',') if p.strip()])
        serie_motivos = motivos_lista.explode().value_counts()
        top_motivos = serie_motivos.head(3)
        base_motivos = max(int(serie_motivos.sum()), 1)
        if not top_motivos.empty:
            itens = [f"- *{motivo}* **{valor}** (**{perc:.1f}%**)" for motivo, valor in top_motivos.items() for perc in [(valor / base_motivos) * 100]]
            st.markdown("\n".join(itens))
        else:
            st.info('Sem dados suficientes para motivos de não acesso.')

    with col_b:
        st.subheader('Top 3 dificuldades na captação de recursos públicos')
        colunas_dificuldades = [c for c in filtrado.columns if normalizar_texto(c).startswith(normalizar_texto('16. Identifique até três principais'))]
        serie_dificuldades = {}
        for coluna in colunas_dificuldades:
            rotulo = coluna.split('(', 1)[1].rsplit(')', 1)[0].strip() if '(' in coluna and ')' in coluna else coluna
            if 'nao temos dificuldades' in normalizar_texto(rotulo):
                continue
            serie_dificuldades[rotulo] = int(para_bool(filtrado[coluna]).sum())
        serie_dificuldades = pd.Series(serie_dificuldades).sort_values(ascending=False)
        top_dificuldades = serie_dificuldades.head(3)
        base_dificuldades = max(int(serie_dificuldades.sum()), 1)
        if not top_dificuldades.empty:
            itens = [f"- *{rotulo}* **{valor}** (**{perc:.1f}%**)" for rotulo, valor in top_dificuldades.items() for perc in [(valor / base_dificuldades) * 100]]
            st.markdown("\n".join(itens))
        else:
            st.info('Sem dados suficientes para dificuldades de captação.')


def pagina_mercados_comercializacao():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'mercados')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Mercados e Comercialização')
    st.markdown('Painel sobre geração de receita própria, tipos de venda e uso dos recursos obtidos.')

    col_comercializa = encontrar_coluna(filtrado.columns, '21. O Ponto de Cultura comercializou (vendeu) produtos e/ou serviços nos últimos 24 meses?')
    comercializa = para_bool(filtrado[col_comercializa]) if col_comercializa else pd.Series(dtype=bool)
    base_comercializa = filtrado[comercializa] if not comercializa.empty else filtrado.copy()
    total_comercializa = max(len(base_comercializa), 1)
    total_filtrado = max(len(filtrado), 1)

    dicionario_produtos = {
        'Produtos  (Artesanato)': 'Artesanato',
        'Produtos  (Produtos de divulgação do ponto de cultura (camisetas, souvernirs, chaveiros etc))': 'Produtos de divulgação',
        'Produtos  (Instrumentos musicais)': 'Instrumentos musicais',
        'Produtos  (Produtos alimentícios beneficiados)': 'Produtos alimentícios',
        'Produtos  (Alimentos in natura)': 'Alimentos in natura',
        'Produtos  (Vestuário)': 'Vestuário',
        'Produtos  (Obras artísticas (pinturas, esculturas, etc))': 'Obras artísticas',
        'Produtos  (Livros e publicações (revistas, catálogos, jornais e etc))': 'Livros e publicações',
        'Produtos  (Outros)': 'Outros'
    }
    dicionario_servicos = {
        'Serviços (Serviços educacionais (aulas, palestras oficinas, cursos etc))': 'Serviços educacionais',
        'Serviços (Apresentações artísticas e eventos culturais)': 'Apresentações artísticas',
        'Serviços (Gestão e produção cultural)': 'Gestão e produção cultural',
        'Serviços (Locação de espaços e equipamentos)': 'Locação de espaços',
        'Serviços (Serviços audiovisuais)': 'Serviços audiovisuais',
        'Serviços (Serviços de confecção têxtil (costura, figurinos, consertos etc))': 'Serviços de confecção',
        'Serviços (Outros)': 'Outros'
    }

    serie_produtos = serie_multiselecionada(base_comercializa, dicionario_produtos)
    serie_servicos = serie_multiselecionada(base_comercializa, dicionario_servicos)
    top_produto = serie_produtos.idxmax() if not serie_produtos.empty else '-'
    top_servico = serie_servicos.idxmax() if not serie_servicos.empty else '-'
    perc_produto = (serie_produtos.max() / total_comercializa) if not serie_produtos.empty else 0
    perc_servico = (serie_servicos.max() / total_comercializa) if not serie_servicos.empty else 0

    col_estrategia = encontrar_coluna(filtrado.columns, '23. Identifique até três principais dificuldades do Ponto de Cultura para acessar mercados/comercializar produtos e/ou serviços? (Ausência de estratégia comercial)')
    perc_estrategia = (para_bool(filtrado[col_estrategia]).mean()) if col_estrategia else 0

    st.subheader('Resumo das principais métricas')
    st.metric('Comercializam', f'{(comercializa.mean() if not comercializa.empty else 0):.1%}')

    col_fluxo, col_justo = st.columns([0.65, 0.35])
    with col_fluxo:
        dicionario_destinacao = {
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Custeio das despesas obtidas com a própria ação cultural realizada)': 'Custeio da ação',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Fundo de caixa)': 'Fundo de caixa',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Investimento em infraestrutura (reforma do espaço, compra de equipamento, maquinário, etc))': 'Infraestrutura',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Aplicações ﬁnanceiras)': 'Aplicações financeiras',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Divisão entre os participantes)': 'Divisão entre participantes',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Revertido para a associação associação/Ponto de Cultura)': 'Revertido para o Ponto',
            '21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda. (Outra)': 'Outros'
        }
        serie_destinacao = serie_multiselecionada(base_comercializa, dicionario_destinacao)
        if not serie_destinacao.empty:
            fig_dest = grafico_barras_series(serie_destinacao, 'Destinação do recurso', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=360)
            fig_dest.update_layout(margin=dict(l=10, r=80, t=40, b=10))
            mostrar_grafico(fig_dest, 'Destinação do recurso')
        else:
            st.info('Sem dados suficientes para o fluxo de destinação do recurso.')
    with col_justo:
        col_justo_base = encontrar_coluna(filtrado.columns, '22. O Ponto de Cultura possui relação comercial com o mercado justo e solidário?')
        serie_justo = serie_tem_nao(filtrado, col_justo_base, 'Sim', 'Não') if col_justo_base else pd.Series(dtype=int)
        if not serie_justo.empty:
            mostrar_grafico(grafico_donut(serie_justo, 'Relação com mercado justo/solidário', altura=360), 'Relação com mercado justo/solidário')
        else:
            st.info('Sem dados suficientes sobre mercado justo/solidário.')

    col_prod, col_serv = st.columns(2)
    with col_prod:
        produtos_top = serie_produtos.sort_values(ascending=False).head(5)
        if not produtos_top.empty:
            fig_prod = grafico_barras_series(produtos_top, 'Produtos mais comercializados', cor=PALETA_CORES['azul_principal'], horizontal=False, altura=360)
            fig_prod.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            mostrar_grafico(fig_prod, 'Produtos mais comercializados')
        else:
            st.info('Sem dados suficientes de produtos.')
    with col_serv:
        servicos_top = serie_servicos.sort_values(ascending=False).head(5)
        if not servicos_top.empty:
            fig_serv = grafico_barras_series(servicos_top.sort_values(ascending=True), 'Serviços mais comercializados', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=360)
            fig_serv.update_layout(margin=dict(l=10, r=80, t=40, b=10))
            mostrar_grafico(fig_serv, 'Serviços mais comercializados')
        else:
            st.info('Sem dados suficientes de serviços.')


def pagina_economias_singulares():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'economias_singulares')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Economias Singulares (Solidariedade)')
    st.markdown('A economia invisível se revela na mobilização coletiva, nas práticas tradicionais e na força das redes comunitárias.')

    total_registros = max(len(filtrado), 1)
    col_mobiliza = encontrar_coluna(filtrado.columns, '17. O Ponto de Cultura mobilizou recursos não-monetários de colaboração e solidariedade nos últimos 24 meses?')
    col_pratica = encontrar_coluna(filtrado.columns, '24. O Ponto de Cultura realiza ou participa de práticas culturais, espirituais ou produtivas de base tradicional ou popular')
    col_voluntario = encontrar_coluna(filtrado.columns, '17. 1. Se sim, quais? (Trabalho voluntário)')

    mobilizam = int(para_bool(filtrado[col_mobiliza]).sum()) if col_mobiliza else 0
    praticas = int(para_bool(filtrado[col_pratica]).sum()) if col_pratica else 0
    voluntario = int(para_bool(filtrado[col_voluntario]).sum()) if col_voluntario else 0
    base_mobilizam = max(mobilizam, 1)

    col1, col2, col3 = st.columns(3)
    col1.metric('Mobilizam Rec. Não-Monetários', f"{(mobilizam / total_registros) * 100:.1f}%")
    col2.metric('Prática Ancestral', f"{(praticas / total_registros) * 100:.1f}%")
    col3.metric('Principal Recurso: Trabalho Voluntário', f"{(voluntario / base_mobilizam) * 100:.1f}%")

    col_esq, col_dir = st.columns([0.6, 0.4])
    with col_esq:
        st.subheader('Tipos de Recursos Não-Monetários')
        st.caption('Revela o peso das trocas solidárias que sustentam as ações culturais.')
        dicionario_recursos = {
            'Trabalho voluntário': 'Voluntariado',
            'Ações de ajuda mútua (mutirões, ações comunitárias, iniciativas beneﬁcentes, etc)': 'Mutirões',
            'Doações não-monetárias (equipamentos, mobiliários, espaços, vestuário, etc.)': 'Doações',
            'Trocas diretas de produtos e serviços': 'Trocas'
        }
        dados_recursos = {}
        for busca, rotulo in dicionario_recursos.items():
            coluna = encontrar_coluna(filtrado.columns, f'17. 1. Se sim, quais? ({busca})')
            if coluna:
                dados_recursos[rotulo] = int(para_bool(filtrado[coluna]).sum())
        serie_recursos = pd.Series(dados_recursos)
        if not serie_recursos.empty:
            serie_percentual = (serie_recursos / base_mobilizam * 100).round(1).sort_values(ascending=True)
            mostrar_grafico(grafico_barras_series(serie_percentual, 'Recursos não-monetários (%)', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=420, mostrar_percentual=False), 'Recursos não-monetários (%)')
        else:
            st.info('Sem dados para recursos não-monetários.')
    with col_dir:
        st.subheader('Práticas Ancestrais')
        st.caption('Aponta a presença de saberes tradicionais que geram renda e pertencimento.')
        col_descricao = encontrar_coluna(filtrado.columns, '24. 1. Se sim, descreva brevemente as práticas e atividades realizadas')
        praticas_texto = filtrado[col_descricao].fillna('').astype(str).apply(normalizar_texto) if col_descricao else pd.Series(dtype=str)
        dados_praticas = {
            'Festas populares': praticas_texto.str.contains('festa|festejo|folia').sum() if not praticas_texto.empty else 0,
            'Rituais': praticas_texto.str.contains('ritual|reza|cerimonia|culto|terreiro').sum() if not praticas_texto.empty else 0,
            'Artesanato': praticas_texto.str.contains('artesan|bordad|croche|ceram|costur|biojoia|tecel').sum() if not praticas_texto.empty else 0
        }
        serie_praticas = pd.Series(dados_praticas).sort_values(ascending=True)
        if serie_praticas.sum() > 0:
            mostrar_grafico(grafico_barras_series(serie_praticas, 'Tipos de práticas ancestrais', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=320), 'Tipos de práticas ancestrais')
        else:
            st.info('Sem descrições suficientes para classificar práticas.')


def pagina_articulacao_rede():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'articulacao_rede')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Articulação em Rede')
    st.markdown('Conexão política, participação social e trocas entre Pontos de Cultura.')

    total_registros = max(len(filtrado), 1)
    col_participa = encontrar_coluna(filtrado.columns, '34. O Ponto de Cultura é integrado a algum espaço de participação social?')
    participa = para_bool(filtrado[col_participa]) if col_participa else pd.Series(dtype=bool)
    pct_participa = participa.mean() if not participa.empty else 0
    base_participa = filtrado[participa] if not participa.empty else filtrado.copy()
    total_participa = max(len(base_participa), 1)

    col_nao_federal = encontrar_coluna(filtrado.columns, 'Esfera Nacional (Não participa)')
    col_nao_estadual = encontrar_coluna(filtrado.columns, 'Esfera Estadual (Não participa)')
    col_nao_municipal = encontrar_coluna(filtrado.columns, 'Esfera Municipal (Não participa)')

    def pct_esfera(coluna):
        if not coluna or base_participa.empty:
            return 0, 0
        nao = int(para_bool(base_participa[coluna]).sum())
        sim = max(total_participa - nao, 0)
        return sim / total_participa, nao / total_participa

    participa_mun, nao_mun = pct_esfera(col_nao_municipal)
    participa_est, nao_est = pct_esfera(col_nao_estadual)
    participa_fed, nao_fed = pct_esfera(col_nao_federal)

    col_demanda = encontrar_coluna(filtrado.columns, '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Parceria em projetos artístico e culturais)')
    demanda_parceria = para_bool(filtrado[col_demanda]).mean() if col_demanda else 0

    k1, k2, k3 = st.columns(3)
    k1.metric('Participação social (geral)', f'{pct_participa:.1%}')
    k2.metric('Participação municipal', f'{participa_mun:.1%}')
    k3.metric('Demanda principal: Parcerias', f'{demanda_parceria:.1%}')

    col_esq, col_dir = st.columns([0.4, 0.6])
    with col_esq:
        esferas = ['Municipal', 'Estadual', 'Federal']
        participa_vals = [participa_mun, participa_est, participa_fed]
        nao_vals = [nao_mun, nao_est, nao_fed]
        fig_participa = go.Figure()
        fig_participa.add_trace(go.Bar(x=esferas, y=participa_vals, name='Participa', marker_color=PALETA_CORES['azul_principal'], text=[f'{v:.1%}' for v in participa_vals], textposition='outside'))
        fig_participa.add_trace(go.Bar(x=esferas, y=nao_vals, name='Não participa', marker_color=PALETA_CORES['cinza_medio'], text=[f'{v:.1%}' for v in nao_vals], textposition='outside'))
        fig_participa.update_layout(title='Participação por esfera', barmode='group', height=420, margin=dict(l=10, r=80, t=40, b=10), legend_title_text='')
        fig_participa.update_yaxes(title='', tickformat='.0%', range=[0, 1])
        fig_participa.update_xaxes(title='')
        mostrar_grafico(fig_participa, '', config_extra={'displayModeBar': 'hover'})

    with col_dir:
        dicionario_oferta = {
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Espaço físico)': 'Espaço físico',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Equipamentos)': 'Equipamentos',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Gestão Compartilhada da Política Nacional Cultura Viva)': 'Gestão Compartilhada da Política Nacional Cultura Viva',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Intercâmbios artísticos, estéticos e culturais)': 'Intercâmbios artísticos, estéticos e culturais',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Parceria em projetos artístico e culturais)': 'Parceria em projetos artístico e culturais',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Serviços de comunicação e difusão)': 'Serviços de comunicação e difusão',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Serviços de formação)': 'Serviços de formação',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Serviços de tecnologias da informação)': 'Serviços de tecnologias da informação',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Trocas de produtos e serviços)': 'Trocas de produtos e serviços',
            '35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva? (Troca de conhecimentos e metodologias de trabalho e mediação)': 'Troca de conhecimentos e metodologias de trabalho e mediação'
        }
        dicionario_demanda = {
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Assessoria contábil)': 'Assessoria contábil',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Assessoria jurídica)': 'Assessoria jurídica',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Espaço físico)': 'Espaço físico',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Equipamentos)': 'Equipamentos',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Gestão Compartilhada da Política Nacional Cultura Viva)': 'Gestão Compartilhada da Política Nacional Cultura Viva',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Intercâmbios artísticos, estéticos e culturais)': 'Intercâmbios artísticos, estéticos e culturais',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Parceria em projetos artístico e culturais)': 'Parceria em projetos artístico e culturais',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Serviços de comunicação e difusão)': 'Serviços de comunicação e difusão',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Serviços de formação)': 'Serviços de formação',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Serviços de tecnologias da informação)': 'Serviços de tecnologias da informação',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Trocas de produtos e serviços)': 'Trocas de produtos e serviços',
            '36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva: (Troca de conhecimentos e metodologias de trabalho e mediação)': 'Troca de conhecimentos e metodologias de trabalho e mediação'
        }
        oferta = {rotulo: int(para_bool(filtrado[coluna]).sum()) for coluna, rotulo in dicionario_oferta.items() if coluna in filtrado.columns}
        demanda = {rotulo: int(para_bool(filtrado[coluna]).sum()) for coluna, rotulo in dicionario_demanda.items() if coluna in filtrado.columns}
        categorias = sorted(set(oferta) | set(demanda))
        if categorias:
            df_gap = pd.DataFrame({'categoria': categorias, 'oferta': [oferta.get(c, 0) for c in categorias], 'demanda': [demanda.get(c, 0) for c in categorias]})
            df_gap['oferta'] = df_gap['oferta'] / total_registros
            df_gap['demanda'] = df_gap['demanda'] / total_registros
            df_gap = df_gap.sort_values('demanda', ascending=False).head(8)
            max_val = max(df_gap['oferta'].max(), df_gap['demanda'].max(), 0.1)
            fig_gap = go.Figure()
            fig_gap.add_trace(go.Bar(y=df_gap['categoria'], x=-df_gap['oferta'], name='Oferta', orientation='h', marker_color=PALETA_CORES['cinza_medio'], text=[f'{v:.1%}' for v in df_gap['oferta']], textposition='outside'))
            fig_gap.add_trace(go.Bar(y=df_gap['categoria'], x=df_gap['demanda'], name='Demanda', orientation='h', marker_color=PALETA_CORES['azul_principal'], text=[f'{v:.1%}' for v in df_gap['demanda']], textposition='outside'))
            fig_gap.update_layout(title='Oferta x Demanda na Rede Cultura Viva', barmode='relative', height=420, margin=dict(l=10, r=80, t=40, b=10), legend_title_text='')
            fig_gap.update_xaxes(title='', tickformat='.0%', range=[-max_val, max_val])
            fig_gap.update_yaxes(title='', autorange='reversed')
            mostrar_grafico(fig_gap, '', config_extra={'displayModeBar': 'hover'})
        else:
            st.info('Sem dados suficientes para o comparativo de oferta e demanda.')


def pagina_gestao_mundo_trabalho():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'gestao_trabalho')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return

    st.title('Gestão e Mundo do Trabalho')
    st.markdown('Quem trabalha e como são pagos.')

    col_volunt = encontrar_coluna(filtrado.columns, 'Trabalhadores voluntários (parceiros e colaboradores)')
    col_clt = encontrar_coluna(filtrado.columns, 'Pessoas com vínculo empregatício (CLT)')
    col_mei = encontrar_coluna(filtrado.columns, 'Prestadores de serviços contratados como MEI')
    col_renda = encontrar_coluna(filtrado.columns, '30. Qual a porcentagem aproximada de pessoas que trabalham no Ponto de Cultura e tiveram nesse trabalho sua principal fonte de renda nos últimos 24 meses?')
    col_planilha = encontrar_coluna(filtrado.columns, '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Planilha de custos por projeto)')
    col_software = encontrar_coluna(filtrado.columns, '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Software ou aplicativo de contabilidade/finanças)')

    def mediana_coluna(coluna):
        if not coluna:
            return 0
        serie = pd.to_numeric(filtrado[coluna], errors='coerce').dropna()
        return int(serie.median()) if not serie.empty else 0

    mediana_volunt = mediana_coluna(col_volunt)
    mediana_clt = mediana_coluna(col_clt)
    perc_planilha = para_bool(filtrado[col_planilha]).mean() if col_planilha else 0
    perc_software = para_bool(filtrado[col_software]).mean() if col_software else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Mediana Voluntários', f'{mediana_volunt}')
    k2.metric('Mediana CLT', f'{mediana_clt}')
    k3.metric('Usa Planilha de Custos', f'{perc_planilha:.1%}')
    k4.metric('Usa Software de Gestão', f'{perc_software:.1%}')

    st.subheader('Distribuição de trabalhadores por tipo de vínculo')
    st.caption('Mostra a base real de sustentação da equipe e evidencia a raridade de vínculos formais.')
    dados_vinculo = []
    for coluna, rotulo in [(col_volunt, 'Voluntários'), (col_clt, 'CLT'), (col_mei, 'MEI')]:
        if coluna:
            serie = pd.to_numeric(filtrado[coluna], errors='coerce').dropna()
            serie = serie[serie >= 0]
            if not serie.empty:
                q1 = serie.quantile(0.25)
                q3 = serie.quantile(0.75)
                iqr = q3 - q1
                p99 = serie.quantile(0.99)
                limite = min(q3 + 1.5 * iqr, p99) if iqr > 0 else p99
                serie = serie[serie <= limite]
                dados_vinculo.append(pd.DataFrame({'vinculo': rotulo, 'quantidade': serie}))
    if dados_vinculo:
        df_vinculo = pd.concat(dados_vinculo, ignore_index=True)
        fig_box = grafico_boxplot(df_vinculo, 'vinculo', 'quantidade', 'Distribuição por vínculo', altura=420)
        fig_box.update_xaxes(categoryorder='array', categoryarray=['Voluntários', 'CLT', 'MEI'])
        mostrar_grafico(fig_box, 'Distribuição por vínculo')
    else:
        st.info('Sem dados suficientes para o boxplot de vínculos.')

    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.subheader('Capacidade de Geração de Renda para a Equipe')
        st.caption('Mostra a proporção de pessoas cuja principal fonte de renda vem do Ponto.')
        if col_renda:
            serie_renda = filtrado[col_renda].fillna('').astype(str)
            mapa_rotulos = {
                'Menos de 10% das pessoas trabalhadoras do Ponto de Cultura': 'Menos de 10% das pessoas'
            }
            serie_renda = serie_renda.replace(mapa_rotulos)
            ordem = [
                'Nenhuma pessoa (0%)',
                'Menos de 10% das pessoas',
                'Entre 10% e 25% das pessoas',
                'Entre 26% e 50% das pessoas',
                'Entre 51% e 75% das pessoas',
                'Mais de 75% das pessoas',
                'Não sei informar'
            ]
            contagens = serie_renda.value_counts().reindex(ordem, fill_value=0)
            if contagens.sum() > 0:
                mostrar_grafico(
                    grafico_barras_series(contagens, 'Capacidade de Geração de Renda para a Equipe', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=320),
                    'Capacidade de Geração de Renda para a Equipe'
                )
            else:
                st.info('Sem respostas válidas para capacidade de geração de renda.')
        else:
            st.info('Sem coluna de capacidade de geração de renda na base.')

    with col_dir:
        st.subheader('Ferramentas de gestão financeira utilizadas')
        st.caption('Indica o nível de organização administrativa e capacidade de controle financeiro.')
        dicionario_gestao = {
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Orçamento anual formalizado (planilha ou documento escrito))': 'Orçamento anual formalizado',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Controle mensal de fluxo de caixa)': 'Fluxo de caixa mensal',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Planilha de custos por projeto)': 'Planilha de custos por projeto',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Software ou aplicativo de contabilidade/finanças)': 'Software de contabilidade',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Assessoria contábil externa ou contador permanente)': 'Assessoria contábil',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Nenhuma das opções acima)': 'Nenhuma das opções',
            '31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Outros)': 'Outros'
        }
        serie_gestao = serie_multiselecionada(filtrado, dicionario_gestao)
        if not serie_gestao.empty:
            mostrar_grafico(
                grafico_barras_series(serie_gestao, 'Ferramentas de gestão financeira', cor=PALETA_CORES['azul_principal'], horizontal=True, altura=320),
                'Ferramentas de gestão financeira'
            )
        else:
            st.info('Sem dados suficientes para ferramentas de gestão.')


def pagina_cruzamentos_estrategicos():
    mostrar_cabecalho()
    df = preparar_base('v2')
    filtrado, resumo = painel_filtros(df, 'cruzamentos_estrategicos')
    st.caption(f"Registros filtrados: **{len(filtrado):,}** • Filtros ativos: {resumo}".replace(',', '.'))
    if filtrado.empty:
        st.warning('Nenhum registro com os filtros atuais.')
        return
    st.title('Cruzamentos Estratégicos (Análise Avançada)')
    st.markdown('Correlações e descobertas finais.')

    colunas_vinculo = {
        'Pessoas com vínculo empregatício (CLT)': 'CLT',
        'Prestadores de serviços contratados como MEI': 'MEI',
        'Trabalhadores voluntários (parceiros e colaboradores)': 'Voluntariado'
    }
    dados_bolhas = []
    faixas_disponiveis = [f for f in FAIXAS_RECEITA if f in filtrado['faixa_receita'].dropna().unique()]
    for faixa in faixas_disponiveis:
        base_faixa = filtrado[filtrado['faixa_receita'] == faixa]
        for coluna, rotulo in colunas_vinculo.items():
            if coluna not in base_faixa.columns:
                continue
            serie = base_faixa[coluna]
            numerico = pd.to_numeric(serie, errors='coerce')
            presenca = (numerico.fillna(0) > 0) if numerico.notna().any() else para_bool(serie)
            dados_bolhas.append({'faixa_receita': faixa, 'vinculo': rotulo, 'qtde': int(presenca.sum())})
    df_bolhas = pd.DataFrame(dados_bolhas)

    st.subheader('Vínculo de trabalho por faixa de receita')
    st.caption('Leitura direta da distribuição de vínculos por faixa de receita.')
    if not df_bolhas.empty:
        matriz = df_bolhas.pivot(index='vinculo', columns='faixa_receita', values='qtde').reindex(index=['Voluntariado', 'CLT', 'MEI'], columns=FAIXAS_RECEITA).fillna(0)
        fig_heat = go.Figure(data=go.Heatmap(
            z=matriz.values,
            x=list(matriz.columns),
            y=list(matriz.index),
            colorscale=['#EBF5FF', PALETA_CORES['azul_principal']],
            colorbar=dict(title='Qtde')
        ))
        fig_heat.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
        fig_heat.update_xaxes(title='', tickangle=-25)
        fig_heat.update_yaxes(title='')
        mostrar_grafico(fig_heat, 'Vínculo de trabalho por faixa de receita')
    else:
        st.info('Sem dados suficientes para o gráfico de vínculos.')

    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.subheader('Ação estruturante por território')
        st.caption('Compara o foco das ações quando o engajamento se dá por municípios ou por redes.')
        colunas_municipio = [c for c in filtrado.columns if str(c).startswith('Esfera Municipal')]
        colunas_rede = [c for c in filtrado.columns if str(c).startswith('Redes de articulação setorial') or 'Rede Estadual de Pontos de Cultura' in str(c)]

        def tem_participacao(colunas):
            if not colunas:
                return pd.Series([False] * len(filtrado), index=filtrado.index)
            base = pd.concat([para_bool(filtrado[c]) for c in colunas if c in filtrado.columns], axis=1)
            return base.any(axis=1)

        mask_municipio = tem_participacao(colunas_municipio)
        mask_rede = tem_participacao(colunas_rede)

        acoes_temas = [
            'Cultura e Direitos Humanos',
            'Cultura e Educação',
            'Cultura e Juventude',
            'Cultura e Meio Ambiente',
            'Cultura e Saúde',
            'Cultura e Mulheres',
            'Gênero e Diversidade',
            'Acessibilidade Cultural e Equidade',
            'Cultura e Territórios Rurais',
            'Cultura, Territórios de Fronteira e Integração Latino-americana',
            'Culturas Populares',
            'Culturas Tradicionais',
            'Culturas de Matriz Africana',
            'Culturas Indígenas',
            'Memória e Patrimônio cultural',
            'Mestres e Mestras das Culturas Tradicionais e Populares',
            'Cultura, Infância e Adolescência'
        ]
        acoes_ferramentas = [
            'Cultura Digital',
            'Cultura, Comunicação e Mídia livre',
            'Economia criativa e solidária',
            'Intercâmbio e residências',
            'Linguagens Artísticas',
            'Livro, leitura e literatura',
            'Cultura Hip Hop',
            'Agente cultura viva',
            'Conhecimentos tradicionais'
        ]

        def conta_grupo(mask, acoes):
            colunas = [c for c in acoes if c in filtrado.columns]
            if not colunas:
                return 0
            base = pd.concat([para_bool(filtrado[c]) for c in colunas], axis=1)
            return int(base.any(axis=1)[mask].sum())

        dados_territorio = pd.DataFrame([
            {
                'territorio': 'Municípios',
                'Temas sociais': conta_grupo(mask_municipio, acoes_temas),
                'Ferramentas': conta_grupo(mask_municipio, acoes_ferramentas)
            },
            {
                'territorio': 'Redes',
                'Temas sociais': conta_grupo(mask_rede, acoes_temas),
                'Ferramentas': conta_grupo(mask_rede, acoes_ferramentas)
            }
        ])
        if dados_territorio[['Temas sociais', 'Ferramentas']].sum().sum() > 0:
            fig_territorio = go.Figure()
            fig_territorio.add_trace(go.Bar(x=dados_territorio['territorio'], y=dados_territorio['Temas sociais'], name='Temas sociais', marker_color=PALETA_CORES['azul_principal'], opacity=0.85))
            fig_territorio.add_trace(go.Bar(x=dados_territorio['territorio'], y=dados_territorio['Ferramentas'], name='Ferramentas', marker_color=PALETA_CORES['azul_principal'], opacity=0.45))
            fig_territorio.update_layout(barmode='stack', height=360, margin=dict(l=10, r=10, t=40, b=10))
            fig_territorio.update_xaxes(title='')
            fig_territorio.update_yaxes(title='')
            mostrar_grafico(fig_territorio, 'Ação estruturante por território')
        else:
            st.info('Sem dados suficientes para o cruzamento de território.')

    with col_dir:
        st.subheader('Formalização (CNPJ) por faixa de receita')
        st.caption('Evidencia a correlação positiva entre receita e formalização jurídica.')
        if 'registro' in filtrado.columns:
            registro_norm = filtrado['registro'].fillna('').map(normalizar_texto)
            mask_cnpj = registro_norm.str.contains('cnpj')
            dados_cnpj = []
            for faixa in faixas_disponiveis:
                base_faixa = filtrado['faixa_receita'] == faixa
                total_faixa = int(base_faixa.sum())
                perc_cnpj = (mask_cnpj[base_faixa].sum() / total_faixa * 100) if total_faixa else 0
                dados_cnpj.append({'faixa_receita': faixa, 'percentual': round(perc_cnpj, 1)})
            df_cnpj = pd.DataFrame(dados_cnpj)
            if not df_cnpj.empty:
                fig_cnpj = go.Figure(go.Bar(
                    x=df_cnpj['faixa_receita'],
                    y=df_cnpj['percentual'],
                    marker_color=PALETA_CORES['azul_principal'],
                    text=[f'{v:.1f}%' for v in df_cnpj['percentual']],
                    textposition='outside',
                    cliponaxis=False
                ))
                fig_cnpj.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
                fig_cnpj.update_xaxes(title='', categoryorder='array', categoryarray=FAIXAS_RECEITA, tickangle=-25)
                fig_cnpj.update_yaxes(title='', ticksuffix='%')
                mostrar_grafico(fig_cnpj, 'Formalização (CNPJ) por faixa de receita')
            else:
                st.info('Sem dados suficientes para formalização por receita.')
        else:
            st.info('Sem coluna de cadastro jurídico para medir formalização.')



