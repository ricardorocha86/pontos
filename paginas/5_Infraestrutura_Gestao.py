import os
import sys
import textwrap
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components import grafico_barras_series, grafico_donut, mostrar_grafico
from config import FONTE_FAMILIA, FONTE_TAMANHOS, PALETA_CORES
from texto_wordcloud import gerar_wordcloud
from utils import aplicar_filtros, para_bool, preparar_base


def _norm_local(texto):
    texto = "" if texto is None else str(texto)
    texto = texto.replace("\ufb01", "fi").replace("\ufb02", "fl")
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().split())


def _encontrar_coluna_local(colunas, alvo):
    alvo_n = _norm_local(alvo)
    for coluna in colunas:
        if _norm_local(coluna) == alvo_n:
            return coluna
    for coluna in colunas:
        if alvo_n in _norm_local(coluna):
            return coluna
    return None


def _rotulo_parenteses(coluna):
    texto = str(coluna)
    if "(" in texto and ")" in texto:
        return texto.split("(", 1)[1].rsplit(")", 1)[0].strip()
    return texto


def _serie_multiescolha_por_prefixo(df, prefixo, excluir_rotulos=None):
    excluir = {_norm_local(x) for x in (excluir_rotulos or [])}
    dados = {}
    prefixo_n = _norm_local(prefixo)

    for coluna in df.columns:
        coluna_n = _norm_local(coluna)
        if not coluna_n.startswith(prefixo_n):
            continue
        if "(" not in str(coluna) or ")" not in str(coluna):
            continue

        rotulo = _rotulo_parenteses(coluna).replace("ﬁ", "fi").replace("oﬁ", "ofi")
        if _norm_local(rotulo) in excluir:
            continue

        dados[rotulo] = int(para_bool(df[coluna]).sum())

    if not dados:
        return pd.Series(dtype="int64")

    serie = pd.Series(dados, dtype="int64").sort_values(ascending=True)
    return serie[serie > 0]


def _encurtar_index_serie(serie, limite=36):
    def _encurtar(txt):
        txt = str(txt)
        return txt if len(txt) <= limite else f"{txt[:limite - 3]}..."

    novos = []
    usados = {}
    for item in serie.index:
        curto = _encurtar(item)
        if curto not in usados:
            usados[curto] = 1
            novos.append(curto)
        else:
            usados[curto] += 1
            novos.append(f"{curto} ({usados[curto]})")

    serie_out = serie.copy()
    serie_out.index = novos
    return serie_out


def _quebrar_linha_label(texto, largura=10):
    partes = textwrap.wrap(str(texto), width=largura, break_long_words=False, break_on_hyphens=False)
    return "<br>".join(partes) if partes else str(texto)


def _aplicar_percentual_base(fig, serie, base):
    base_segura = max(int(base), 1)
    textos = [f"{int(v)}<br>({(int(v) / base_segura) * 100:.1f}%)" for v in serie.tolist()]
    fig.update_traces(text=textos, textposition="outside", cliponaxis=False)
    return fig


def _ordenar_serie_sim_nao(serie):
    if serie is None or serie.empty:
        return serie

    ordem_fixa = ["sim", "nao"]
    serie_norm = pd.Series(
        serie.values,
        index=[_norm_local(idx) for idx in serie.index],
        dtype=serie.dtype,
    ).groupby(level=0).sum()

    ordem = [chave for chave in ordem_fixa if chave in serie_norm.index]
    ordem += [chave for chave in serie_norm.index if chave not in ordem]

    nomes = {"sim": "Sim", "nao": "Não"}
    serie_out = serie_norm.reindex(ordem).fillna(0)
    serie_out.index = [nomes.get(idx, idx) for idx in serie_out.index]
    return serie_out


