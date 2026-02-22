import base64
import io
import os
from datetime import datetime

import streamlit as st
from PIL import Image, ImageDraw
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from config import SIGLA_PARA_ESTADO_NOME


_RELATORIO_CTX_KEY = "_relatorio_pagina_ctx"
_RELATORIO_ABA_KEY = "_relatorio_aba_atual"

_MAPA_RECURSOS = {
    "rec_federal": "Recursos Federais",
    "rec_minc": "Editais do Ministério da Cultura",
    "rec_estadual": "Recursos Estaduais",
    "rec_municipal": "Recursos Municipais",
    "pnab_estadual": "PNAB Estadual",
    "pnab_municipal": "PNAB Municipal",
    "tcc_est_ponto": "TCC Estadual (Ponto)",
    "tcc_est_pontao": "TCC Estadual (Pontão)",
    "tcc_mun_ponto": "TCC Municipal (Ponto)",
    "tcc_mun_pontao": "TCC Municipal (Pontão)",
}


def _ctx():
    return st.session_state.get(_RELATORIO_CTX_KEY)


def _encode_data_uri(raw_bytes, mime_type):
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _asset_data_uri(candidatos):
    raiz = os.path.dirname(__file__)
    for rel in candidatos:
        caminho = os.path.join(raiz, rel)
        if not os.path.exists(caminho):
            continue
        try:
            with open(caminho, "rb") as f:
                payload = f.read()
            ext = os.path.splitext(caminho)[1].lower()
            mime = {
                ".svg": "image/svg+xml",
                ".webp": "image/webp",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
            }.get(ext, "application/octet-stream")
            return _encode_data_uri(payload, mime)
        except Exception:
            continue
    return ""


def iniciar_contexto_relatorio(titulo_pagina):
    st.session_state[_RELATORIO_CTX_KEY] = {
        "titulo_pagina": str(titulo_pagina or "Página"),
        "graficos": [],
    }
    st.session_state[_RELATORIO_ABA_KEY] = "Visão geral"


def definir_aba_relatorio(nome_aba):
    if nome_aba:
        st.session_state[_RELATORIO_ABA_KEY] = str(nome_aba).strip()


def registrar_grafico_plotly(fig, titulo):
    ctx = _ctx()
    if ctx is None or fig is None:
        return

    try:
        fig_export = go.Figure(fig)
        largura = int(fig_export.layout.width or 0) or 0
        altura = int(fig_export.layout.height or 0) or 0
        margem = fig_export.layout.margin or {}
        y_labels = []
        for tr in fig_export.data:
            ys = getattr(tr, "y", None)
            if ys is None:
                continue
            for y in ys:
                y_labels.append(str(y))
        max_label = max((len(lbl) for lbl in y_labels), default=0)
        extra_l = min(max(max_label - 20, 0) * 3, 70)
        margem_l = max(int(getattr(margem, "l", 0) or 0), 10) + extra_l
        margem_r = max(int(getattr(margem, "r", 0) or 0), 28)
        margem_t = max(int(getattr(margem, "t", 0) or 0), 56)
        margem_b = max(int(getattr(margem, "b", 0) or 0), 36)
        layout_patch = dict(margin=dict(l=margem_l, r=margem_r, t=margem_t, b=margem_b))
        if largura > 0 and altura > 0:
            layout_patch.update(dict(autosize=False, width=largura, height=altura))
        fig_export.update_layout(**layout_patch)
        fig_export.for_each_xaxis(lambda ax: ax.update(automargin=True))
        fig_export.for_each_yaxis(lambda ax: ax.update(automargin=True))
        img_bytes = fig_export.to_image(format="png", scale=2)
        data_uri = _encode_data_uri(img_bytes, "image/png")
    except Exception:
        # Fallback estático: evita gráficos reativos no relatório final.
        imagem = Image.new("RGB", (1400, 780), color=(245, 247, 251))
        draw = ImageDraw.Draw(imagem)
        mensagem = "Nao foi possivel exportar o grafico em PNG nesta execucao."
        draw.text((48, 48), str(titulo or "Grafico"), fill=(18, 52, 102))
        draw.text((48, 96), mensagem, fill=(102, 112, 133))
        buf = io.BytesIO()
        imagem.save(buf, format="PNG")
        data_uri = _encode_data_uri(buf.getvalue(), "image/png")

    aba = st.session_state.get(_RELATORIO_ABA_KEY, "Visão geral")
    ctx["graficos"].append(
        {
            "tipo": "imagem",
            "titulo": str(titulo or ""),
            "aba": str(aba or "Visão geral"),
            "data_uri": data_uri,
        }
    )


