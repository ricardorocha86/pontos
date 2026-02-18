import os
import sys
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components import grafico_barras_series, grafico_donut, mostrar_grafico
from config import CORES_GRAFICOS, FONTE_FAMILIA, FONTE_TAMANHOS, PALETA_CORES
from texto_wordcloud import gerar_wordcloud
from utils import aplicar_filtros, para_bool, preparar_base


DICIONARIO_PRODUTOS_SERVICOS = {
    # Produtos
    "Produtos  (Artesanato)": "Artesanato",
    "Produtos  (Produtos de divulgação do ponto de cultura (camisetas, souvernirs, chaveiros etc))": "Produtos de divulgação do ponto de cultura (camisetas, souvernirs, chaveiros etc)",
    "Produtos  (Instrumentos musicais)": "Instrumentos musicais",
    "Produtos  (Produtos alimentícios beneficiados)": "Produtos alimentícios beneficiados",
    "Produtos  (Alimentos in natura)": "Alimentos in natura",
    "Produtos  (Vestuário)": "Vestuário",
    "Produtos  (Outros)": "Outros (Produtos)",
    "Produtos  (Obras artísticas (pinturas, esculturas, etc))": "Obras artísticas (pinturas, esculturas, etc)",
    "Produtos  (Livros e publicações (revistas, catálogos, jornais e etc))": "Livros e publicações (revistas, catálogos, jornais e etc)",
    # Serviços
    "Serviços (Serviços educacionais (aulas, palestras oficinas, cursos etc))": "Serviços educacionais (aulas, palestras oficinas, cursos etc)",
    "Serviços (Apresentações artísticas e eventos culturais)": "Apresentações artísticas e eventos culturais",
    "Serviços (Gestão e produção cultural)": "Gestão e produção cultural",
    "Serviços (Locação de espaços e equipamentos)": "Locação de espaços e equipamentos",
    "Serviços (Serviços audiovisuais)": "Serviços audiovisuais",
    "Serviços (Serviços de confecção têxtil (costura, figurinos, consertos etc))": "Serviços de confecção têxtil (costura, figurinos, consertos etc)",
    "Serviços (Outros)": "Outros (Serviços)",
}

LISTA_PRODUTOS = [
    "Artesanato",
    "Produtos de divulgação do ponto de cultura (camisetas, souvernirs, chaveiros etc)",
    "Instrumentos musicais",
    "Produtos alimentícios beneficiados",
    "Alimentos in natura",
    "Vestuário",
    "Outros (Produtos)",
    "Obras artísticas (pinturas, esculturas, etc)",
    "Livros e publicações (revistas, catálogos, jornais e etc)",
]

LISTA_SERVICOS = [
    "Serviços educacionais (aulas, palestras oficinas, cursos etc)",
    "Apresentações artísticas e eventos culturais",
    "Gestão e produção cultural",
    "Locação de espaços e equipamentos",
    "Serviços audiovisuais",
    "Serviços de confecção têxtil (costura, figurinos, consertos etc)",
    "Outros (Serviços)",
]


def _aplicar_padrao_donut(fig):
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        domain=dict(x=[0.08, 0.92], y=[0.03, 0.97]),
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=40, b=2),
    )
    return fig


def _mostrar_legenda_donut(labels):
    if not labels:
        return
    itens = []
    for i, label in enumerate(labels):
        cor = CORES_GRAFICOS[i % len(CORES_GRAFICOS)]
        itens.append(
            f"<div style='display:inline-flex;align-items:center;gap:8px;'>"
            f"<span style='display:inline-block;width:12px;height:12px;background:{cor};'></span>"
            f"<span>{label}</span>"
            f"</div>"
        )
    st.markdown(
        "<div style='display:flex;flex-wrap:nowrap;align-items:center;gap:18px;"
        "white-space:nowrap;overflow-x:auto;margin-top:-8px;margin-bottom:14px;'>"
        + "".join(itens)
        + "</div>",
        unsafe_allow_html=True,
    )


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


def _norm_local(txt):
    txt = "" if txt is None else str(txt)
    txt = txt.replace("\ufb01", "fi").replace("\ufb02", "fl")
    txt = unicodedata.normalize("NFKD", txt)
    txt = txt.encode("ascii", "ignore").decode("ascii")
    txt = " ".join(txt.lower().split())
    return txt


