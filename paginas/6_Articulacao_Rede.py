import os
import re
import sys
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components import grafico_barras_series, grafico_donut, mostrar_grafico
from config import PALETA_CORES
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


def _encurtar_index_serie(serie, limite=42):
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


def _aplicar_percentual_base(fig, serie, base):
    base_segura = max(int(base), 1)
    textos = [f"{int(v)}<br>({(int(v) / base_segura) * 100:.1f}%)" for v in serie.tolist()]
    fig.update_traces(text=textos, textposition="outside", cliponaxis=False)
    return fig


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

        rotulo = _rotulo_parenteses(coluna)
        if _norm_local(rotulo) in excluir:
            continue

        dados[rotulo] = int(para_bool(df[coluna]).sum())

    if not dados:
        return pd.Series(dtype="int64")

    serie = pd.Series(dados, dtype="int64").sort_values(ascending=True)
    return serie[serie > 0]


def _serie_esfera_participacao(df_participa, termo_esfera):
    cols = [c for c in df_participa.columns if _norm_local(c).startswith(_norm_local(termo_esfera + " ("))]
    col_nao = next((c for c in cols if "nao participa" in _norm_local(c)), None)

    total = len(df_participa)
    if total == 0:
        return pd.Series({"Participa": 0, "Não participa": 0}, dtype="int64")

    nao_participa = int(para_bool(df_participa[col_nao]).sum()) if col_nao else 0
    participa = max(total - nao_participa, 0)
    return pd.Series({"Participa": participa, "Não participa": nao_participa}, dtype="int64")


def _serie_top_palavras(textos, top_n=14):
    if textos.empty:
        return pd.Series(dtype="int64")

    stopwords = {
        "de", "da", "do", "das", "dos", "e", "em", "para", "com", "por", "na", "no", "nas", "nos",
        "a", "o", "as", "os", "um", "uma", "que", "se", "ao", "aos", "sao", "são", "sim", "nao", "não",
        "mais", "como", "entre", "ou", "etc", "rede", "cultura", "viva", "ponto", "pontos",
    }

    tokens = []
    for texto in textos.astype(str):
        limpo = _norm_local(texto)
        palavras = re.findall(r"[a-zA-Z]{4,}", limpo)
        tokens.extend([p for p in palavras if p not in stopwords])

    if not tokens:
        return pd.Series(dtype="int64")

    return pd.Series(tokens).value_counts().head(top_n).sort_values(ascending=True)