def registrar_figura_matplotlib(fig, titulo):
    ctx = _ctx()
    if ctx is None or fig is None:
        return

    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
        data_uri = _encode_data_uri(buf.getvalue(), "image/png")
    except Exception:
        return

    aba = st.session_state.get(_RELATORIO_ABA_KEY, "Visão geral")
    ctx["graficos"].append(
        {
            "tipo": "imagem",
            "titulo": str(titulo or ""),
            "aba": str(aba or "Visão geral"),
            "data_uri": data_uri,
        }
    )


def registrar_imagem_array(img_array, titulo):
    ctx = _ctx()
    if ctx is None or img_array is None:
        return

    try:
        imagem = Image.fromarray(img_array)
        buf = io.BytesIO()
        imagem.save(buf, format="PNG")
        data_uri = _encode_data_uri(buf.getvalue(), "image/png")
    except Exception:
        return

    aba = st.session_state.get(_RELATORIO_ABA_KEY, "Visão geral")
    ctx["graficos"].append(
        {
            "tipo": "imagem",
            "titulo": str(titulo or ""),
            "aba": str(aba or "Visão geral"),
            "data_uri": data_uri,
        }
    )


def _rotulo_parenteses(valor):
    txt = str(valor)
    if "(" in txt and ")" in txt:
        return txt.split("(", 1)[1].rsplit(")", 1)[0].strip()
    return txt


def _limpar_lista(valores):
    if valores is None:
        return []
    if isinstance(valores, (list, tuple, set)):
        base = list(valores)
    else:
        base = [valores]
    saida = []
    for item in base:
        txt = str(item).strip()
        if txt:
            saida.append(txt)
    return saida


def _resumo_filtros(filtros):
    if not isinstance(filtros, dict):
        return []

    resumo = []

    def add(label, valores):
        lista = _limpar_lista(valores)
        if lista:
            resumo.append({"label": label, "values": lista})

    add("Região", filtros.get("regiao"))
    add("Estado", [SIGLA_PARA_ESTADO_NOME.get(v, v) for v in _limpar_lista(filtros.get("estado"))])
    add("Município", filtros.get("municipio"))
    add("Faixa populacional", filtros.get("faixa_populacional"))
    add("Tipo de estabelecimento", filtros.get("tipo_ponto"))
    add("Cadastro jurídico", filtros.get("registro"))
    add(
        "Ação estruturante",
        [_rotulo_parenteses(v) for v in _limpar_lista(filtros.get("acoes_estruturantes"))],
    )
    add("Linguagem artística", filtros.get("linguagem_artistica"))
    add("Faixa de receita anual", filtros.get("faixa_receita"))
    add(
        "Acesso a recursos",
        [_MAPA_RECURSOS.get(v, v) for v in _limpar_lista(filtros.get("acessos_recursos_or"))],
    )

    return resumo


def gerar_payload_relatorio(filtros):
    ctx = _ctx() or {"titulo_pagina": "Página", "graficos": []}

    return {
        "titulo_pagina": ctx.get("titulo_pagina", "Página"),
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "filtros": _resumo_filtros(filtros),
        "graficos": list(ctx.get("graficos", [])),
        "fonte_rodape": (
            "Fonte: Diagnóstico Econômico da Cultura Viva. Projeto de pesquisa vinculado à Política Nacional de Cultura Viva."
        ),
        "texto_projeto": (
            "Este relatório apresenta um recorte analítico do Diagnóstico Econômico da Cultura Viva, "
            "gerado a partir da página selecionada, da aba ativa e dos filtros aplicados no Dashboard."
        ),
        "texto_parceria": (
            "O projeto é desenvolvido pelo Consórcio Universitário Cultura Viva (UFBA, UFF e UFPR), "
            "em parceria com o Ministério da Cultura, para qualificar evidências sobre sustentabilidade econômica, "
            "infraestrutura, gestão, articulação em rede e acesso a recursos de Pontos e Pontões de Cultura."
        ),
        "logo_data_uri": _asset_data_uri(
            [
                os.path.join("assets", "cor-completa.png"),
            ]
        ),
        "cover_data_uri": _asset_data_uri(
            [
                os.path.join("assets", "cover.webp"),
                os.path.join("pontos_repo_sync_2", "assets", "cover.webp"),
            ]
        ),
    }


