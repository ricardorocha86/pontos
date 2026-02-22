import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb, n_colors
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import preparar_base, aplicar_filtros, para_bool, ACOES_ESTRUTURANTES, encontrar_coluna
from components import mostrar_grafico, grafico_barras_series, grafico_donut
from config import PALETA_CORES, FONTE_FAMILIA, FONTE_TAMANHOS
from relatorio_pagina import definir_aba_relatorio

st.title("B) Atuação Cultural")
definir_aba_relatorio("Abrangência Territorial e Ações Estruturantes")
st.markdown(
    """
Esta página analisa como os Pontos e Pontões atuam no território e no ecossistema cultural, conectando abrangência de atuação, linguagens artísticas e dimensões de trabalho prioritárias. Ela ajuda a compreender a vocação pedagógica, produtiva e comunitária das iniciativas, além da coexistência de múltiplas frentes de atuação em um mesmo coletivo. O conjunto dos gráficos permite comparar intensidade, diversidade e foco das práticas culturais. Nesta seção, você verá conteúdos associados às questões Q9 a Q12 do formulário.
"""
)

df = preparar_base()
if 'filtros_globais' in st.session_state:
    df = aplicar_filtros(df, st.session_state['filtros_globais'])

# Abas
tab1, tab2, tab3 = st.tabs([
    "Abrangência Territorial e Ações Estruturantes",
    "Linguagens Artísticas e Ecossistema",
    "Detalhamento por Linguagem Artística"
])

