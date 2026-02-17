import os
import sys
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components import mostrar_grafico
from config import FAIXAS_RECEITA, PALETA_CORES
from utils import aplicar_filtros, para_bool, preparar_base


def _norm(texto):
    texto = "" if texto is None else str(texto)
    texto = texto.replace("\ufb01", "fi").replace("\ufb02", "fl")
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().split())


def _find_col(colunas, alvo):
    alvo_n = _norm(alvo)
    for c in colunas:
        if _norm(c) == alvo_n:
            return c
    for c in colunas:
        if alvo_n in _norm(c):
            return c
    return None


def _serie_col(df, coluna):
    if not coluna or coluna not in df.columns:
        return pd.Series(dtype="object")
    s = df[coluna].copy()
    s = s.astype("object")
    return s


def _serie_bool(df, coluna, nome_sim="Sim", nome_nao="Não"):
    if not coluna or coluna not in df.columns:
        return pd.Series(dtype="object")
    b = para_bool(df[coluna])
    return b.map({True: nome_sim, False: nome_nao})


def _serie_q20(df):
    col_raiz = None
    for c in df.columns:
        n = _norm(c)
        if n.startswith("20. as acoes e atividades culturais realizadas pelo ponto de cultura sao predominantemente") and "(" not in str(c):
            col_raiz = c
            break
    if not col_raiz:
        return pd.Series(dtype="object")

    s = df[col_raiz].fillna("").astype(str).str.strip()
    s = s.replace("", pd.NA)
    return s


def _serie_q33(df):
    col = _find_col(df.columns, "possui estratégias comerciais")
    if not col:
        return pd.Series(dtype="object")
    s = df[col].fillna("").astype(str).str.strip()
    s = s.replace("", pd.NA)
    return s


def _serie_limitar_categorias(serie, max_categorias=12, label_outros="Outros"):
    serie = serie.astype("object")
    vc = serie.value_counts(dropna=True)
    if len(vc) <= max_categorias:
        return serie
    manter = set(vc.head(max_categorias).index.tolist())
    return serie.apply(lambda x: x if x in manter else label_outros)


def _ordem_referencia_variavel(nome_variavel):
    ordens = {
        "Faixa de receita": list(FAIXAS_RECEITA),
        "Faixa populacional": [
            "Até 5.000 habitantes",
            "5.001 a 10.000 habitantes",
            "10.001 a 20.000 habitantes",
            "20.001 a 50.000 habitantes",
            "50.001 a 100.000 habitantes",
            "100.001 a 500.000 habitantes",
            "Mais de 500.000 habitantes",
        ],
        "Q30 - Dependência da renda no Ponto": [
            "Nenhuma pessoa (0%)",
            "Menos de 10% das pessoas trabalhadoras do Ponto de Cultura",
            "Entre 10% e 25% das pessoas",
            "Entre 26% e 50% das pessoas",
            "Entre 51% e 75% das pessoas",
            "Mais de 75% das pessoas",
            "Não sei informar",
        ],
    }
    return ordens.get(nome_variavel)


def _reordenar_labels(labels, ordem_ref):
    if not ordem_ref:
        return list(labels)

    mapa_existentes = {_norm(lbl): lbl for lbl in labels}
    ordem_final = []

    for item in ordem_ref:
        chave = _norm(item)
        if chave in mapa_existentes:
            ordem_final.append(mapa_existentes[chave])

    for lbl in labels:
        if lbl not in ordem_final:
            ordem_final.append(lbl)

    return ordem_final


st.title("G) Cruzamentos Estratégicos")
st.write(
    "Nesta página, você escolhe duas variáveis para cruzamento bivariado e compara as distribuições "
    "em contagem absoluta e frequência relativa."
)

base = preparar_base()
if "filtros_globais" in st.session_state:
    base = aplicar_filtros(base, st.session_state["filtros_globais"])

