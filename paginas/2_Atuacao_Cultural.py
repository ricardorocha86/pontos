import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import hex_to_rgb, n_colors
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils import preparar_base, aplicar_filtros, para_bool, ACOES_ESTRUTURANTES
from components import mostrar_grafico, grafico_barras_series, grafico_donut
from config import PALETA_CORES, FONTE_FAMILIA, FONTE_TAMANHOS

st.title("B) Atuação Cultural")

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
        colunas_acao = [c for c in ACOES_ESTRUTURANTES if c in df.columns]
        if colunas_acao:
            contagens = {c: int(para_bool(df[c]).sum()) for c in colunas_acao if c != 'Sem ação estruturante'}
            serie_acoes = pd.Series(contagens).sort_values(ascending=True)
            top_acoes = serie_acoes.tail(15)

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
    c1, c2 = st.columns([2, 3])

    with c1:
        termos = df['linguagem_artistica'].fillna('').astype(str).str.split(',').explode().str.strip()
        termos = termos.replace({'O Ponto de Cultura não trabalha com linguagens artísticas': 'Sem linguagens'})
        termos = termos[termos != '']
        top_linguagens = termos.value_counts().head(10)

        if not top_linguagens.empty:
            fig_ling = grafico_donut(top_linguagens, "Top 10 Linguagens Predominantes", altura=450)
            mostrar_grafico(fig_ling, "Top 10 Linguagens Predominantes")
        else:
            st.info("Sem dados de linguagens.")

    with c2:
        cols_q12 = [c for c in df.columns if str(c).strip().startswith("12.")]

        if cols_q12:
            ecosistema_counts = {}
            for col in cols_q12:
                if df[col].dtype == object and df[col].str.contains(',').any():
                    items = df[col].fillna('').astype(str).str.split(',').explode().str.strip()
                    counts = items.value_counts()
                    for k, v in counts.items():
                        if k:
                            ecosistema_counts[k] = ecosistema_counts.get(k, 0) + v
                else:
                    counts = df[col].value_counts()
                    for k, v in counts.items():
                        k_str = str(k)
                        if k_str.lower() not in ['nan', 'none', '']:
                            label = col.split('(')[-1].strip(')') if '(' in col else str(k)
                            if len(cols_q12) == 1:
                                label = str(k)
                            ecosistema_counts[label] = ecosistema_counts.get(label, 0) + v

            if ecosistema_counts:
                s_eco = pd.Series(ecosistema_counts).sort_values(ascending=True).tail(10)
                fig_eco = grafico_barras_series(
                    s_eco,
                    "Top 10 Elementos do Ecossistema Cultural",
                    cor=PALETA_CORES['principais'][2],
                    horizontal=True,
                    altura=450
                )
                mostrar_grafico(fig_eco, "Top 10 Elementos do Ecossistema Cultural")
            else:
                st.info("Dados de ecossistema não processáveis.")
        else:
            st.info("Questão 12 não encontrada nos dados.")

with tab3:
    st.markdown("Visão detalhada das categorias específicas dentro de cada linguagem.")

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