with tab1:
    definir_aba_relatorio("Abrangência Territorial e Ações Estruturantes")
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

        valid_cols = []
        for col in dados.columns:
            if not dados[col].dropna().empty:
                valid_cols.append(col)

        if not valid_cols:
            return None

        contagens = {col: dados[col].value_counts().reindex(ordem, fill_value=0).to_list() for col in valid_cols}
        df_final = pd.DataFrame({'Frequência': ordem, **contagens})
        df_contagens = df_final.set_index('Frequência').reindex(ordem)

        totais = df_contagens.sum(axis=0).replace(0, 1)
        df_proporcoes = df_contagens.div(totais, axis=1)

        if 'Sempre' in df_proporcoes.index:
            cols_sorted = df_proporcoes.loc['Sempre'].sort_values(ascending=False).index.tolist()
            df_proporcoes = df_proporcoes[cols_sorted]
            df_contagens = df_contagens[cols_sorted]

        variaveis = df_proporcoes.columns

        cor_inicial = f"rgb{hex_to_rgb(PALETA_CORES['principais'][1])}"
        cor_final = f"rgb{hex_to_rgb('#EBF5FF')}"
        cores = n_colors(cor_inicial, cor_final, len(df_proporcoes.index), colortype='rgb')

        fig = go.Figure()
        for i, categoria in enumerate(df_proporcoes.index):
            proporcoes = df_proporcoes.loc[categoria].tolist()
            contagens_vals = df_contagens.loc[categoria].tolist()
            texto = [f'{c}<br>({v:.1%})' if v > 0.05 else '' for c, v in zip(contagens_vals, proporcoes)]

            fig.add_trace(go.Bar(
                x=variaveis,
                y=proporcoes,
                name=categoria,
                marker_color=cores[i],
                text=texto,
                textposition='inside'
            ))

        fig.update_layout(
            barmode='stack',
            yaxis=dict(tickformat='.0%'),
            legend_title_text='Frequência',
            height=560,
            font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS['geral'])
        )
        return fig

    col_esq, col_dir = st.columns([3, 2])

    with col_esq:
        fig_abrangencia = grafico_abrangencia_empilhado(df)
        if fig_abrangencia:
            mostrar_grafico(fig_abrangencia, "Abrangência Territorial das Ações")
        else:
            st.info("Sem dados de abrangência territorial.")

    with col_dir:
        acoes_estruturantes = [
            "Conhecimentos tradicionais",
            "Cultura Hip Hop",
            "Cultura Alimentar",
            "Cultura Circense",
            "Cultura Digital",
            "Cultura e Mulheres",
            "Cultura e Territórios Rurais",
            "Cultura e Direitos Humanos",
            "Cultura e Educação",
            "Cultura e Juventude",
            "Cultura e Meio Ambiente",
            "Cultura e Saúde",
            "Cultura Urbana e Direito à Cidade",
            "Cultura, Territórios de Fronteira e Integração Latino-americana",
            "Cultura, Comunicação e Mídia livre",
            "Cultura, Infância e Adolescência",
            "Culturas Populares",
            "Culturas Tradicionais",
            "Culturas de Matriz Africana",
            "Culturas Indígenas",
            "Economia criativa e solidária",
            "Gênero e Diversidade",
            "Intercâmbio e residências",
            "Linguagens Artísticas",
            "Livro, leitura e literatura",
            "Memória e Patrimônio cultural",
            "Mestres e Mestras das Culturas Tradicionais e Populares",
            "Acessibilidade Cultural e Equidade",
            "Outras ações estruturantes"
        ]

        colunas_acao = [c for c in acoes_estruturantes if c in df.columns]
        if colunas_acao:
            resultado = df[colunas_acao].sum().sort_values(ascending=False)
            top_acoes = resultado.head(15).sort_values(ascending=True)

            # Encurta labels no eixo para aumentar área de barras no layout 40%
            def _encurtar_label(txt, limite=34):
                t = str(txt)
                return t if len(t) <= limite else f"{t[:limite - 1]}..."

            labels_originais = list(top_acoes.index)
            labels_encurtados = [_encurtar_label(lbl) for lbl in labels_originais]

            # Garante unicidade no eixo após truncamento
            vistos = {}
            labels_finais = []
            for lbl in labels_encurtados:
                if lbl not in vistos:
                    vistos[lbl] = 1
                    labels_finais.append(lbl)
                else:
                    vistos[lbl] += 1
                    labels_finais.append(f"{lbl} ({vistos[lbl]})")

            top_acoes_plot = top_acoes.copy()
            top_acoes_plot.index = labels_finais

            fig_acoes = grafico_barras_series(
                top_acoes_plot,
                'Top 15 Ações Estruturantes',
                cor=PALETA_CORES['secundarias'][0],
                horizontal=True,
                altura=560
            )
            # Usa label completo no hover e reduz margens laterais para dar mais área às barras
            fig_acoes.update_traces(
                customdata=labels_originais,
                hovertemplate='%{customdata}<br>Frequência: %{x}<extra></extra>',
            )
            fig_acoes.update_layout(margin=dict(l=16, r=28, t=62, b=24))
            mostrar_grafico(fig_acoes, 'Top 15 Ações Estruturantes')
        else:
            st.info("Sem dados de ações estruturantes.")