col_q30 = _find_col(base.columns, "30. Qual a porcentagem aproximada de pessoas que trabalham no Ponto de Cultura")
col_q32 = _find_col(base.columns, "31. O Ponto de Cultura elaborou alguma Análise de Viabilidade Econômica?")
col_q321 = _find_col(base.columns, "32. 1. Se nunca a realizou")
col_q34 = _find_col(base.columns, "34. O Ponto de Cultura é integrado a algum espaço de participação social?")
col_q22 = _find_col(base.columns, "22. O Ponto de Cultura possui relação comercial com o mercado justo e solidário?")
col_q31_nenhuma = _find_col(
    base.columns,
    "31. Quais ferramentas ou práticas de gestão financeira o Ponto de Cultura utiliza atualmente? (Nenhuma das opções acima)",
)

variaveis = {
    "Região": lambda df: _serie_col(df, "regiao"),
    "UF": lambda df: _serie_col(df, "uf"),
    "Faixa populacional": lambda df: _serie_col(df, "faixa_populacional"),
    "Classificação rural/urbana": lambda df: _serie_col(df, "classificacao_rural_urbana"),
    "Tipo de Ponto": lambda df: _serie_col(df, "tipo_ponto"),
    "Registro (CNPJ/CPF)": lambda df: _serie_col(df, "registro"),
    "Faixa de receita": lambda df: _serie_col(df, "faixa_receita"),
    "Acesso a recursos federais": lambda df: _serie_bool(df, "rec_federal"),
    "Acesso a recursos estaduais": lambda df: _serie_bool(df, "rec_estadual"),
    "Acesso a recursos municipais": lambda df: _serie_bool(df, "rec_municipal"),
    "Q20 - Modelo de acesso predominante": _serie_q20,
    "Q22 - Relação com mercado justo e solidário": lambda df: _serie_col(df, col_q22),
    "Q30 - Dependência da renda no Ponto": lambda df: _serie_col(df, col_q30),
    "Q31 - Sem ferramentas de gestão": lambda df: _serie_bool(df, col_q31_nenhuma),
    "Q32 - Elaborou análise de viabilidade": lambda df: _serie_col(df, col_q32),
    "Q32.1 - Necessidade de elaborar análise": lambda df: _serie_col(df, col_q321),
    "Q33 - Estratégias comerciais": _serie_q33,
    "Q34 - Participação social": lambda df: _serie_col(df, col_q34),
}

opcoes = list(variaveis.keys())
col_cfg, col_chart = st.columns([1, 3])

with col_cfg:
    tipo_visual = st.radio(
        "Tipo de Visualização",
        ["Heatmap", "Barras agrupadas", "Barras empilhadas 100%"],
        index=2,
    )
    var_linha = st.selectbox("Variável 1 (linhas)", opcoes, index=0)
    var_coluna = st.selectbox(
        "Variável 2 (colunas)",
        opcoes,
        index=opcoes.index("Faixa de receita") if "Faixa de receita" in opcoes else 1,
    )
    limite_cat = st.selectbox("Máximo de Categorias", ["Todas", 8, 10, 12, 15, 20], index=3)

if var_linha == var_coluna:
    with col_chart:
        st.warning("Selecione duas variáveis diferentes para o cruzamento.")
    st.stop()

x = variaveis[var_linha](base)
y = variaveis[var_coluna](base)

df_cross = pd.DataFrame({"linha": x, "coluna": y}).copy()
df_cross["linha"] = df_cross["linha"].astype("object")
df_cross["coluna"] = df_cross["coluna"].astype("object")
df_cross = df_cross.dropna(subset=["linha", "coluna"])
df_cross = df_cross[(df_cross["linha"].astype(str).str.strip() != "") & (df_cross["coluna"].astype(str).str.strip() != "")]

if df_cross.empty:
    with col_chart:
        st.info("Sem dados suficientes para esse cruzamento na amostra filtrada.")
    st.stop()

if limite_cat != "Todas":
    df_cross["linha"] = _serie_limitar_categorias(df_cross["linha"], max_categorias=int(limite_cat))
    df_cross["coluna"] = _serie_limitar_categorias(df_cross["coluna"], max_categorias=int(limite_cat))