def _encontrar_coluna_local(colunas, alvo):
    alvo_n = _norm_local(alvo)
    for c in colunas:
        if _norm_local(c) == alvo_n:
            return c
    for c in colunas:
        if alvo_n in _norm_local(c):
            return c
    return None


def _encontrar_por_prefixo(colunas, prefixos_norm):
    for c in colunas:
        cn = _norm_local(c)
        if any(cn.startswith(p) for p in prefixos_norm):
            return c
    return None


def _find_col_tokens(colunas, *tokens):
    tokens_norm = [_norm_local(t) for t in tokens]
    for coluna in colunas:
        cn = _norm_local(coluna)
        if all(tok in cn for tok in tokens_norm):
            return coluna
    return None


def _serie_sim_nao(df, coluna):
    if not coluna or coluna not in df.columns:
        return pd.Series(dtype=int)
    sim = int(para_bool(df[coluna]).sum())
    nao = int(len(df) - sim)
    return pd.Series({"Sim": sim, "Não": nao})


def _encurtar_serie_labels(serie, limite=34):
    def _encurtar(txt):
        t = str(txt)
        return t if len(t) <= limite else f"{t[:limite - 3]}..."

    labels_originais = list(serie.index)
    labels_curtos = [_encurtar(lbl) for lbl in labels_originais]

    vistos = {}
    finais = []
    for lbl in labels_curtos:
        if lbl not in vistos:
            vistos[lbl] = 1
            finais.append(lbl)
        else:
            vistos[lbl] += 1
            finais.append(f"{lbl} ({vistos[lbl]})")

    serie_plot = serie.copy()
    serie_plot.index = finais
    return serie_plot, labels_originais


def _aplicar_texto_com_base(fig, serie, base):
    base_segura = max(int(base), 1)
    textos = [f"{int(v)}<br>({(int(v) / base_segura) * 100:.1f}%)" for v in serie.tolist()]
    fig.update_traces(text=textos, textposition="outside", cliponaxis=False)
    return fig


def _serie_q20_predominancia(df):
    root_q20 = _encontrar_por_prefixo(
        df.columns,
        ["20. as acoes e atividades culturais realizadas pelo ponto de cultura sao predominantemente"],
    )

    categorias = ["Gratuitas ao público", "Ambas", "Pagas", "Não se aplica"]
    contagens = {}

    # Primeiro tenta colunas booleanas por categoria (modelo da base tratada)
    for categoria in categorias:
        col = _encontrar_coluna_local(
            df.columns,
            f"20. As ações e atividades culturais realizadas pelo Ponto de Cultura são predominantemente ({categoria})",
        )
        if col and col in df.columns:
            contagens[categoria] = int(para_bool(df[col]).sum())
        else:
            contagens[categoria] = 0

    # Fallback para coluna única de resposta textual
    if sum(contagens.values()) == 0 and root_q20 and root_q20 in df.columns:
        resposta = df[root_q20].fillna("").astype(str).map(_norm_local)
        mapa = {
            "Gratuitas ao público": "gratuitas ao publico",
            "Ambas": "ambas",
            "Pagas": "pagas",
            "Não se aplica": "nao se aplica",
        }
        for categoria, token in mapa.items():
            contagens[categoria] = int((resposta == token).sum())

    return pd.Series(contagens).reindex(categorias).fillna(0).astype(int)


def _serie_multiselect_por_prefixo(df, prefixo_normalizado):
    dados = {}
    for col in df.columns:
        col_norm = _norm_local(col)
        if not col_norm.startswith(prefixo_normalizado):
            continue
        if "(" not in str(col) or ")" not in str(col):
            continue
        rotulo = str(col).split("(", 1)[1].rsplit(")", 1)[0].strip()
        dados[rotulo] = int(para_bool(df[col]).sum())
    return pd.Series(dados, dtype="int64")