def _fig_lacuna_oferta_demanda(serie_oferta, serie_demanda, base_total):
    if serie_oferta.empty and serie_demanda.empty:
        return None

    # Normaliza e agrega por categoria para evitar desalinhamentos sutis de rótulo.
    oferta_norm = {}
    demanda_norm = {}
    label_ref = {}

    for rotulo, valor in serie_oferta.items():
        chave = _norm_local(rotulo)
        oferta_norm[chave] = oferta_norm.get(chave, 0) + int(valor)
        if chave not in label_ref or len(str(rotulo)) > len(label_ref[chave]):
            label_ref[chave] = str(rotulo)

    for rotulo, valor in serie_demanda.items():
        chave = _norm_local(rotulo)
        demanda_norm[chave] = demanda_norm.get(chave, 0) + int(valor)
        if chave not in label_ref or len(str(rotulo)) > len(label_ref[chave]):
            label_ref[chave] = str(rotulo)

    chaves = sorted(set(oferta_norm.keys()) | set(demanda_norm.keys()))
    if not chaves:
        return None

    df_gap = pd.DataFrame({"chave": chaves})
    df_gap["categoria"] = df_gap["chave"].map(label_ref)
    df_gap["oferta"] = df_gap["chave"].map(oferta_norm).fillna(0).astype(int)
    df_gap["demanda"] = df_gap["chave"].map(demanda_norm).fillna(0).astype(int)

    base = max(int(base_total), 1)
    df_gap["oferta_pct"] = (df_gap["oferta"] / base) * 100
    df_gap["demanda_pct"] = (df_gap["demanda"] / base) * 100
    df_gap["forca"] = df_gap[["oferta_pct", "demanda_pct"]].max(axis=1)
    df_gap = df_gap[df_gap["forca"] > 0]
    if df_gap.empty:
        return None

    df_gap = df_gap.sort_values("forca", ascending=False).head(12).copy()

    def _encurtar(txt, limite=42):
        txt = str(txt)
        return txt if len(txt) <= limite else f"{txt[:limite - 3]}..."

    labels_curtos = []
    usados = {}
    for categoria in df_gap["categoria"].tolist():
        curto = _encurtar(categoria)
        if curto not in usados:
            usados[curto] = 1
            labels_curtos.append(curto)
        else:
            usados[curto] += 1
            labels_curtos.append(f"{curto} ({usados[curto]})")

    df_gap["cat_plot"] = labels_curtos
    df_gap = df_gap.sort_values("forca", ascending=False)
    ordem_cat = df_gap["cat_plot"].tolist()

    fig = go.Figure()
    fig.add_bar(
        y=df_gap["cat_plot"],
        x=-df_gap["oferta_pct"],
        orientation="h",
        name="Oferta (Q35)",
        marker_color=PALETA_CORES["secundarias"][2],
        text=df_gap.apply(lambda r: f"{int(r['oferta'])} ({r['oferta_pct']:.1f}%)", axis=1),
        textposition="outside",
        cliponaxis=False,
        customdata=df_gap["categoria"],
        hovertemplate="%{customdata}<br>Oferta: %{text}<extra></extra>",
    )
    fig.add_bar(
        y=df_gap["cat_plot"],
        x=df_gap["demanda_pct"],
        orientation="h",
        name="Demanda (Q36)",
        marker_color=PALETA_CORES["principais"][1],
        text=df_gap.apply(lambda r: f"{int(r['demanda'])} ({r['demanda_pct']:.1f}%)", axis=1),
        textposition="outside",
        cliponaxis=False,
        customdata=df_gap["categoria"],
        hovertemplate="%{customdata}<br>Demanda: %{text}<extra></extra>",
    )

    max_x = max(float(df_gap["oferta_pct"].max()), float(df_gap["demanda_pct"].max()), 1.0)
    limite = max_x * 1.30
    max_tick = max(int(limite // 10) * 10 + 10, 10)
    ticks = list(range(-max_tick, max_tick + 1, 10))

    fig.update_layout(
        barmode="relative",
        height=470,
        margin=dict(l=12, r=28, t=56, b=68),
        xaxis=dict(
            title="Percentual sobre a base total",
            range=[-limite, limite],
            tickvals=ticks,
            ticktext=[f"{abs(t)}%" for t in ticks],
            zeroline=True,
            zerolinecolor="#8C8C8C",
            zerolinewidth=1.1,
            tickangle=0,
        ),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=ordem_cat,
            autorange="reversed",
        ),
        legend=dict(orientation="h", y=-0.18, x=0.0),
    )
    return fig


st.title("F) Articulação em Rede")
st.write(
    "Esta página apresenta a participação social dos Pontos de Cultura (Q34 e desdobramentos) "
    "e o compartilhamento em rede sobre ofertas e demandas na Rede Cultura Viva (Q35 e Q36)."
)

base = preparar_base()
if "filtros_globais" in st.session_state:
    base = aplicar_filtros(base, st.session_state["filtros_globais"])

aba1, aba2 = st.tabs(["Participação social (Q34)", "Compartilhamento em rede (Q35-Q36)"])

with aba1:
    col_q34 = _encontrar_coluna_local(base.columns, "34. O Ponto de Cultura é integrado a algum espaço de participação social?")
    if not col_q34:
        st.info("Sem dados de participação social na amostra filtrada.")
    else:
        serie_q34 = base[col_q34].value_counts()

        base_participa = base[base[col_q34].astype(str).map(_norm_local) == "sim"].copy()
        n_participa = len(base_participa)

        c1, c2, c3 = st.columns([2, 2, 3])

        with c1:
            fig_q34 = grafico_donut(serie_q34, "Integração em espaços de participação social (Q34)", altura=340)
            fig_q34.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.0))
            fig_q34.update_traces(textposition="inside", textinfo="percent")
            mostrar_grafico(fig_q34, "Integração em espaços de participação social (Q34)")

        with c2:
            serie_mun = _serie_esfera_participacao(base_participa, "Esfera Municipal")
            serie_est = _serie_esfera_participacao(base_participa, "Esfera Estadual")
            serie_nac = _serie_esfera_participacao(base_participa, "Esfera Nacional")

            serie_esferas = pd.Series(
                {
                    "Municipal": int(serie_mun.get("Participa", 0)),
                    "Estadual": int(serie_est.get("Participa", 0)),
                    "Nacional": int(serie_nac.get("Participa", 0)),
                },
                dtype="int64",
            )

            fig_esferas = grafico_barras_series(
                serie_esferas,
                "Participação por esfera entre os que marcaram Q34=Sim",
                cor=PALETA_CORES["principais"][1],
                horizontal=False,
                altura=340,
            )
            fig_esferas = _aplicar_percentual_base(fig_esferas, serie_esferas, n_participa)
            mostrar_grafico(fig_esferas, "Participação por esfera entre os que marcaram Q34=Sim")

        with c3:
            s_setorial = _serie_multiescolha_por_prefixo(
                base_participa,
                "Redes de articulação setorial",
                excluir_rotulos=["Outros espaços municipais de participação social:"],
            )
            if s_setorial.empty:
                st.info("Sem dados de redes de articulação setorial.")
            else:
                fig_setorial = grafico_barras_series(
                    _encurtar_index_serie(s_setorial, limite=34),
                    "Redes de articulação setorial (Q34.1)",
                    cor=PALETA_CORES["principais"][2],
                    horizontal=True,
                    altura=340,
                )
                fig_setorial = _aplicar_percentual_base(fig_setorial, s_setorial, n_participa)
                mostrar_grafico(fig_setorial, "Redes de articulação setorial (Q34.1)")

        e1, e2, e3 = st.columns(3)

        with e1:
            s_nacional = _serie_multiescolha_por_prefixo(base_participa, "Esfera Nacional")
            if s_nacional.empty:
                st.info("Sem dados da esfera nacional.")
            else:
                fig_n = grafico_barras_series(
                    _encurtar_index_serie(s_nacional, limite=20),
                    "Espaços de participação social - Esfera nacional",
                    cor=PALETA_CORES["principais"][0],
                    horizontal=True,
                    altura=440,
                )
                fig_n = _aplicar_percentual_base(fig_n, s_nacional, n_participa)
                mostrar_grafico(fig_n, "Espaços de participação social - Esfera nacional")

        with e2:
            s_estadual = _serie_multiescolha_por_prefixo(base_participa, "Esfera Estadual")
            if s_estadual.empty:
                st.info("Sem dados da esfera estadual.")
            else:
                fig_e = grafico_barras_series(
                    _encurtar_index_serie(s_estadual, limite=20),
                    "Espaços de participação social - Esfera estadual",
                    cor=PALETA_CORES["secundarias"][0],
                    horizontal=True,
                    altura=440,
                )
                fig_e = _aplicar_percentual_base(fig_e, s_estadual, n_participa)
                mostrar_grafico(fig_e, "Espaços de participação social - Esfera estadual")

        with e3:
            s_municipal = _serie_multiescolha_por_prefixo(base_participa, "Esfera Municipal")
            if s_municipal.empty:
                st.info("Sem dados da esfera municipal.")
            else:
                fig_m = grafico_barras_series(
                    _encurtar_index_serie(s_municipal, limite=20),
                    "Espaços de participação social - Esfera municipal",
                    cor=PALETA_CORES["secundarias"][2],
                    horizontal=True,
                    altura=440,
                )
                fig_m = _aplicar_percentual_base(fig_m, s_municipal, n_participa)
                mostrar_grafico(fig_m, "Espaços de participação social - Esfera municipal")

