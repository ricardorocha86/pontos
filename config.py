PALETA_CORES = {
    "principais": ["#E43C2F", "#0749AB", "#DDB33F"],
    "secundarias": [
        "#FF4903", "#05A155", 
        "#417ABD", "#007934", 
        "#FFA400" 
    ]
}

# Mapping old keys to new palette for compatibility/preference
CORES_DINAMICAS = {
    'azul_principal': PALETA_CORES['principais'][1], # #0749AB
    'vermelho_principal': PALETA_CORES['principais'][0], # #E43C2F
    'amarelo_principal': PALETA_CORES['principais'][2], # #DDB33F
    'cinza_claro': '#F3F3F3',
    'cinza_medio': '#C7C7C7',
    'cinza_escuro': '#4A4A4A',
    'texto_grafico': '#000000'
}

CORES_GRAFICOS = PALETA_CORES['principais'] + PALETA_CORES['secundarias']

REGIOES_POR_UF = {
    'AC': 'Norte', 'AL': 'Nordeste', 'AP': 'Norte', 'AM': 'Norte', 'BA': 'Nordeste',
    'CE': 'Nordeste', 'DF': 'Centro-Oeste', 'ES': 'Sudeste', 'GO': 'Centro-Oeste',
    'MA': 'Nordeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'MG': 'Sudeste',
    'PA': 'Norte', 'PB': 'Nordeste', 'PR': 'Sul', 'PE': 'Nordeste', 'PI': 'Nordeste',
    'RJ': 'Sudeste', 'RN': 'Nordeste', 'RS': 'Sul', 'RO': 'Norte', 'RR': 'Norte',
    'SC': 'Sul', 'SP': 'Sudeste', 'SE': 'Nordeste', 'TO': 'Norte'
}

ESTADO_NOME_PARA_SIGLA = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito federal': 'DF', 'espirito santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio de janeiro': 'RJ', 'rio grande do norte': 'RN', 'rio grande do sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'sao paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO'
}

ORDEM_FAIXA_POPULACIONAL = [
    'Até 5.000 habitantes',
    '5.001 a 10.000 habitantes',
    '10.001 a 20.000 habitantes',
    '20.001 a 50.000 habitantes',
    '50.001 a 100.000 habitantes',
    '100.001 a 500.000 habitantes',
    'Mais de 500.000 habitantes'
]

FAIXAS_RECEITA = [
    'Não teve receita',
    'Menor que 15.000',
    '15.001 a 50.000',
    '50.001 a 100.000',
    '100.001 a 150.000',
    '150.001 a 200.000',
    '200.001 a 250.000',
    '250.001 a 300.000',
    '300.001 a 350.000',
    '350.001 a 400.000',
    'Maior que 400.000'
]

# ---------------------------------------------------------------------------
# Tipografia Global (Sans-Serif padronizada)
# ---------------------------------------------------------------------------
FONTE_FAMILIA = "Inter, Arial, Helvetica, sans-serif"

FONTE_TAMANHOS = {
    'titulo': 18,       # título do gráfico
    'subtitulo': 18,    # subtítulo / anotações
    'eixo': 14,         # labels dos eixos
    'tick': 13,         # valores nos eixos (ticks)
    'legenda': 14,      # texto da legenda
    'legenda_titulo': 15,
    'dado': 14,         # texto sobre as barras / fatias
    'anotacao': 20,     # anotações centrais (donut, etc.)
    'geral': 13,        # font-size padrão do layout
}


