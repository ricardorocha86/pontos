PALETA_CORES = {
    'azul_principal': '#0749AB',
    'verde_secundario': '#007934',
    'amarelo_destaque': '#DDB33F',
    'cinza_claro': '#F3F3F3',
    'cinza_medio': '#C7C7C7',
    'cinza_escuro': '#4A4A4A'
}

CORES_GRAFICOS = [
    PALETA_CORES['azul_principal'],
    PALETA_CORES['verde_secundario'],
    PALETA_CORES['amarelo_destaque']
]

REGIOES_POR_UF = {
    'AC': 'Norte',
    'AL': 'Nordeste',
    'AP': 'Norte',
    'AM': 'Norte',
    'BA': 'Nordeste',
    'CE': 'Nordeste',
    'DF': 'Centro-Oeste',
    'ES': 'Sudeste',
    'GO': 'Centro-Oeste',
    'MA': 'Nordeste',
    'MT': 'Centro-Oeste',
    'MS': 'Centro-Oeste',
    'MG': 'Sudeste',
    'PA': 'Norte',
    'PB': 'Nordeste',
    'PR': 'Sul',
    'PE': 'Nordeste',
    'PI': 'Nordeste',
    'RJ': 'Sudeste',
    'RN': 'Nordeste',
    'RS': 'Sul',
    'RO': 'Norte',
    'RR': 'Norte',
    'SC': 'Sul',
    'SP': 'Sudeste',
    'SE': 'Nordeste',
    'TO': 'Norte'
}

ESTADO_NOME_PARA_SIGLA = {
    'acre': 'AC',
    'alagoas': 'AL',
    'amapa': 'AP',
    'amazonas': 'AM',
    'bahia': 'BA',
    'ceara': 'CE',
    'distrito federal': 'DF',
    'espirito santo': 'ES',
    'goias': 'GO',
    'maranhao': 'MA',
    'mato grosso': 'MT',
    'mato grosso do sul': 'MS',
    'minas gerais': 'MG',
    'para': 'PA',
    'paraiba': 'PB',
    'parana': 'PR',
    'pernambuco': 'PE',
    'piaui': 'PI',
    'rio de janeiro': 'RJ',
    'rio grande do norte': 'RN',
    'rio grande do sul': 'RS',
    'rondonia': 'RO',
    'roraima': 'RR',
    'santa catarina': 'SC',
    'sao paulo': 'SP',
    'sergipe': 'SE',
    'tocantins': 'TO'
}

ORDEM_RECEITA_ANUAL = [
    'Sem receita',
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

MAPA_RECEITA_MEDIA = {
    'Sem receita': 0,
    'Menor que 15.000': 7500,
    '15.001 a 50.000': 32500,
    '50.001 a 100.000': 75000,
    '100.001 a 150.000': 125000,
    '150.001 a 200.000': 175000,
    '200.001 a 250.000': 225000,
    '250.001 a 300.000': 275000,
    '300.001 a 350.000': 325000,
    '350.001 a 400.000': 375000,
    'Maior que 400.000': 450000
}

FAIXAS_PORTE = [
    (20000, 'Até 20 mil'),
    (50000, '20 a 50 mil'),
    (100000, '50 a 100 mil'),
    (500000, '100 a 500 mil'),
    (float('inf'), 'Acima de 500 mil')
]

ORDEM_FAIXA_POPULACIONAL = [
    'Até 5.000 habitantes',
    '5.001 a 10.000 habitantes',
    '10.001 a 20.000 habitantes',
    '20.001 a 50.000 habitantes',
    '50.001 a 100.000 habitantes',
    '100.001 a 500.000 habitantes',
    'Mais de 500.000 habitantes'
]