ct_abs = pd.crosstab(df_cross["linha"], df_cross["coluna"])
ordem_linha = _reordenar_labels(ct_abs.index.tolist(), _ordem_referencia_variavel(var_linha))
ordem_coluna = _reordenar_labels(ct_abs.columns.tolist(), _ordem_referencia_variavel(var_coluna))
ct_abs = ct_abs.reindex(index=ordem_linha, columns=ordem_coluna)
total_cross = int(ct_abs.values.sum())

with col_chart:
    if tipo_visual == "Heatmap":
        freq_heat = (ct_abs / max(total_cross, 1)) * 100
        anotacoes = ct_abs.copy().astype(str)
        for i in ct_abs.index:
            for j in ct_abs.columns:
                n = int(ct_abs.loc[i, j])
                f = float(freq_heat.loc[i, j])
                anotacoes.loc[i, j] = f"{n}<br>({f:.1f}%)"

        fig = go.Figure(
            data=go.Heatmap(
                z=ct_abs.values,
                x=ct_abs.columns.tolist(),
                y=ct_abs.index.tolist(),
                text=anotacoes.values,
                texttemplate="%{text}",
                coloraxis="coloraxis",
                hovertemplate=(
                    f"{var_linha}: %{{y}}<br>"
                    f"{var_coluna}: %{{x}}<br>"
                    "Contagem: %{z}<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            height=595,
            coloraxis=dict(colorscale=["#EBF5FF", PALETA_CORES["principais"][1]], colorbar_title="Contagem"),
            xaxis_title=var_coluna,
            yaxis_title=var_linha,
        )
        mostrar_grafico(fig, f"{var_linha} x {var_coluna}")

    elif tipo_visual == "Barras agrupadas":
        plot_df = ct_abs.reset_index().melt(id_vars="linha", var_name="coluna", value_name="contagem")
        plot_df["frequencia"] = (plot_df["contagem"] / max(total_cross, 1)) * 100
        plot_df["texto"] = plot_df.apply(lambda r: f"{int(r['contagem'])}<br>({r['frequencia']:.1f}%)", axis=1)

        fig = px.bar(
            plot_df,
            x="linha",
            y="contagem",
            color="coluna",
            barmode="group",
            text="texto",
            color_discrete_sequence=PALETA_CORES["principais"] + PALETA_CORES["secundarias"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=595,
            xaxis_title=var_linha,
            yaxis_title="Contagem",
            legend=dict(orientation="v", y=1.0, yanchor="top", x=1.02, xanchor="left"),
            margin=dict(r=190),
        )
        mostrar_grafico(fig, f"{var_linha} x {var_coluna}")

    else:
        pct_linha = ct_abs.div(ct_abs.sum(axis=1).replace(0, pd.NA), axis=0) * 100
        palette = PALETA_CORES["principais"] + PALETA_CORES["secundarias"]
        fig = go.Figure()

        for idx, col_name in enumerate(ct_abs.columns):
            y_pct = pct_linha[col_name].fillna(0)
            y_abs = ct_abs[col_name].fillna(0)
            y_freq = (y_abs / max(total_cross, 1)) * 100
            textos = [
                f"{int(n)}<br>({f:.1f}%)" if p >= 4 else ""
                for n, f, p in zip(y_abs.tolist(), y_freq.tolist(), y_pct.tolist())
            ]

            nome_legenda = str(col_name).strip() if str(col_name).strip() else "Sem resposta"
            fig.add_bar(
                x=ct_abs.index.tolist(),
                y=y_pct.tolist(),
                name=nome_legenda,
                text=textos,
                textposition="inside",
                marker_color=palette[idx % len(palette)],
                cliponaxis=False,
            )

        fig.update_layout(
            height=595,
            xaxis_title=var_linha,
            yaxis_title="% por linha",
            yaxis_range=[0, 100],
            barmode="stack",
            legend=dict(orientation="v", y=1.0, yanchor="top", x=1.02, xanchor="left"),
            margin=dict(r=190),
        )
        mostrar_grafico(fig, f"{var_linha} x {var_coluna}")