def montar_html_relatorio(payload, aba_preferida=None):
    payload = payload or {}
    titulo_pagina = str(payload.get("titulo_pagina", "Página"))
    gerado_em = str(payload.get("gerado_em", ""))
    filtros = payload.get("filtros", []) or []
    graficos = payload.get("graficos", []) or []
    fonte_rodape = str(payload.get("fonte_rodape", ""))
    texto_projeto = str(payload.get("texto_projeto", ""))
    texto_parceria = str(payload.get("texto_parceria", ""))
    logo_data_uri = str(payload.get("logo_data_uri", ""))
    cover_data_uri = str(payload.get("cover_data_uri", ""))

    if aba_preferida:
        alvo = str(aba_preferida).strip()
        subset = [g for g in graficos if str(g.get("aba", "")).strip() == alvo]
        if subset:
            graficos = subset

    abas_unicas = []
    for g in graficos:
        nome_aba = str(g.get("aba", "")).strip() or "Visão geral"
        if nome_aba not in abas_unicas:
            abas_unicas.append(nome_aba)

    if aba_preferida:
        aba_relatorio = str(aba_preferida)
    elif len(abas_unicas) > 1:
        aba_relatorio = "Todas as abas"
    else:
        aba_relatorio = str(abas_unicas[0] if abas_unicas else "Página atual")

    def esc(txt):
        return (
            str(txt or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

    if filtros:
        filtros_html = "".join(
            f"<div class='filtro-item'><span class='filtro-label'>{esc(item.get('label'))}:</span> "
            f"{esc(', '.join([str(v) for v in (item.get('values') or [])]))}</div>"
            for item in filtros
        )
    else:
        filtros_html = (
            "<p class='vazio'>Nenhum filtro aplicado. O relatório reflete a base ativa completa da página.</p>"
        )

    grupos = {}
    for item in graficos:
        aba = str(item.get("aba", "")).strip() or "Visão geral"
        grupos.setdefault(aba, []).append(item)

    charts_html_parts = []
    for idx, aba_nome in enumerate(abas_unicas, start=1):
        itens = grupos.get(aba_nome, [])
        if not itens:
            continue
        cards = []
        for item in itens:
            titulo = esc(item.get("titulo", "Gráfico"))
            conteudo = ""
            if item.get("tipo") == "imagem":
                uri = esc(item.get("data_uri", ""))
                conteudo = f"<img src='{uri}' alt='{titulo}' class='chart-image' />"
            cards.append(
                "<section class='chart-card'>"
                f"<div class='chart-body'>{conteudo}</div>"
                f"<div class='chart-source'>{esc(fonte_rodape)}</div>"
                "</section>"
            )
        charts_html_parts.append(
            "<section class='aba-section'>"
            f"<h3 class='aba-title'>{idx}. {esc(aba_nome)}</h3>"
            + "".join(cards)
            + "</section>"
        )

    charts_html = "".join(charts_html_parts) if charts_html_parts else "<p class='vazio'>Nenhum gráfico disponível para esta página.</p>"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Relatório da Página - {esc(titulo_pagina)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --cv-blue: #0749AB;
      --cv-text: #344054;
      --cv-muted: #667085;
      --cv-border: #dbe4f0;
      --cv-card: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Instrument Sans", Arial, Helvetica, sans-serif;
      color: var(--cv-text);
      background: linear-gradient(180deg, #fbfcff 0%, #f3f6fb 100%);
    }}
    .wrap {{ max-width: 1000px; margin: 0 auto; padding: 20px 22px 34px; }}
    .head {{
      background: var(--cv-card);
      border: 1px solid var(--cv-border);
      border-radius: 16px;
      box-shadow: 0 10px 24px rgba(16,24,40,.08);
      overflow: hidden;
      margin-bottom: 16px;
    }}
    .head-top {{
      padding: 14px 16px 8px;
    }}
    .head-logo {{ width: 100%; max-height: 92px; object-fit: contain; object-position: left center; }}
    .head-cover-wrap {{
      padding: 0 16px 8px;
    }}
    .head-cover {{ width: 100%; height: 288px; border-radius: 10px; object-fit: cover; display: block; }}
    .head-text {{ padding: 0 16px 22px; }}
    h1 {{
      margin: 0 0 4px;
      font-size: 1.9rem;
      color: rgba(0, 0, 0, 0.9);
      line-height: 1.1;
      font-family: "Instrument Sans", Arial, Helvetica, sans-serif;
      font-weight: 800;
    }}
    .head-page {{
      margin-top: 8px;
      font-size: 1.02rem;
      color: #1f3860;
      font-weight: 700;
      line-height: 1.3;
    }}
    .meta {{ margin-top: 10px; font-size: .92rem; color: var(--cv-muted); font-weight: 600; }}
    .bloco {{
      background: var(--cv-card);
      border: 1px solid var(--cv-border);
      border-radius: 14px;
      box-shadow: 0 8px 20px rgba(16,24,40,.06);
      padding: 14px 16px;
      margin-bottom: 14px;
    }}
    .bloco h2 {{ margin: 0 0 8px; font-size: 1.18rem; color: #1f3860; }}
    .aba-section {{ margin-bottom: 20px; }}
    .aba-title {{
      margin: 0 0 12px;
      padding: 10px 14px;
      font-size: 1.06rem;
      color: #ffffff;
      font-weight: 800;
      background: linear-gradient(135deg, #0749AB 0%, #3e73bc 100%);
      border: 1px solid #0a469f;
      border-radius: 10px;
      box-shadow: 0 6px 14px rgba(7, 73, 171, 0.24);
      letter-spacing: 0.01em;
    }}
    .texto {{ margin: 0 0 8px; line-height: 1.45; color: #364f72; }}
    .filtro-item {{ margin: 0 0 5px; font-size: .92rem; line-height: 1.35; }}
    .filtro-label {{ color: #1f3860; font-weight: 700; }}
    .chart-card {{ border: 1px solid var(--cv-border); border-radius: 12px; padding: 10px 12px; margin-bottom: 12px; background: #fff; }}
    .chart-body {{ background: #fff; border-radius: 8px; overflow: hidden; }}
    .chart-image {{ width: 100%; height: auto; display: block; }}
    .chart-source {{ margin-top: 8px; font-size: .78rem; color: #8f97a3; }}
    .vazio {{ margin: 0; color: #667085; font-size: .95rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="head">
      <div class="head-top">
        <img class="head-logo" src="{esc(logo_data_uri)}" alt="Cultura Viva" />
      </div>
      <div class="head-cover-wrap">
        <img class="head-cover" src="{esc(cover_data_uri)}" alt="Capa do projeto" />
      </div>
      <div class="head-text">
        <h1>Dashboard Diagnóstico Econômico da Cultura Viva</h1>
        <div class="head-page">Página: {esc(titulo_pagina)}</div>
        <div class="meta">Criado em: {esc(gerado_em)}</div>
      </div>
    </header>

    <section class="bloco">
      <h2>Introdução</h2>
      <p class="texto">{esc(texto_parceria)}</p>
    </section>

    <section class="bloco">
      <h2>Filtros Ativos da Página</h2>
      {filtros_html}
    </section>

    <section class="bloco">
      {charts_html}
    </section>
  </div>
</body>
</html>
"""


def _bytes_from_data_uri(data_uri):
    if not data_uri or "," not in str(data_uri):
        return "", b""
    try:
        head, body = str(data_uri).split(",", 1)
        mime = ""
        if head.lower().startswith("data:"):
            mime = head.split(":", 1)[1].split(";", 1)[0].strip().lower()
        return mime, base64.b64decode(body)
    except Exception:
        return "", b""


def montar_pdf_relatorio(payload, aba_preferida=None):
    payload = payload or {}
    titulo_pagina = str(payload.get("titulo_pagina", "Página"))
    gerado_em = str(payload.get("gerado_em", ""))
    filtros = payload.get("filtros", []) or []
    graficos = payload.get("graficos", []) or []
    fonte_rodape = str(payload.get("fonte_rodape", ""))
    texto_parceria = str(payload.get("texto_parceria", ""))
    logo_data_uri = str(payload.get("logo_data_uri", ""))
    cover_data_uri = str(payload.get("cover_data_uri", ""))

    if aba_preferida:
        alvo = str(aba_preferida).strip()
        subset = [g for g in graficos if str(g.get("aba", "")).strip() == alvo]
        if subset:
            graficos = subset

    abas_unicas = []
    grupos = {}
    for g in graficos:
        aba = str(g.get("aba", "")).strip() or "Visão geral"
        if aba not in abas_unicas:
            abas_unicas.append(aba)
        grupos.setdefault(aba, []).append(g)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    titulo_doc = f"Dashboard Diagnóstico Econômico da Cultura Viva - {titulo_pagina}"
    c.setTitle(titulo_doc)
    c.setAuthor("Consórcio Universitário Cultura Viva (UFBA, UFF, UFPR)")
    c.setSubject(
        "Relatório analítico gerado pelo Dashboard do Diagnóstico Econômico da Cultura Viva, "
        "com filtros ativos e visualizações da página."
    )
    c.setCreator("Dashboard Diagnóstico Econômico da Cultura Viva")
    c.setKeywords(
        "Cultura Viva, Diagnóstico Econômico, Pontos de Cultura, Pontões de Cultura, "
        "Relatório, Dashboard, Ministério da Cultura, PNCV, PNAB"
    )
    w, h = A4
    ml, mr, mt, mb = 36, 36, 34, 34
    usable_w = w - ml - mr
    y = h - mt

    def nova_pagina():
        nonlocal y
        c.showPage()
        y = h - mt

    def texto_linha(txt, size=10, bold=False, color=(0, 0, 0), spacing=13):
        nonlocal y
        if y < mb + spacing:
            nova_pagina()
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColorRGB(*color)
        c.drawString(ml, y, txt)
        y -= spacing

    def texto_bloco(txt, size=10, bold=False, color=(0, 0, 0), leading=13):
        nonlocal y
        if not txt:
            return
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColorRGB(*color)
        max_w = usable_w
        palavras = str(txt).split()
        linha = ""
        for p in palavras:
            teste = f"{linha} {p}".strip()
            if c.stringWidth(teste, "Helvetica-Bold" if bold else "Helvetica", size) <= max_w:
                linha = teste
            else:
                if y < mb + leading:
                    nova_pagina()
                    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
                    c.setFillColorRGB(*color)
                c.drawString(ml, y, linha)
                y -= leading
                linha = p
        if linha:
            if y < mb + leading:
                nova_pagina()
                c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
                c.setFillColorRGB(*color)
            c.drawString(ml, y, linha)
            y -= leading

    def texto_filtro(label, values, size=9.5, color=(0.2, 0.3, 0.45), leading=12):
        nonlocal y
        label_txt = f"{str(label).strip()}: "
        values_txt = str(values).strip()
        if not label_txt.strip() or not values_txt:
            return

        font_label = "Helvetica-Bold"
        font_val = "Helvetica"

        if y < mb + leading:
            nova_pagina()

        c.setFillColorRGB(*color)
        c.setFont(font_label, size)
        prefix_w = c.stringWidth(label_txt, font_label, size)

        # Monta primeira linha respeitando espaço após o prefixo em negrito
        words = values_txt.split()
        first_line = ""
        while words:
            candidate = f"{first_line} {words[0]}".strip()
            if c.stringWidth(candidate, font_val, size) <= max(20, usable_w - prefix_w):
                first_line = candidate
                words.pop(0)
            else:
                break
        if not first_line and words:
            first_line = words.pop(0)

        # Primeira linha com label em negrito + valor normal
        c.setFont(font_label, size)
        c.drawString(ml, y, label_txt)
        c.setFont(font_val, size)
        c.drawString(ml + prefix_w, y, first_line)
        y -= leading

        # Demais linhas só com o valor (quebra automática)
        if words:
            resto = " ".join(words)
            c.setFont(font_val, size)
            max_w = usable_w
            linha = ""
            for p in resto.split():
                teste = f"{linha} {p}".strip()
                if c.stringWidth(teste, font_val, size) <= max_w:
                    linha = teste
                else:
                    if y < mb + leading:
                        nova_pagina()
                        c.setFillColorRGB(*color)
                        c.setFont(font_val, size)
                    c.drawString(ml, y, linha)
                    y -= leading
                    linha = p
            if linha:
                if y < mb + leading:
                    nova_pagina()
                    c.setFillColorRGB(*color)
                    c.setFont(font_val, size)
                c.drawString(ml, y, linha)
                y -= leading

    # Header
    _, logo_b = _bytes_from_data_uri(logo_data_uri)

    if logo_b:
        try:
            img = ImageReader(io.BytesIO(logo_b))
            iw, ih = img.getSize()
            ww = usable_w
            hh = ww * (ih / max(iw, 1))
            c.drawImage(img, ml, y - hh, width=ww, height=hh, mask="auto")
            y -= hh + 12
        except Exception:
            pass

    _, cover_b = _bytes_from_data_uri(cover_data_uri)
    if cover_b:
        try:
            img = ImageReader(io.BytesIO(cover_b))
            hh = 118
            ww = usable_w
            c.drawImage(img, ml, y - hh, width=ww, height=hh, mask="auto")
            y -= hh + 28
        except Exception:
            pass

    texto_linha("Dashboard Diagnóstico Econômico da Cultura Viva", size=16, bold=True, color=(0.1, 0.1, 0.1), spacing=20)
    texto_linha(f"Página: {titulo_pagina}", size=11, bold=True, color=(0.12, 0.22, 0.38), spacing=15)
    texto_linha(f"Criado em: {gerado_em}", size=10, bold=False, color=(0.4, 0.45, 0.52), spacing=18)
    y -= 14

    # Introdução
    texto_linha("Introdução", size=13, bold=True, color=(0.09, 0.22, 0.4), spacing=17)
    texto_bloco(str(texto_parceria).strip(), size=10, color=(0.2, 0.3, 0.45), leading=13)
    y -= 18

    # Filtros
    texto_linha("Filtros Ativos da Página", size=13, bold=True, color=(0.09, 0.22, 0.4), spacing=17)
    if not filtros:
        texto_linha("Nenhum filtro aplicado.", size=10, color=(0.3, 0.35, 0.45), spacing=13)
    else:
        for item in filtros:
            label = str(item.get("label", "")).strip()
            values = ", ".join([str(v) for v in (item.get("values") or [])]).strip()
            if not label or not values:
                continue
            texto_filtro(label, values, size=9.5, color=(0.2, 0.3, 0.45), leading=12)
    y -= 22

    # Seções (abas) + gráficos
    for idx, aba in enumerate(abas_unicas, start=1):
        nova_pagina()
        # faixa azul de seção
        faixa_h = 20
        c.setFillColorRGB(0.03, 0.29, 0.67)
        c.roundRect(ml, y - faixa_h + 2, usable_w, faixa_h, 4, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(ml + 8, y - 12, f"{idx}. {aba}")
        y -= faixa_h + 8

        for item in grupos.get(aba, []):
            data_uri = str(item.get("data_uri", ""))
            _, img_b = _bytes_from_data_uri(data_uri)
            if not img_b:
                continue
            titulo_item = str(item.get("titulo", "")).strip()
            eh_wordcloud = "palavras mais frequentes" in titulo_item.lower()

            if eh_wordcloud:
                if y < mb + 34:
                    nova_pagina()
                c.setFont("Helvetica", 13)
                c.setFillColorRGB(0.18, 0.26, 0.37)
                c.drawCentredString(ml + (usable_w / 2), y - 6, titulo_item)
                y -= 24

            try:
                img = ImageReader(io.BytesIO(img_b))
                iw, ih = img.getSize()
            except Exception:
                continue

            target_w = usable_w
            target_h = target_w * (ih / max(iw, 1))
            max_h = h - mt - mb - 90
            if target_h > max_h:
                target_h = max_h
                target_w = target_h * (iw / max(ih, 1))

            needed = target_h + 24
            if y < mb + needed:
                nova_pagina()

            c.drawImage(img, ml, y - target_h, width=target_w, height=target_h, mask="auto")
            y -= target_h + 10
            c.setFont("Helvetica", 8.5)
            c.setFillColorRGB(0.56, 0.6, 0.65)
            c.drawString(ml, y, fonte_rodape[:180])
            y -= 14

        y -= 6

    c.save()
    return buf.getvalue()
