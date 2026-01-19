import concurrent.futures as cf
import json
import os
import urllib.parse
import urllib.request
import pandas as pd

CAMINHO_BASE = 'base_final.csv'
COLUNA_CEP = 'cep_corrigido'
CAMINHO_SAIDA = 'assets/ceps_geocodificados.csv'


def limpar_ceps(serie):
    return pd.Series(serie).dropna().astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)


def buscar_lat_lon(cep):
    params = urllib.parse.urlencode({'format': 'json', 'limit': 1, 'postalcode': cep, 'country': 'Brazil'})
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': 'pontos-cultura/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            dados = json.loads(resp.read().decode('utf-8'))
        if dados:
            return float(dados[0]['lat']), float(dados[0]['lon'])
    except Exception:
        return None, None
    return None, None


def carregar_existente():
    if not os.path.exists(CAMINHO_SAIDA):
        return {}
    df = pd.read_csv(CAMINHO_SAIDA, encoding='utf-8-sig')
    df['cep'] = df['cep'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(8)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    return {row['cep']: (row['latitude'], row['longitude']) for _, row in df.iterrows()}


def gerar_ceps():
    df = pd.read_csv(CAMINHO_BASE, encoding='utf-8-sig')
    if COLUNA_CEP not in df.columns:
        print('Coluna de CEP não encontrada.')
        return
    existentes = carregar_existente()
    ceps_todos = limpar_ceps(df[COLUNA_CEP]).unique().tolist()
    ceps = [c for c in ceps_todos if c not in existentes]
    resultados = []
    total = len(ceps)
    with cf.ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {executor.submit(buscar_lat_lon, cep): cep for cep in ceps}
        for i, futuro in enumerate(cf.as_completed(futuros), 1):
            cep = futuros[futuro]
            lat, lon = futuro.result()
            if lat is not None and lon is not None:
                resultados.append({'cep': cep, 'latitude': lat, 'longitude': lon})
            if i % 100 == 0 or i == total:
                print(f'{i}/{total}')
    for cep, (lat, lon) in existentes.items():
        resultados.append({'cep': cep, 'latitude': lat, 'longitude': lon})
    pd.DataFrame(resultados).drop_duplicates(subset=['cep']).to_csv(CAMINHO_SAIDA, index=False, encoding='utf-8-sig')
    print(f'Arquivo gerado: {CAMINHO_SAIDA} ({len(resultados)}/{len(ceps_todos)})')


gerar_ceps()