def _serie_produtos(df):
    dados = {}
    rotulo_para_coluna = {}
    for texto_coluna, rotulo in DICIONARIO_PRODUTOS_SERVICOS.items():
        if rotulo not in LISTA_PRODUTOS:
            continue
        col = _encontrar_coluna_local(df.columns, texto_coluna)
        rotulo_para_coluna[rotulo] = col

    for rotulo in LISTA_PRODUTOS:
        col = rotulo_para_coluna.get(rotulo)
        dados[rotulo] = int(para_bool(df[col]).sum()) if col else 0

    return pd.Series(dados, dtype="int64")


def _serie_servicos(df):
    dados = {}
    rotulo_para_coluna = {}
    for texto_coluna, rotulo in DICIONARIO_PRODUTOS_SERVICOS.items():
        if rotulo not in LISTA_SERVICOS:
            continue
        col = _encontrar_coluna_local(df.columns, texto_coluna)
        rotulo_para_coluna[rotulo] = col

    for rotulo in LISTA_SERVICOS:
        col = rotulo_para_coluna.get(rotulo)
        dados[rotulo] = int(para_bool(df[col]).sum()) if col else 0

    return pd.Series(dados, dtype="int64")


def _serie_q22_aberta_categorizada(df):
    col_aberta = _encontrar_coluna_local(df.columns, "saiba mais mercado justo")
    if not col_aberta:
        return pd.Series(dtype=int)

    textos = df[col_aberta].fillna("").astype(str)
    textos = textos[textos.str.strip() != ""]
    if textos.empty:
        return pd.Series(dtype=int)

    regras = [
        ("Feiras, eventos e venda direta", ["feira", "bazar", "evento", "venda direta", "loja"]),
        ("Artesanato e produção sociocultural", ["artesan", "manual", "bordad", "costura"]),
        ("Agricultura e alimentação", ["agric", "agro", "horta", "alimento", "comida"]),
        ("Redes e parcerias institucionais", ["rede", "forum", "parceria", "cooperativa", "associacao"]),
        ("Apoio a produtores locais", ["produtor local", "comunidade", "local", "contratacao", "compra local"]),
        ("Sustentabilidade e reciclagem", ["reciclag", "catador", "residu", "sustent"]),
        ("Trocas e serviços não-monetários", ["troca", "permuta", "nao monet", "não monet", "volunt"]),
    ]

    contagens = {nome: 0 for nome, _ in regras}
    contagens["Outros"] = 0

    for texto in textos:
        txt = _norm_local(texto)
        encaixou = False
        for nome, palavras in regras:
            if any(p in txt for p in palavras):
                contagens[nome] += 1
                encaixou = True
                break
        if not encaixou:
            contagens["Outros"] += 1

    serie = pd.Series(contagens).sort_values(ascending=True)
    return serie[serie > 0]


def _colunas_q23(df):
    prefixo = _norm_local(
        "23. Identifique até três principais dificuldades do Ponto de Cultura para acessar mercados/comercializar produtos e/ou serviços?"
    )
    cols = []
    for c in df.columns:
        cn = _norm_local(c)
        if cn.startswith(prefixo) and "(" in str(c) and ")" in str(c):
            cols.append(c)
    return cols


