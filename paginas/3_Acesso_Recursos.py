import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config import FAIXAS_RECEITA, FONTE_FAMILIA, FONTE_TAMANHOS, PALETA_CORES
from components import grafico_barras_series, grafico_donut, mostrar_grafico
from utils import aplicar_filtros, encontrar_coluna, normalizar_texto, para_bool, preparar_base


def _aplicar_padrao_donut_pagina_a(fig):
  fig.update_traces(textposition="inside", textinfo="percent")
  fig.update_layout(
    showlegend=True,
    margin=dict(l=4, r=4, t=46, b=4),
    legend=dict(orientation="h", y=-0.16, x=0.0),
  )
  return fig


def _encurtar_serie_para_barra(serie, limite=38):
  def _encurtar(txt):
    t = str(txt)
    return t if len(t) <= limite else f"{t[:limite - 3]}..."

  labels_originais = list(serie.index)
  labels_encurtados = [_encurtar(lbl) for lbl in labels_originais]

  vistos = {}
  labels_finais = []
  for lbl in labels_encurtados:
    if lbl not in vistos:
      vistos[lbl] = 1
      labels_finais.append(lbl)
    else:
      vistos[lbl] += 1
      labels_finais.append(f"{lbl} ({vistos[lbl]})")

  serie_plot = serie.copy()
  serie_plot.index = labels_finais
  return serie_plot, labels_originais


def _serie_sim_nao(df, coluna):
  if not coluna or coluna not in df.columns:
    return pd.Series(dtype=int)
  resposta_sim = int(para_bool(df[coluna]).sum())
  resposta_nao = int(len(df) - resposta_sim)
  return pd.Series({"Sim": resposta_sim, "Não": resposta_nao})


def _contar_colunas_booleanas(df, mapeamento):
  contagens = {}
  for rotulo, texto_coluna in mapeamento.items():
    coluna = encontrar_coluna(df.columns, texto_coluna)
    if coluna and coluna in df.columns:
      contagens[rotulo] = int(para_bool(df[coluna]).sum())
  return pd.Series(contagens, dtype="int64")


def _q16_dificuldades(df):
  prefixo = normalizar_texto("16. Identifique até três principais dificuldades")
  colunas = [c for c in df.columns if normalizar_texto(c).startswith(prefixo)]
  contagens = {}

  for coluna in colunas:
    if "(" not in coluna or ")" not in coluna:
      continue
    rotulo = coluna.split("(", 1)[1].rsplit(")", 1)[0].strip()
    contagens[rotulo] = int(para_bool(df[coluna]).sum())

  return pd.Series(contagens, dtype="int64")


def _q18_motivos_nao_credito(df):
  coluna_motivo = encontrar_coluna(df.columns, "18. 2. Se não, sinalize o motivo")
  if not coluna_motivo:
    return pd.Series(dtype=int)

  categorias_referencia = [
    "Desconhecimento de linhas de crédito para ações culturais",
    "Não tem interesse em obter empréstimos",
    "Receio de endividamento",
    "Não tem necessidade de obter empréstimos",
    "Juros muito altos",
    "Solicitação de crédito negada",
  ]

  contagem = df[coluna_motivo].value_counts().reindex(categorias_referencia).fillna(0).astype(int)
  return contagem[contagem > 0]


def _q19_receita_anual(df):
  mapeamento_q19 = {
    "Sem receita": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (O Ponto de Cultura não teve receita em 2024)",
    "Menor que 15.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (Menor que 15.000)",
    "15.001 a 50.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (15.001 a 50.000)",
    "50.001 a 100.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (50.001 a 100.000)",
    "100.001 a 150.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (100.001 a 150.000)",
    "150.001 a 200.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (150.001 a 200.000)",
    "200.001 a 250.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (200.001 a 250.000)",
    "250.001 a 300.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (250.001 a 300.000)",
    "300.001 a 350.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (300.001 a 350.000)",
    "350.001 a 400.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (350.001 a 400.000)",
    "Maior que 400.000": "19. Qual foi a receita anual do Ponto de Cultura em 2024? (Maior que 400.000)",
  }

  contagens = {}
  for faixa, texto_coluna in mapeamento_q19.items():
    coluna = encontrar_coluna(df.columns, texto_coluna)
    if coluna and coluna in df.columns:
      contagens[faixa] = int(para_bool(df[coluna]).sum())
    else:
      contagens[faixa] = 0

  ordem = ["Sem receita"] + [f for f in FAIXAS_RECEITA if normalizar_texto(f) != normalizar_texto("Não teve receita")]
  return pd.Series(contagens, dtype="int64").reindex(ordem).fillna(0).astype(int)