def _aplicar_cores_donut_sim_nao(fig):
    mapa_cores = {
        "sim": PALETA_CORES["principais"][1],
        "nao": PALETA_CORES["principais"][0],
    }
    for trace in fig.data:
        raw_labels = getattr(trace, "labels", None)
        if raw_labels is None:
            continue
        labels = [str(lbl) for lbl in list(raw_labels)]
        if len(labels) == 0:
            continue
        trace.sort = False
        trace.marker.colors = [mapa_cores.get(_norm_local(lbl), PALETA_CORES["secundarias"][0]) for lbl in labels]
    fig.update_layout(legend=dict(traceorder="normal"))
    return fig


def _serie_participacao_faixas(df, coluna):
    if not coluna or coluna not in df.columns:
        return pd.Series(dtype="int64")

    base = pd.to_numeric(df[coluna], errors="coerce")
    base = base[base.notna() & (base >= 0)]
    if base.empty:
        return pd.Series(dtype="int64")

    bins = [-1, 50, 100, 300, 600, float("inf")]
    labels = ["Até 50", "51 a 100", "101 a 300", "301 a 600", "Mais de 600"]
    faixa = pd.cut(base, bins=bins, labels=labels)
    return faixa.value_counts().reindex(labels).fillna(0).astype(int)


def _mostrar_titulo_wordcloud(titulo):
    st.markdown(
        "<div style='"
        f"font-family:{FONTE_FAMILIA};"
        f"font-size:{FONTE_TAMANHOS['titulo']}px;"
        "font-weight:700;"
        "line-height:1.15;"
        "margin:0 0 6px 0;"
        "'>"
        f"{titulo}"
        "</div>",
        unsafe_allow_html=True,
    )