with aba2:
    s_q35 = _serie_multiescolha_por_prefixo(
        base,
        "35. O que o Ponto de Cultura gostaria de oferecer para a Rede Cultura Viva?",
    )
    s_q36 = _serie_multiescolha_por_prefixo(
        base,
        "36. Identifique até três bens/serviços que o Ponto de Cultura gostaria de obter da Rede Cultura Viva:",
    )

    fig_gap = _fig_lacuna_oferta_demanda(s_q35, s_q36, len(base))
    if fig_gap is None:
        st.info("Sem dados suficientes para o comparativo de oferta x demanda.")
    else:
        mostrar_grafico(fig_gap, "Lacuna estratégica entre oferta (Q35) e demanda (Q36)")

    col_dir_1, col_dir_2 = st.columns(2, gap="small")

    with col_dir_1:
        col_q35_outros = _encontrar_coluna_local(base.columns, "35. Quais?")
        if col_q35_outros and col_q35_outros in base.columns:
            txt35 = base[col_q35_outros].dropna().astype(str)
            txt35 = txt35[txt35.str.strip() != ""]
            s_txt35 = _serie_top_palavras(txt35, top_n=12)
            if not s_txt35.empty:
                fig_txt35 = grafico_barras_series(
                    s_txt35,
                    "Termos mais frequentes em Outros (Q35.1)",
                    cor=PALETA_CORES["secundarias"][1],
                    horizontal=True,
                    altura=340,
                )
                mostrar_grafico(fig_txt35, "Termos mais frequentes em Outros (Q35.1)")
        else:
            st.info("Sem respostas textuais em Outros (Q35.1).")

    with col_dir_2:
        col_q36_outros = _encontrar_coluna_local(base.columns, "36. Quais?")
        if col_q36_outros and col_q36_outros in base.columns:
            txt36 = base[col_q36_outros].dropna().astype(str)
            txt36 = txt36[txt36.str.strip() != ""]
            s_txt36 = _serie_top_palavras(txt36, top_n=12)
            if not s_txt36.empty:
                fig_txt36 = grafico_barras_series(
                    s_txt36,
                    "Termos mais frequentes em Outros (Q36.1)",
                    cor=PALETA_CORES["secundarias"][4],
                    horizontal=True,
                    altura=340,
                )
                mostrar_grafico(fig_txt36, "Termos mais frequentes em Outros (Q36.1)")
        else:
            st.info("Sem respostas textuais em Outros (Q36.1).")