st.title("C) Acesso a Recursos")
st.markdown(
  "Esta página organiza os resultados de sustentabilidade econômica em dois blocos: "
  "economia do Ponto de Cultura (Q13 a Q15) e dificuldades/estratégias financeiras (Q16 a Q19)."
)

df = preparar_base()
if "filtros_globais" in st.session_state:
  df = aplicar_filtros(df, st.session_state["filtros_globais"])

tab_economia, tab_dificuldades = st.tabs(
  [
    "Economia do Ponto de Cultura",
    "Dificuldades e estratégias financeiras dos Pontos de Cultura",
  ]
)

with tab_economia:
  col_q13 = encontrar_coluna(
    df.columns,
    "13. O Projeto do Ponto de Cultura representa a principal fonte de renda da entidade/coletivo/pessoa física?",
  )
  col_q14 = encontrar_coluna(
    df.columns, "14. O Ponto de Cultura acessou recursos públicos nos últimos 24 meses?"
  )
  col_q15 = encontrar_coluna(
    df.columns, "15. O Ponto de Cultura acessou recursos financeiros privados nos últimos 24 meses?"
  )

  esfera_map = {
    "Recursos municipais": "14. 1. Se sim, quais? (Recursos Municipais)",
    "Recursos estaduais": "14. 1. Se sim, quais? (Recursos Estaduais)",
    "Recursos federais": "14. 1. Se sim, quais? (Recursos Federais)",
  }
  serie_esferas = _contar_colunas_booleanas(df, esfera_map).sort_values(ascending=True)

  detalhe_publico_map = {
    "Editais MinC": "Recursos federais (Editais Ministério da Cultura)",
    "Outros ministérios": "Recursos federais (Editais de outros ministério)",
    "Emendas federais": "Recursos federais (Emendas parlamentares federais)",
    "Lei Rouanet": "Recursos federais (Lei Rouanet)",
    "PNAB estadual": "Recursos federais (Editais estaduais da PNAB",
    "PNAB municipal": "Recursos federais (Editais municipais da PNAB",
    "LPG estadual": "Recursos federais (Editais estaduais da LPG",
    "LPG municipal": "Recursos federais (Editais municipais da LPG",
    "Editais estaduais": "Recursos Estaduais (Editais estaduais (exceto PNAB e LPG))",
    "Lei incentivo estadual": "Recursos Estaduais (Lei Estadual de Incentivo à Cultura)",
    "Emendas estaduais": "Recursos Estaduais ( Emendas parlamentares estaduais)",
    "Termo fomento estadual": "Recursos Estaduais (Termo de Fomento)",
    "Fundo municipal": "Recursos Municipais (Editais do Fundo Municipal de Cultura (exceto PNAB e LPG))",
    "Lei incentivo municipal": "Recursos Municipais (Lei Municipal de Incentivo à Cultura)",
    "Emendas municipais": "Recursos Municipais (Emendas parlamentares municipais)",
    "Termo fomento municipal": "Recursos Municipais (Termo de Fomento)",
  }
  serie_publico_detalhe = _contar_colunas_booleanas(df, detalhe_publico_map).sort_values(ascending=True)

  recursos_privados_map = {
    "Empresas privadas": "15. 1. Se sim, quais recursos financeiros privados? (Recursos de Empresas Privadas)",
    "OSC brasileiras": "15. 1. Se sim, quais recursos financeiros privados? (Organizações da Sociedade Civil - OSC brasileiras)",
    "Editais internacionais": "15. 1. Se sim, quais recursos financeiros privados? (Editais de Organizações Internacionais)",
    "Organismo internacional": "15. 1. Se sim, quais recursos financeiros privados? (Organismo de fomento internacional",
    "Bancos de fomento": "15. 1. Se sim, quais recursos financeiros privados? (Bancos de fomento nacional",
    "Sistema S": "15. 1. Se sim, quais recursos financeiros privados? (Sistema S",
    "Rifas ou bingos": "15. 1. Se sim, quais recursos financeiros privados? (Rifas ou bingos)",
    "Doações (vaquinha)": "15. 1. Se sim, quais recursos financeiros privados? (Doações via campanhas de pessoas físicas (vaquinha))",
    "Festas arrecadação": "15. 1. Se sim, quais recursos financeiros privados? (Festas para arrecadação de recursos)",
    "Campanhas em plataforma": "15. 1. Se sim, quais recursos financeiros privados? (Campanhas em plataforma virtuais:)",
  }
  serie_privados = _contar_colunas_booleanas(df, recursos_privados_map).sort_values(ascending=True)

  modalidade_map = {
    "Patrocínio": "15. Qual tipo de financiamento? (Patrocínio)",
    "Financiamento direto": "15. Qual tipo de financiamento? (Financiamento direto)",
    "Doação": "15. Qual tipo de financiamento? (Doação)",
  }
  serie_modalidade = _contar_colunas_booleanas(df, modalidade_map).sort_values(ascending=True)

  serie_q13 = _serie_sim_nao(df, col_q13).sort_values(ascending=False)
  serie_q13.index = serie_q13.index.map(
    {
      "Sim": "Sim - é a principal fonte de renda",
      "Não": "Não - não é a principal fonte de renda",
    }
  )
  serie_acesso = pd.Series(
    {
      "Acesso a recursos públicos": int(para_bool(df[col_q14]).sum()) if col_q14 else 0,
      "Acesso a recursos privados": int(para_bool(df[col_q15]).sum()) if col_q15 else 0,
    }
  ).sort_values(ascending=False)

  d1, d2, d3, d4 = st.columns(4)
  with d1:
    if not serie_q13.empty and int(serie_q13.sum()) > 0:
      fig_q13 = grafico_donut(serie_q13, "Principal fonte de renda (Q13)", altura=300)
      fig_q13 = _aplicar_padrao_donut_pagina_a(fig_q13)
      mostrar_grafico(fig_q13, "Principal fonte de renda (Q13)")
    else:
      st.info("Sem dados de Q13 na amostra filtrada.")

  with d2:
    if int(serie_acesso.sum()) > 0:
      serie_acesso_bar = serie_acesso.sort_values(ascending=False).copy()
      serie_acesso_bar.index = serie_acesso_bar.index.map(
        {
          "Acesso a recursos públicos": "Recursos públicos",
          "Acesso a recursos privados": "Recursos privados",
        }
      )
      fig_acesso = grafico_barras_series(
        serie_acesso_bar,
        "Acesso a recursos (Q14-Q15)",
        cor=PALETA_CORES["principais"][0],
        horizontal=False,
        altura=360,
      )
      mostrar_grafico(fig_acesso, "Acesso a recursos (Q14-Q15)")
    else:
      st.info("Sem dados de Q14/Q15 na amostra filtrada.")

  with d3:
    if not serie_esferas.empty and int(serie_esferas.sum()) > 0:
      fig_esferas = grafico_barras_series(
        serie_esferas.sort_values(ascending=False),
        "Esferas de recursos públicos (Q14.1)",
        cor=PALETA_CORES["secundarias"][1],
        horizontal=False,
        altura=360,
      )
      mostrar_grafico(fig_esferas, "Esferas de recursos públicos (Q14.1)")
    else:
      st.info("Sem dados de desdobramento da Q14 na amostra filtrada.")

  with d4:
    if not serie_modalidade.empty and int(serie_modalidade.sum()) > 0:
      fig_modalidade = grafico_barras_series(
        serie_modalidade.sort_values(ascending=False),
        "Tipo de financiamento (Q15)",
        cor=PALETA_CORES["principais"][1],
        horizontal=False,
        altura=360,
      )
      mostrar_grafico(fig_modalidade, "Tipo de financiamento (Q15)")
    else:
      st.info("Sem dados de modalidade de financiamento na amostra filtrada.")

  c5, c6 = st.columns(2)
  with c5:
    if not serie_privados.empty and int(serie_privados.sum()) > 0:
      fig_privados = grafico_barras_series(
        serie_privados,
        "Fontes de recursos financeiros privados (Q15.1)",
        cor=PALETA_CORES["principais"][2],
        horizontal=True,
        altura=430,
      )
      mostrar_grafico(fig_privados, "Fontes de recursos financeiros privados (Q15.1)")
    else:
      st.info("Sem dados de fontes privadas na amostra filtrada.")

  with c6:
    if not serie_publico_detalhe.empty and int(serie_publico_detalhe.sum()) > 0:
      fig_det_pub = grafico_barras_series(
        serie_publico_detalhe.tail(10),
        "Instrumentos públicos mais acessados - Top 10 (Q14.1)",
        cor=PALETA_CORES["secundarias"][2],
        horizontal=True,
        altura=430,
      )
      mostrar_grafico(fig_det_pub, "Instrumentos públicos mais acessados - Top 10 (Q14.1)")
    else:
      st.info("Sem dados detalhados de instrumentos públicos na amostra filtrada.")