def _grafico_espelhado_participacao(serie_direta, serie_indireta):
    ordem = ["Até 50", "51 a 100", "101 a 300", "301 a 600", "Mais de 600"]
    direta = serie_direta.reindex(ordem).fillna(0).astype(int)
    indireta = serie_indireta.reindex(ordem).fillna(0).astype(int)

    total_direta = max(int(direta.sum()), 1)
    total_indireta = max(int(indireta.sum()), 1)

    df_plot = pd.DataFrame(
        {
            "faixa": ordem,
            "direta": direta.values,
            "indireta": indireta.values,
        }
    )
    df_plot["pct_direta"] = (df_plot["direta"] / total_direta) * 100
    df_plot["pct_indireta"] = (df_plot["indireta"] / total_indireta) * 100
    df_plot["x_direta"] = -df_plot["pct_direta"]
    df_plot["x_indireta"] = df_plot["pct_indireta"]
    df_plot["txt_direta"] = df_plot.apply(
        lambda r: f"{int(r['direta'])} ({r['pct_direta']:.1f}%)", axis=1
    )
    df_plot["txt_indireta"] = df_plot.apply(
        lambda r: f"{int(r['indireta'])} ({r['pct_indireta']:.1f}%)", axis=1
    )

    fig = go.Figure()
    fig.add_bar(
        y=df_plot["faixa"],
        x=df_plot["x_direta"],
        orientation="h",
        name="direta",
        marker_color=PALETA_CORES["secundarias"][0],
        text=df_plot["txt_direta"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Direta: %{text}<extra></extra>",
    )
    fig.add_bar(
        y=df_plot["faixa"],
        x=df_plot["x_indireta"],
        orientation="h",
        name="indireta",
        marker_color=PALETA_CORES["secundarias"][1],
        text=df_plot["txt_indireta"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Indireta: %{text}<extra></extra>",
    )

    max_x = max(float(df_plot["pct_direta"].max()), float(df_plot["pct_indireta"].max()), 1.0)
    limite = max_x * 1.30
    max_tick = max(int(limite // 10) * 10 + 10, 10)
    ticks = list(range(-max_tick, max_tick + 1, 10))

    fig.update_layout(
        barmode="relative",
        height=680,
        margin=dict(l=160, r=22, t=58, b=24),
        xaxis=dict(
            title="Percentual por tipo de participação",
            range=[-limite, limite],
            tickvals=ticks,
            ticktext=[f"{abs(t)}%" for t in ticks],
            zeroline=True,
            zerolinecolor="#8C8C8C",
            zerolinewidth=1.1,
        ),
        yaxis=dict(
            title="",
            automargin=True,
            ticklabelposition="outside",
            ticklabelstandoff=32,
        ),
        legend=dict(
            orientation="v",
            x=0.98,
            y=0.98,
            xanchor="right",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.6)",
        ),
    )
    return fig


def _serie_q29_presenca(df):
    colunas_vinculo = {
        "CLT": _encontrar_coluna_local(df.columns, "Pessoas com vínculo empregatício (CLT)"),
        "MEI": _encontrar_coluna_local(df.columns, "Prestadores de serviços contratados como MEI"),
        "Bolsistas": _encontrar_coluna_local(df.columns, "Bolsistas"),
        "Voluntários": _encontrar_coluna_local(df.columns, "Trabalhadores voluntários (parceiros e colaboradores)"),
        "Pessoa Física": _encontrar_coluna_local(df.columns, "Prestadores de serviços contratados como Pessoas Física"),
        "Associados": _encontrar_coluna_local(df.columns, "Associados da instituição"),
    }

    sentinel = 11302769880
    dados = {}
    for nome, coluna in colunas_vinculo.items():
        if not coluna or coluna not in df.columns:
            continue

        valores = pd.to_numeric(df[coluna], errors="coerce")
        if _norm_local(nome) == _norm_local("CLT"):
            valores = valores.mask(valores == sentinel)

        dados[nome] = int((valores.fillna(0) > 0).sum())

    if not dados:
        return pd.Series(dtype="int64")

    return pd.Series(dados, dtype="int64").sort_values(ascending=True)


def _serie_q30(df):
    coluna = _encontrar_coluna_local(
        df.columns,
        "30. Qual a porcentagem aproximada de pessoas que trabalham no Ponto de Cultura e tiveram nesse trabalho sua principal fonte de renda nos últimos 24 meses?",
    )
    if not coluna:
        return pd.Series(dtype="int64")

    ordem = [
        "Nenhuma pessoa (0%)",
        "Menos de 10% das pessoas trabalhadoras do Ponto de Cultura",
        "Entre 10% e 25% das pessoas",
        "Entre 26% e 50% das pessoas",
        "Entre 51% e 75% das pessoas",
        "Mais de 75% das pessoas",
        "Não sei informar",
    ]

    serie = df[coluna].value_counts().reindex(ordem).fillna(0).astype(int)
    return serie[serie > 0]


st.title("E) Infraestrutura e Gestão")
st.write(
    "Esta página reúne os resultados de infraestrutura (Q25 e Q28), serviços ofertados à comunidade "
    "(Q26 e Q27) e gestão dos Pontos de Cultura (Q29 a Q33)."
)

base = preparar_base()
if "filtros_globais" in st.session_state:
    base = aplicar_filtros(base, st.session_state["filtros_globais"])

aba1, aba2, aba3, aba4 = st.tabs(
    [
        "Infraestrutura (Q25-Q28)",
        "Serviços ofertados à comunidade (Q26-Q27)",
        "Gestão dos Pontos de Cultura (Q29-Q32.1)",
        "Estratégias comerciais (Q33)",
    ]
)

with aba1:
    col1, col2 = st.columns([4, 6])

    with col1:
        serie_q28 = _serie_multiescolha_por_prefixo(base, "28. A sede do Ponto de Cultura é")
        if serie_q28.empty:
            st.info("Sem dados de sede na amostra filtrada.")
        else:
            serie_q28_plot = serie_q28.sort_values(ascending=False)
            serie_q28_plot_vis = _encurtar_index_serie(serie_q28_plot, limite=20)
            serie_q28_plot_vis.index = [_quebrar_linha_label(lbl, largura=10) for lbl in serie_q28_plot_vis.index]
            fig_q28 = grafico_barras_series(
                serie_q28_plot_vis,
                "Situação da sede do Ponto de Cultura (Q28)",
                cor=PALETA_CORES["principais"][2],
                horizontal=False,
                altura=560,
            )
            fig_q28 = _aplicar_percentual_base(fig_q28, serie_q28_plot_vis, len(base))
            fig_q28.update_layout(
                margin=dict(l=8, r=8, t=52, b=28),
            )
            fig_q28.update_xaxes(tickangle=0, automargin=True)
            mostrar_grafico(fig_q28, "Situação da sede do Ponto de Cultura (Q28)")

    with col2:
        serie_q25 = _serie_multiescolha_por_prefixo(
            base,
            "25. Indique se o Ponto de Cultura tem infraestrutura disponível para uso público/comunitário",
        )
        if serie_q25.empty:
            st.info("Sem dados de infraestrutura na amostra filtrada.")
        else:
            fig_q25 = grafico_barras_series(
                _encurtar_index_serie(serie_q25, limite=52),
                "Infraestruturas disponíveis para uso público/comunitário (Q25)",
                cor=PALETA_CORES["principais"][1],
                horizontal=True,
                altura=560,
            )
            mostrar_grafico(fig_q25, "Infraestruturas disponíveis para uso público/comunitário (Q25)")

with aba2:
    serie_q26 = _serie_multiescolha_por_prefixo(
        base,
        "26. Quais serviços são prestados pelo Ponto de Cultura à comunidade?",
        excluir_rotulos=["Outros", "O Ponto de Cultura não presta serviços à comunidade"],
    )

    c1, c2 = st.columns([1, 1])
    col_direta = _encontrar_coluna_local(base.columns, "27. pessoas/mês participam diretamente")
    col_indireta = _encontrar_coluna_local(base.columns, "27. pessoas/mês participam indiretamente")

    with c1:
        serie_dir = _serie_participacao_faixas(base, col_direta)
        serie_ind = _serie_participacao_faixas(base, col_indireta)

        if serie_dir.empty and serie_ind.empty:
            st.info("Sem dados de participação direta/indireta na amostra filtrada.")
        else:
            fig_esp = _grafico_espelhado_participacao(serie_dir, serie_ind)
            mostrar_grafico(fig_esp, "Participação média mensal por faixa (Direta x Indireta) (Q27)")

    with c2:
        if serie_q26.empty:
            st.info("Sem dados de serviços ofertados na amostra filtrada.")
        else:
            fig_q26 = grafico_barras_series(
                _encurtar_index_serie(serie_q26, limite=54),
                "Serviços prestados à comunidade (Q26)",
                cor=PALETA_CORES["principais"][2],
                horizontal=True,
                altura=680,
            )
            mostrar_grafico(fig_q26, "Serviços prestados à comunidade (Q26)")

with aba3:
    l1, l2, l3 = st.columns(3)

    with l1:
        col_q32 = _encontrar_coluna_local(base.columns, "31. O Ponto de Cultura elaborou alguma Análise de Viabilidade Econômica?")
        if col_q32 and col_q32 in base.columns:
            serie_q32 = _ordenar_serie_sim_nao(base[col_q32].value_counts())
            fig_q32 = grafico_donut(serie_q32, "Análise de Viabilidade Econômica elaborada (Q32)", altura=360)
            fig_q32 = _aplicar_cores_donut_sim_nao(fig_q32)
            fig_q32.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.0))
            fig_q32.update_traces(textposition="inside", textinfo="percent")
            mostrar_grafico(fig_q32, "Análise de Viabilidade Econômica elaborada (Q32)")
        else:
            st.info("Sem dados de Q32 na amostra filtrada.")

    with l2:
        col_q321 = _encontrar_coluna_local(
            base.columns,
            "32. 1. Se nunca a realizou, o Ponto de Cultura sente necessidade de elaborar uma Análise de Viabilidade Econômica?",
        )
        if col_q321 and col_q321 in base.columns:
            serie_q321 = _ordenar_serie_sim_nao(base[col_q321].dropna().value_counts())
            if not serie_q321.empty:
                fig_q321 = grafico_donut(
                    serie_q321,
                    "Necessidade de elaborar análise (Q32.1)",
                    altura=360,
                )
                fig_q321 = _aplicar_cores_donut_sim_nao(fig_q321)
                fig_q321.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.0))
                fig_q321.update_traces(textposition="inside", textinfo="percent")
                mostrar_grafico(fig_q321, "Necessidade de elaborar análise (Q32.1)")
            else:
                st.info("Sem dados de Q32.1 na amostra filtrada.")
        else:
            st.info("Sem dados de Q32.1 na amostra filtrada.")

    with l3:
        serie_q29 = _serie_q29_presenca(base)
        if serie_q29.empty:
            st.info("Sem dados de vínculos de trabalho na amostra filtrada.")
        else:
            fig_q29 = grafico_barras_series(
                serie_q29,
                "Pontos com presença de cada vínculo de trabalho (Q29)",
                cor=PALETA_CORES["principais"][0],
                horizontal=True,
                altura=360,
            )
            mostrar_grafico(fig_q29, "Pontos com presença de cada vínculo de trabalho (Q29)")

    m1, m2 = st.columns(2)

    with m1:
        serie_q30 = _serie_q30(base)
        if serie_q30.empty:
            st.info("Sem dados de dependência de renda na amostra filtrada.")
        else:
            fig_q30 = grafico_barras_series(
                _encurtar_index_serie(serie_q30, limite=48),
                "Pessoas que têm o Ponto como principal fonte de renda (Q30)",
                cor=PALETA_CORES["principais"][1],
                horizontal=True,
                altura=420,
            )
            mostrar_grafico(fig_q30, "Pessoas que têm o Ponto como principal fonte de renda (Q30)")

    with m2:
        serie_q31 = _serie_multiescolha_por_prefixo(
            base,
            "31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente?",
        )
        if serie_q31.empty:
            st.info("Sem dados de ferramentas de gestão financeira na amostra filtrada.")
        else:
            fig_q31 = grafico_barras_series(
                _encurtar_index_serie(serie_q31, limite=52),
                "Ferramentas e práticas de gestão financeira utilizadas (Q31)",
                cor=PALETA_CORES["secundarias"][3],
                horizontal=True,
                altura=420,
            )
            mostrar_grafico(fig_q31, "Ferramentas e práticas de gestão financeira utilizadas (Q31)")

