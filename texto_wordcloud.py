import re
import unicodedata

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from config import CORES_GRAFICOS


STOPWORDS_PADRAO = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "para",
    "com",
    "por",
    "na",
    "no",
    "nas",
    "nos",
    "a",
    "o",
    "as",
    "os",
    "um",
    "uma",
    "que",
    "se",
    "ao",
    "aos",
    "sim",
    "nao",
    "mais",
    "como",
    "entre",
    "ou",
    "etc",
    "ponto",
    "cultura",
    "cultural",
    "atividade",
    "atividades",
    "quais",
    "tipo",
    "tipos",
}


def normalizar_texto(texto):
    texto = "" if texto is None else str(texto)
    texto = texto.replace("\ufb01", "fi").replace("\ufb02", "fl")
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar_texto(texto, min_chars=4, stopwords=None):
    stop = STOPWORDS_PADRAO if stopwords is None else stopwords
    limpo = normalizar_texto(texto)
    limpo = re.sub(r"http\S+|www\S+", " ", limpo)
    limpo = re.sub(r"[^a-z\s]", " ", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip()
    return [t for t in limpo.split() if len(t) >= min_chars and t not in stop]


def frequencia_termos(series_texto, top_n=120, min_chars=4, stopwords_extra=None):
    stop = set(STOPWORDS_PADRAO)
    if stopwords_extra:
        stop.update({normalizar_texto(x) for x in stopwords_extra})

    tokens = []
    for texto in series_texto:
        tokens.extend(tokenizar_texto(texto, min_chars=min_chars, stopwords=stop))

    if not tokens:
        return pd.Series(dtype="int64")

    return pd.Series(tokens).value_counts().head(top_n)


def gerar_wordcloud(
    series_texto,
    altura_plot=420,
    largura_wc=1400,
    altura_wc=700,
    max_words=180,
    colormap="tab20",
):
    freq = frequencia_termos(series_texto, top_n=max_words)
    if freq.empty:
        return {"tipo": "vazio", "freq": freq}

    try:
        from wordcloud import WordCloud

        def _palette_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            if random_state is None:
                idx = abs(hash(word)) % len(CORES_GRAFICOS)
            else:
                idx = random_state.randint(0, len(CORES_GRAFICOS) - 1)
            return CORES_GRAFICOS[idx]

        # Máscara elíptica para evitar nuvem quadrada.
        yy, xx = np.ogrid[:altura_wc, :largura_wc]
        cx, cy = largura_wc / 2, altura_wc / 2
        rx, ry = largura_wc * 0.46, altura_wc * 0.40
        ellipse = ((xx - cx) ** 2) / (rx**2) + ((yy - cy) ** 2) / (ry**2) <= 1
        mask = np.ones((altura_wc, largura_wc), dtype=np.uint8) * 255
        mask[ellipse] = 0

        wc = WordCloud(
            width=largura_wc,
            height=altura_wc,
            background_color="#f5f5f5",
            mode="RGB",
            mask=mask,
            max_words=min(max_words, len(freq)),
            collocations=False,
            prefer_horizontal=0.9,
            random_state=42,
            min_font_size=12,
            color_func=_palette_color_func,
        )
        wc.generate_from_frequencies(freq.to_dict())

        imagem = wc.to_array()
        # Remove bordas brancas excedentes com limiar de densidade para evitar faixa vazia no topo.
        mascara = np.any(imagem < 245, axis=2)
        linhas = np.where(mascara.sum(axis=1) > max(8, int(mascara.shape[1] * 0.01)))[0]
        colunas = np.where(mascara.sum(axis=0) > max(8, int(mascara.shape[0] * 0.01)))[0]
        if linhas.size > 0 and colunas.size > 0:
            y0, y1 = linhas[0], linhas[-1] + 1
            x0, x1 = colunas[0], colunas[-1] + 1
            pad_y = max((y1 - y0) // 60, 2)
            pad_x = max((x1 - x0) // 60, 2)
            y0 = max(0, y0 - pad_y)
            x0 = max(0, x0 - pad_x)
            y1 = min(imagem.shape[0], y1 + pad_y)
            x1 = min(imagem.shape[1], x1 + pad_x)
            imagem = imagem[y0:y1, x0:x1]

        return {"tipo": "image", "img": imagem, "freq": freq}
    except Exception:
        df_f = freq.reset_index()
        df_f.columns = ["termo", "frequencia"]
        fig = go.Figure(
            go.Treemap(
                labels=df_f["termo"],
                parents=[""] * len(df_f),
                values=df_f["frequencia"],
                marker=dict(colors=df_f["frequencia"], colorscale="Blues"),
                textinfo="label",
                hovertemplate="%{label}<br>Frequencia: %{value}<extra></extra>",
            )
        )
        fig.update_layout(height=altura_plot, margin=dict(l=8, r=8, t=56, b=10))
        return {"tipo": "plotly", "fig": fig, "freq": freq}