with tab_dificuldades:
  col_q17 = encontrar_coluna(
    df.columns,
    "17. O Ponto de Cultura mobilizou recursos não-monetários de colaboração e solidariedade nos últimos 24 meses?",
  )
  col_q18 = encontrar_coluna(
    df.columns, "18. O Ponto de Cultura acessou linha de crédito para a realização de suas ações?"
  )

  serie_q16 = _q16_dificuldades(df).sort_values(ascending=True)
  serie_q17 = _serie_sim_nao(df, col_q17).sort_values(ascending=True)
  serie_q18 = _serie_sim_nao(df, col_q18).sort_values(ascending=True)
  serie_q18_motivos = _q18_motivos_nao_credito(df).sort_values(ascending=True)
  serie_q19 = _q19_receita_anual(df)

  recursos_nao_monetarios_map = {
    "Ajuda mútua": "17. 1. Se sim, quais? (Ações de ajuda mútua (mutirões, ações comunitárias, iniciativas beneﬁcentes, etc))",
    "Doações não-monetárias": "17. 1. Se sim, quais? (Doações não-monetárias (equipamentos, mobiliários, espaços, vestuário, etc.))",
    "Trabalho voluntário": "17. 1. Se sim, quais? (Trabalho voluntário)",
    "Trocas diretas": "17. 1. Se sim, quais? (Trocas diretas de produtos e serviços)",
    "Intercâmbio": "17. 1. Se sim, quais? (Intercâmbio de espetáculos ou apresentações)",
    "Produção para autoconsumo": "17. 1. Se sim, quais? (Produção própria para o autoconsumo)",
  }
  serie_q17_detalhe = _contar_colunas_booleanas(df, recursos_nao_monetarios_map).sort_values(ascending=True)

  r1c1, r1c2, r1c3, r1c4 = st.columns([2, 2, 4, 5], gap="small")
  with r1c1:
    if not serie_q17.empty and int(serie_q17.sum()) > 0:
      fig_q17 = grafico_donut(
        serie_q17.sort_values(ascending=False),
        "Mobilização não-monetária (Q17)",
        altura=300,
      )
      fig_q17 = _aplicar_padrao_donut_pagina_a(fig_q17)
      mostrar_grafico(fig_q17, "Mobilização não-monetária (Q17)")
    else:
      st.info("Sem dados de Q17 na amostra filtrada.")

  with r1c2:
    if not serie_q18.empty and int(serie_q18.sum()) > 0:
      fig_q18 = grafico_donut(
        serie_q18.sort_values(ascending=False),
        "Acesso a crédito (Q18)",
        altura=300,
      )
      fig_q18 = _aplicar_padrao_donut_pagina_a(fig_q18)
      mostrar_grafico(fig_q18, "Acesso a crédito (Q18)")
    else:
      st.info("Sem dados de Q18 na amostra filtrada.")

  with r1c3:
    if not serie_q17_detalhe.empty and int(serie_q17_detalhe.sum()) > 0:
      serie_q17_plot, labels_q17 = _encurtar_serie_para_barra(serie_q17_detalhe, limite=20)
      fig_q17_detalhe = grafico_barras_series(
        serie_q17_plot,
        "Tipos de recursos não-monetários mobilizados (Q17.1)",
        cor=PALETA_CORES["secundarias"][0],
        horizontal=True,
        altura=360,
      )
      fig_q17_detalhe.update_traces(
        customdata=labels_q17,
        hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
      )
      max_q17 = max(float(serie_q17_detalhe.max()), 1.0)
      fig_q17_detalhe.update_xaxes(range=[0, max_q17 * 1.15])
      fig_q17_detalhe.update_layout(margin=dict(l=10, r=40, t=58, b=24))
      fig_q17_detalhe.update_yaxes(tickfont=dict(size=10), automargin=True)
      mostrar_grafico(fig_q17_detalhe, "Tipos de recursos não-monetários mobilizados (Q17.1)")
    else:
      st.info("Sem dados de desdobramento da Q17 na amostra filtrada.")

  with r1c4:
    if int(serie_q19.sum()) > 0:
      df_q19 = pd.DataFrame({"faixa": serie_q19.index, "valor": serie_q19.values})
      total_q19 = max(int(df_q19["valor"].sum()), 1)
      df_q19["texto"] = df_q19["valor"].apply(lambda v: f"{int(v)}<br>({(v / total_q19) * 100:.1f}%)")

      fig_q19 = px.bar(
        df_q19,
        x="faixa",
        y="valor",
        color_discrete_sequence=[PALETA_CORES["principais"][1]],
      )
      fig_q19.update_traces(
        text=df_q19["texto"],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS["dado"]),
      )
      fig_q19.update_layout(
        height=360,
        margin=dict(l=10, r=20, t=60, b=120),
        font=dict(family=FONTE_FAMILIA, size=FONTE_TAMANHOS["geral"]),
      )
      fig_q19.update_xaxes(title="", tickangle=-40)
      fig_q19.update_yaxes(title="")
      mostrar_grafico(fig_q19, "Receita anual dos Pontos de Cultura em 2024 (Q19)")
    else:
      st.info("Sem dados da Q19 na amostra filtrada.")

  r2c1, r2c2 = st.columns([1, 1], gap="small")
  with r2c1:
    if not serie_q16.empty and int(serie_q16.sum()) > 0:
      serie_q16_plot, labels_q16 = _encurtar_serie_para_barra(serie_q16, limite=30)
      fig_q16 = grafico_barras_series(
        serie_q16_plot,
        "Principais dificuldades para acessar recursos públicos (Q16)",
        cor=PALETA_CORES["principais"][0],
        horizontal=True,
        altura=430,
      )
      fig_q16.update_traces(
        customdata=labels_q16,
        hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
      )
      max_q16 = max(float(serie_q16.max()), 1.0)
      fig_q16.update_xaxes(range=[0, max_q16 * 1.15])
      fig_q16.update_layout(margin=dict(l=12, r=48, t=58, b=24))
      fig_q16.update_yaxes(tickfont=dict(size=10), automargin=True)
      mostrar_grafico(fig_q16, "Principais dificuldades para acessar recursos públicos (Q16)")
    else:
      st.info("Sem dados da Q16 na amostra filtrada.")

  with r2c2:
    if not serie_q18_motivos.empty and int(serie_q18_motivos.sum()) > 0:
      serie_q18_plot, labels_q18 = _encurtar_serie_para_barra(serie_q18_motivos, limite=30)
      fig_q18_motivos = grafico_barras_series(
        serie_q18_plot,
        "Motivos para não acessar crédito (Q18.2)",
        cor=PALETA_CORES["principais"][0],
        horizontal=True,
        altura=430,
      )
      fig_q18_motivos.update_traces(
        customdata=labels_q18,
        hovertemplate="%{customdata}<br>Frequência: %{x}<extra></extra>",
      )
      max_q18 = max(float(serie_q18_motivos.max()), 1.0)
      fig_q18_motivos.update_xaxes(range=[0, max_q18 * 1.15])
      fig_q18_motivos.update_layout(margin=dict(l=12, r=48, t=58, b=24))
      fig_q18_motivos.update_yaxes(tickfont=dict(size=10), automargin=True)
      mostrar_grafico(fig_q18_motivos, "Motivos para não acessar crédito (Q18.2)")
    else:
      st.info("Sem dados de motivos da Q18.2 na amostra filtrada.")