with tab2:
    definir_aba_relatorio("Linguagens Artísticas e Ecossistema")
    c1, c2 = st.columns([2, 3])

    with c1:
        colunas_linguagens = {
            'Artes Visuais': 'categorias artes visuais',
            'Audiovisual': 'Audiovisual',
            'Dança': 'Dança',
            'Teatro': 'Teatro',
            'Música': 'Música',
            'Literatura': 'Literatura',
            'Circo': 'Circo',
            'Hip Hop': 'Hip Hop',
            'Outras linguagens artísticas': 'Outras linguagens artísticas',
        }
        dados_grafico = {}
        for label, alvo in colunas_linguagens.items():
            col = encontrar_coluna(df.columns, alvo)
            dados_grafico[label] = int(df[col].notna().sum()) if col else 0

        freq_series = pd.Series(dados_grafico).sort_values(ascending=False)
        freq_series = freq_series[freq_series > 0]

        if not freq_series.empty:
            total_amostra = max(len(df), 1)
            fig_ling = go.Figure(
                go.Bar(
                    x=freq_series.index.tolist(),
                    y=freq_series.values.tolist(),
                    marker_color=PALETA_CORES['secundarias'][1],
                    text=[
                        f"{int(v)}<br>({(v / total_amostra) * 100:.1f}%)"
                        for v in freq_series.values.tolist()
                    ],
                    textposition='outside',
                    cliponaxis=False,
                )
            )
            fig_ling.update_layout(height=540)
            fig_ling.update_xaxes(title='')
            fig_ling.update_yaxes(title='')
            mostrar_grafico(fig_ling, "Linguagens artísticas predominantes dos Pontos de Cultura")
        else:
            st.info("Sem dados de linguagens.")

    with c2:
        variaveis_dimensoes = [
            'Concepcao e Criacao',
            'Formacao, Capacitacao e Educacao Cultural',
            'Producao e Realizacao',
            'Curadoria, Programacao e Organizacao de Eventos',
            'Registro, Documentacao e Preservacao',
            'Comunicacao e Divulgacao Cultura',
            'Circulacao e Distribuicao',
            'Comercializacao e Economia da Cultura',
            'Consumo, Fruicao e Participacao',
            'Propriedade Intelectual e Direitos Culturais',
            'Captacao e Financiamento',
            'Articulacao Institucional, Intersetorialidade e Governanca',
            'Avaliacao, Monitoramento e Pesquisa Cultural',
        ]

        colunas_dim = [encontrar_coluna(df.columns, v) for v in variaveis_dimensoes]
        colunas_dim = [c for c in colunas_dim if c is not None]

        if colunas_dim:
            dados_dim = df[colunas_dim]
            contagens = dados_dim.notna().sum().sort_values(ascending=False)
            base_relativa = int((dados_dim.notna().sum(axis=1) > 0).sum())

            s_eco = contagens.sort_values(ascending=True)
            if not s_eco.empty:
                texto = [
                    f"{int(v)}<br>({(v / base_relativa) * 100:.1f}%)" if base_relativa > 0 else f"{int(v)}"
                    for v in s_eco.values
                ]
                fig_eco = go.Figure(
                    go.Bar(
                        x=s_eco.values,
                        y=s_eco.index,
                        orientation='h',
                        marker_color=PALETA_CORES['principais'][2],
                        text=texto,
                        textposition='outside',
                        cliponaxis=False,
                    )
                )
                fig_eco.update_layout(height=540)
                fig_eco.update_xaxes(title='')
                fig_eco.update_yaxes(title='')
                mostrar_grafico(fig_eco, "Dimensões do ecossistema cultural de atuação dos Pontos de Cultura")
            else:
                st.info("Dados de ecossistema não processáveis.")
        else:
            st.info("Dimensões do ecossistema cultural não encontradas na base.")

with tab3:
    definir_aba_relatorio("Detalhamento por Linguagem Artística")
    DICIONARIO_MICRO = {
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

    dados_micro = df.rename(columns=DICIONARIO_MICRO)
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

    opcoes = [t for t, _ in grupos_micro if t in contagens_macro]
    if opcoes:
        col_controle, col_grafico = st.columns([1, 6], gap='small')

        with col_controle:
            escolha = st.radio(
                'Linguagem',
                opcoes,
                index=0,
                key='b_tab3_linguagem_micro_radio'
            )

        with col_grafico:
            colunas = dict(grupos_micro).get(escolha, [])
            colunas_validas = [c for c in colunas if c in dados_micro.columns]
            if colunas_validas:
                contagens = {c: int(para_bool(dados_micro[c]).sum()) for c in colunas_validas}
                serie = pd.Series(contagens).sort_values(ascending=True)
                fig_micro = grafico_barras_series(
                    serie,
                    f'Visão micro: {escolha}',
                    cor=PALETA_CORES['principais'][2],
                    horizontal=True,
                    altura=520,
                    mostrar_percentual=False
                )
                textos = [f'{v} ({(v / total_registros):.1%})' for v in serie.tolist()]
                fig_micro.update_traces(text=textos, textposition='outside', cliponaxis=False)
                mostrar_grafico(fig_micro, f'Visão micro: {escolha}')
            else:
                st.info('Sem dados para a linguagem selecionada.')
    else:
        st.info('Sem dados suficientes para o detalhamento micro.')