def _fig_q23_por_q22(df, col_q22):
    colunas_q23 = _colunas_q23(df)
    if not col_q22 or not colunas_q23:
        return None

    resp_q22 = df[col_q22].fillna("").astype(str).map(_norm_local)
    base_sim = df[resp_q22 == "sim"]
    base_nao = df[resp_q22 == "nao"]
    n_sim = len(base_sim)
    n_nao = len(base_nao)
    if n_sim == 0 and n_nao == 0:
        return None

    registros = []
    for col in colunas_q23:
        rotulo = str(col).split("(", 1)[1].rsplit(")", 1)[0].strip()
        c_sim = int(para_bool(base_sim[col]).sum()) if n_sim > 0 else 0
        c_nao = int(para_bool(base_nao[col]).sum()) if n_nao > 0 else 0
        registros.append({"Dificuldade": rotulo, "Grupo": "Com relação (Q22=Sim)", "Contagem": c_sim, "Base": n_sim})
        registros.append({"Dificuldade": rotulo, "Grupo": "Sem relação (Q22=Não)", "Contagem": c_nao, "Base": n_nao})

    dfx = pd.DataFrame(registros)
    if dfx.empty:
        return None

    top_labels = (
        dfx.groupby("Dificuldade")["Contagem"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .index.tolist()
    )
    dfx = dfx[dfx["Dificuldade"].isin(top_labels)].copy()
    if dfx.empty:
        return None

    ordem = (
        dfx.groupby("Dificuldade")["Contagem"]
        .sum()
        .sort_values(ascending=True)
        .index.tolist()
    )

    mapa_curto = {}
    usados = {}
    for lbl in ordem:
        curto = lbl if len(lbl) <= 34 else f"{lbl[:31]}..."
        if curto not in usados:
            usados[curto] = 1
            mapa_curto[lbl] = curto
        else:
            usados[curto] += 1
            mapa_curto[lbl] = f"{curto} ({usados[curto]})"

    dfx["LabelCurta"] = dfx["Dificuldade"].map(mapa_curto)
    ordem_curta = [mapa_curto[o] for o in ordem]
    dfx["Percentual"] = dfx.apply(lambda r: (r["Contagem"] / max(int(r["Base"]), 1)) * 100, axis=1)
    dfx["Texto"] = dfx.apply(lambda r: f'{int(r["Contagem"])} ({r["Percentual"]:.1f}%)', axis=1)

    fig = px.bar(
        dfx,
        x="Contagem",
        y="LabelCurta",
        color="Grupo",
        orientation="h",
        barmode="group",
        text="Texto",
        category_orders={"LabelCurta": ordem_curta},
        color_discrete_map={
            "Com relação (Q22=Sim)": PALETA_CORES["secundarias"][1],
            "Sem relação (Q22=Não)": PALETA_CORES["principais"][0],
        },
        custom_data=["Dificuldade", "Percentual", "Base"],
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{customdata[0]}<br>Frequência: %{x}<br>Percentual no grupo: %{customdata[1]:.1f}%<br>Base: %{customdata[2]}<extra></extra>",
    )
    maxv = max(float(dfx["Contagem"].max()), 1.0)
    fig.update_xaxes(range=[0, maxv * 1.15], title="")
    fig.update_yaxes(title="")
    fig.update_layout(height=320, margin=dict(l=12, r=40, t=58, b=24))
    return fig


def _serie_q24(df):
    col_q24 = _encontrar_por_prefixo(
        df.columns,
        [
            "24. o ponto de cultura realiza ou participa de praticas culturais, espirituais ou produtivas de base tradicional ou popular"
        ],
    )
    if not col_q24:
        return pd.Series(dtype=int)

    resposta = df[col_q24].fillna("").astype(str).map(_norm_local)
    mapa = {
        "Sim": "sim",
        "Não": "nao",
        "Não sei informar": "nao sei informar",
    }
    return pd.Series({k: int((resposta == v).sum()) for k, v in mapa.items()})


st.title("D) Acesso a Mercados")
st.markdown(
    "Esta página apresenta a dinâmica de comercialização dos Pontos de Cultura e os principais "
    "desafios/estratégias de acesso a mercados com base nas questões 20 a 24."
)

df = preparar_base()
if "filtros_globais" in st.session_state:
    df = aplicar_filtros(df, st.session_state["filtros_globais"])

tab1, tab2 = st.tabs(
    [
        "Comercialização de produtos e serviços (Q20-Q21)",
        "Dificuldades e estratégias de acesso a mercados (Q22-Q24)",
    ]
)

with tab1:
    col_q21 = _encontrar_por_prefixo(
        df.columns,
        ["21. o ponto de cultura comercializou (vendeu) produtos e/ou servicos nos ultimos 24 meses?"],
    )

    serie_q20 = _serie_q20_predominancia(df)
    serie_q21 = _serie_sim_nao(df, col_q21)
    base_comercializa = df[para_bool(df[col_q21])] if col_q21 else df.iloc[0:0]
    n_comercializa = len(base_comercializa)

    serie_uso_venda = _serie_multiselect_por_prefixo(
        base_comercializa, _norm_local("21. 2. Se sim, informe para que foram usados os recursos obtidos com a venda.")
    ).sort_values(ascending=True)

    r1c1, r1c2, r1c3 = st.columns([2, 3, 5], gap="small")
    with r1c1:
        if not serie_q21.empty and int(serie_q21.sum()) > 0:
            fig_q21 = grafico_donut(serie_q21.sort_values(ascending=False), "Comercialização ativa (Q21)", altura=320)
            fig_q21 = _aplicar_padrao_donut(fig_q21)
            mostrar_grafico(fig_q21, "Comercialização ativa (Q21)")
        else:
            st.info("Sem dados de Q21 na amostra filtrada.")

    with r1c2:
        if int(serie_q20.sum()) > 0:
            fig_q20 = grafico_barras_series(
                serie_q20,
                "Modelo de acesso predominante das ações (Q20)",
                cor=PALETA_CORES["principais"][1],
                horizontal=False,
                altura=370,
            )
            mostrar_grafico(fig_q20, "Modelo de acesso predominante das ações (Q20)")
        else:
            st.info("Sem dados de Q20 na amostra filtrada.")

    with r1c3:
        if not serie_uso_venda.empty:
            serie_uso_plot, labels_uso = _encurtar_serie_labels(serie_uso_venda, limite=42)
            fig_uso = grafico_barras_series(
                serie_uso_plot,
                "Destinação dos recursos obtidos com a venda (Q21.2)",
                cor=PALETA_CORES["secundarias"][1],
                horizontal=True,
                altura=320,
                mostrar_percentual=False,
            )
            fig_uso = _aplicar_texto_com_base(fig_uso, serie_uso_plot, n_comercializa)
            fig_uso.update_traces(
                customdata=labels_uso,
                hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
            )
            max_uso = max(float(serie_uso_venda.max()), 1.0)
            fig_uso.update_xaxes(range=[0, max_uso * 1.15])
            fig_uso.update_layout(margin=dict(l=12, r=48, t=58, b=24))
            mostrar_grafico(fig_uso, "Destinação dos recursos obtidos com a venda (Q21.2)")
        else:
            st.info("Sem dados de destinação dos recursos de venda (Q21.2) na amostra filtrada.")

    serie_prod = _serie_produtos(base_comercializa).sort_values(ascending=True)
    serie_serv = _serie_servicos(base_comercializa).sort_values(ascending=True)

    c3, c4 = st.columns([1, 1], gap="small")
    with c3:
        if not serie_prod.empty:
            serie_prod_plot, labels_prod = _encurtar_serie_labels(serie_prod, limite=34)
            fig_prod = grafico_barras_series(
                serie_prod_plot,
                "Produtos comercializados (Q21.1)",
                cor=PALETA_CORES["principais"][2],
                horizontal=True,
                altura=430,
                mostrar_percentual=False,
            )
            fig_prod = _aplicar_texto_com_base(fig_prod, serie_prod_plot, n_comercializa)
            fig_prod.update_traces(
                customdata=labels_prod,
                hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
            )
            max_prod = max(float(serie_prod.max()), 1.0)
            fig_prod.update_xaxes(range=[0, max_prod * 1.15])
            fig_prod.update_layout(margin=dict(l=12, r=42, t=58, b=24))
            mostrar_grafico(fig_prod, "Produtos comercializados (Q21.1)")
        else:
            st.info("Sem dados de produtos comercializados na amostra filtrada.")

    with c4:
        if not serie_serv.empty:
            serie_serv_plot, labels_serv = _encurtar_serie_labels(serie_serv, limite=34)
            fig_serv = grafico_barras_series(
                serie_serv_plot,
                "Serviços comercializados (Q21.1)",
                cor=PALETA_CORES["secundarias"][2],
                horizontal=True,
                altura=430,
                mostrar_percentual=False,
            )
            fig_serv = _aplicar_texto_com_base(fig_serv, serie_serv_plot, n_comercializa)
            fig_serv.update_traces(
                customdata=labels_serv,
                hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
            )
            max_serv = max(float(serie_serv.max()), 1.0)
            fig_serv.update_xaxes(range=[0, max_serv * 1.15])
            fig_serv.update_layout(margin=dict(l=12, r=42, t=58, b=24))
            mostrar_grafico(fig_serv, "Serviços comercializados (Q21.1)")
        else:
            st.info("Sem dados de serviços comercializados na amostra filtrada.")

with tab2:
    col_q22 = _encontrar_por_prefixo(
        df.columns,
        ["22. o ponto de cultura possui relacao comercial com o mercado justo e solidario?"],
    )
    serie_q22 = _serie_sim_nao(df, col_q22)
    serie_q24 = _serie_q24(df)
    serie_q24_plot = serie_q24.rename({"Não sei informar": "Não sei"})

    serie_q23 = _serie_multiselect_por_prefixo(
        df,
        _norm_local("23. Identifique até três principais dificuldades do Ponto de Cultura para acessar mercados/comercializar produtos e/ou serviços?"),
    ).sort_values(ascending=True)
    col_esq, col_dir = st.columns([2, 3], gap="small")

    with col_esq:
        d1, d2 = st.columns([1, 1], gap="small")
        with d1:
            if not serie_q22.empty and int(serie_q22.sum()) > 0:
                serie_q22_plot = serie_q22.sort_values(ascending=False)
                fig_q22 = grafico_donut(serie_q22_plot, "Mercado justo e solidário (Q22)", altura=290)
                fig_q22 = _aplicar_padrao_donut(fig_q22)
                mostrar_grafico(fig_q22, "Mercado justo e solidário (Q22)")
                _mostrar_legenda_donut(list(serie_q22_plot.index))
            else:
                st.info("Sem dados de Q22 na amostra filtrada.")

        with d2:
            if not serie_q24.empty and int(serie_q24.sum()) > 0:
                serie_q24_plot_ord = serie_q24_plot.sort_values(ascending=False)
                fig_q24 = grafico_donut(
                    serie_q24_plot_ord, "Práticas de base tradicional/popular (Q24)", altura=290
                )
                fig_q24 = _aplicar_padrao_donut(fig_q24)
                mostrar_grafico(fig_q24, "Práticas de base tradicional/popular (Q24)")
                _mostrar_legenda_donut(list(serie_q24_plot_ord.index))
            else:
                st.info("Sem dados de Q24 na amostra filtrada.")

    with col_dir:
        if not serie_q23.empty:
            serie_q23_plot, labels_q23 = _encurtar_serie_labels(serie_q23, limite=42)
            fig_q23 = grafico_barras_series(
                serie_q23_plot,
                "Top 8 Principais dificuldades para acesso a mercados (Q23)",
                cor=PALETA_CORES["principais"][0],
                horizontal=True,
                altura=650,
            )
            fig_q23.update_traces(
                customdata=labels_q23,
                hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
            )
            max_q23 = max(float(serie_q23.max()), 1.0)
            fig_q23.update_xaxes(range=[0, max_q23 * 1.15])
            fig_q23.update_layout(margin=dict(l=12, r=42, t=58, b=24))
            mostrar_grafico(fig_q23, "Top 8 Principais dificuldades para acesso a mercados (Q23)")
        else:
            st.info("Sem dados de dificuldades de comercialização (Q23) na amostra filtrada.")

    with col_esq:
        col_q241 = _find_col_tokens(df.columns, "24. 1", "descreva brevemente")
        if col_q241 and col_q241 in df.columns:
            textos_q241 = df[col_q241].dropna().astype(str)
            textos_q241 = textos_q241[textos_q241.str.strip() != ""]

            if textos_q241.empty:
                st.info("Sem conteúdo textual suficiente em Q24.1 na amostra filtrada.")
            else:
                wc_q241 = gerar_wordcloud(textos_q241, altura_plot=430, colormap="tab20")
                titulo_q241 = "Palavras mais frequentes em práticas de base (Q24.1)"
                if wc_q241["tipo"] == "image":
                    _mostrar_titulo_wordcloud(titulo_q241)
                    st.image(wc_q241["img"], use_container_width=True)
                elif wc_q241["tipo"] == "plotly":
                    mostrar_grafico(wc_q241["fig"], titulo_q241)
                else:
                    st.info("Sem conteúdo textual suficiente em Q24.1 na amostra filtrada.")
        else:
            st.info("Sem dados textuais de Q24.1 na amostra filtrada.")