with aba4:
    b1, b2 = st.columns([2, 3])

    with b1:
        col_q33 = _encontrar_coluna_local(
            base.columns,
            "33. O Ponto de Cultura possui estratégias comerciais (feiras, festivais, vendas diretas, eventos, vendas online, rodadas de negócios, redes de comercialização e/ou consumo, etc.)?",
        )
        if col_q33 and col_q33 in base.columns:
            serie_q33 = base[col_q33].value_counts()
            fig_q33 = grafico_donut(serie_q33, "Estratégias comerciais declaradas (Q33)", altura=414)
            fig_q33.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.0))
            fig_q33.update_traces(textposition="inside", textinfo="percent")
            mostrar_grafico(fig_q33, "Estratégias comerciais declaradas (Q33)")
        else:
            st.info("Sem dados de Q33 na amostra filtrada.")

    with b2:
        col_q331 = _encontrar_coluna_local(base.columns, "33. 1 Se sim, quais")
        if not col_q331:
            col_q331 = _encontrar_coluna_local(base.columns, "32. 1. Se sim, quais")

        if col_q331 and col_q331 in base.columns:
            textos = base[col_q331].dropna().astype(str)
            textos = textos[textos.str.strip() != ""]
            if textos.empty:
                st.info("Sem conteúdo textual suficiente em Q33.1 na amostra filtrada.")
            else:
                wc_q331 = gerar_wordcloud(textos, altura_plot=414, colormap="tab20")
                titulo_q331 = "Palavras mais frequentes em estratégias comerciais (Q33.1)"
                if wc_q331["tipo"] == "image":
                    _mostrar_titulo_wordcloud(titulo_q331)
                    st.image(wc_q331["img"], use_container_width=True)
                elif wc_q331["tipo"] == "plotly":
                    mostrar_grafico(wc_q331["fig"], titulo_q331)
                else:
                    st.info("Sem conteúdo textual suficiente em Q33.1 na amostra filtrada.")
        else:
            st.info("Sem dados textuais de Q33.1 na amostra filtrada.")

