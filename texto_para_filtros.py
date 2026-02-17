from __future__ import annotations

import json
from typing import Any, Literal, Type

import streamlit as st

from utils import normalizar_texto

try:
    from pydantic import BaseModel, ConfigDict, Field, create_model

    _HAS_PYDANTIC = True
except Exception:
    BaseModel = None  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    create_model = None  # type: ignore[assignment]
    _HAS_PYDANTIC = False


MODELO_GEMINI_TEXTO_FILTROS = 'gemini-3-flash-preview'
NIVEL_PENSAMENTO = 'low'
MAX_ENUM_ITENS_SCHEMA = 250

_SIM_NAO = ['Sim', 'Não']

_CAPITAIS_POR_REGIAO = {
    'Norte': ['Rio Branco', 'Macapá', 'Manaus', 'Belém', 'Porto Velho', 'Boa Vista', 'Palmas'],
    'Nordeste': ['São Luís', 'Teresina', 'Fortaleza', 'Natal', 'João Pessoa', 'Recife', 'Maceió', 'Aracaju', 'Salvador'],
    'Centro-Oeste': ['Brasília', 'Goiânia', 'Cuiabá', 'Campo Grande'],
    'Sudeste': ['Belo Horizonte', 'Vitória', 'Rio de Janeiro', 'São Paulo'],
    'Sul': ['Curitiba', 'Florianópolis', 'Porto Alegre'],
}

_SYSTEM_INSTRUCTION = """
Você é um interpretador semântico especializado no dashboard "Pontos de Cultura".

Objetivo do seu trabalho:
- Ler a solicitação textual do usuário.
- Traduzir essa solicitação para um objeto de filtros estruturado.
- O objeto será usado para auto-selecionar os widgets de filtro do dashboard.

Contexto funcional do dashboard:
- O painel possui filtros de cadastro territorial/institucional e filtros de acesso a recursos.
- As categorias válidas (estados, regiões, municípios, faixas, ações, linguagens, receitas etc.) variam conforme os dados carregados.
- O schema de resposta já traz os campos e os valores permitidos para o momento atual.
- Não existe tolerância para categorias inventadas.

Interpretação de domínio esperada:
- "pontões", "pontao", "pontão" => tipo_ponto = "Pontão".
- "pontos" (quando não for pontão) => tipo_ponto = "Ponto".
- "capitais do nordeste" => selecionar municípios que sejam capitais nordestinas e estejam disponíveis.
- "somente", "apenas", "quero ver", "filtre por", "mostre" são comandos de filtragem.
- Filtros booleanos representam acesso (Sim/Não) a recursos e modalidades.

Política de validade (`solicitacao_valida`):
- Use `true` quando a entrada parecer uma intenção real de filtrar dados do dashboard.
- Use `false` quando for texto aleatório, brincadeira, ofensa, spam, teste sem contexto, ou conteúdo sem relação com filtros.
- Em caso de baixa confiança sem evidência de intenção clara, use `false`.

Regras obrigatórias de preenchimento:
1) Retorne TODOS os campos do schema.
2) Use exclusivamente valores permitidos no schema (inclusive grafia e acentos).
3) Não invente categorias inexistentes.
4) Em campos de lista sem correspondência, retorne [].
5) Em campos únicos sem correspondência, retorne null.
6) Em filtros booleanos, use somente "Sim", "Não" ou null.
7) Não force suposições: preencha apenas o que estiver explícito ou inferível com alta confiança.
8) Preencha `justificativa` em uma frase curta, objetiva e legível.
9) Não retorne texto fora do JSON estruturado.
""".strip()


if _HAS_PYDANTIC:

    class _SchemaBase(BaseModel):
        model_config = ConfigDict(extra='forbid')


def _resultado_vazio() -> dict[str, Any]:
    return {
        'estado': [],
        'regiao': [],
        'municipio': [],
        'faixa_populacional': [],
        'acoes_estruturantes': [],
        'linguagem_artistica': [],
        'faixa_receita': [],
        'tipo_ponto': None,
        'registro': None,
        'rec_federal': None,
        'rec_minc': None,
        'rec_estadual': None,
        'rec_municipal': None,
        'pnab_estadual': None,
        'pnab_municipal': None,
        'tcc_est_ponto': None,
        'tcc_est_pontao': None,
        'tcc_mun_ponto': None,
        'tcc_mun_pontao': None,
    }


def _deduplicar_lista(valores: list[str]) -> list[str]:
    vistos = set()
    saida = []
    for valor in valores:
        if valor not in vistos:
            vistos.add(valor)
            saida.append(valor)
    return saida


def _normalizar_opcoes(opcoes: Any) -> list[str]:
    if not isinstance(opcoes, (list, tuple, set)):
        return []
    saida = []
    vistos = set()
    for item in opcoes:
        valor = str(item).strip()
        if valor and valor not in vistos:
            vistos.add(valor)
            saida.append(valor)
    return saida


def _literal_dinamico(opcoes: list[str]):
    opcoes_limpa = tuple(_normalizar_opcoes(opcoes))
    if not opcoes_limpa:
        return str
    return Literal.__getitem__(opcoes_limpa)


def _tipo_lista_restrita(opcoes: list[str]):
    if len(_normalizar_opcoes(opcoes)) > MAX_ENUM_ITENS_SCHEMA:
        return list[str]
    literal_tipo = _literal_dinamico(opcoes)
    if literal_tipo is str:
        return list[str]
    return list[literal_tipo]


def _tipo_unico_restrito(opcoes: list[str]):
    literal_tipo = _literal_dinamico(opcoes)
    if literal_tipo is str:
        return str | None
    return literal_tipo | None


def _resumo_catalogo(catalogo: dict[str, Any]) -> dict[str, int]:
    return {
        'estados': len(_normalizar_opcoes(catalogo.get('estado', []))),
        'regioes': len(_normalizar_opcoes(catalogo.get('regiao', []))),
        'municipios': len(_normalizar_opcoes(catalogo.get('municipio', []))),
        'faixas_populacionais': len(_normalizar_opcoes(catalogo.get('faixa_populacional', []))),
        'acoes_estruturantes': len(_normalizar_opcoes(catalogo.get('acoes_estruturantes', []))),
        'linguagens_artisticas': len(_normalizar_opcoes(catalogo.get('linguagem_artistica', []))),
        'faixas_receita': len(_normalizar_opcoes(catalogo.get('faixa_receita', []))),
    }


def _mapear_lista(valores: list[str] | None, opcoes: list[str]) -> list[str]:
    if not valores:
        return []

    mapa = {}
    for opcao in _normalizar_opcoes(opcoes):
        chave = normalizar_texto(opcao)
        if chave and chave not in mapa:
            mapa[chave] = opcao

    saida = []
    for valor in valores:
        chave = normalizar_texto(valor)
        if chave in mapa:
            saida.append(mapa[chave])

    return _deduplicar_lista(saida)


def _mapear_unico(valor: str | None, opcoes: list[str]) -> str | None:
    if not valor:
        return None
    encontrados = _mapear_lista([valor], opcoes)
    return encontrados[0] if encontrados else None


def _obter_api_key() -> str:
    try:
        secret_key = str(st.secrets.get('GEMINI_API_KEY', '')).strip()
        if secret_key:
            return secret_key
    except Exception:
        pass
    return ''


def _montar_prompt_usuario(solicitacao: str, catalogo: dict[str, Any]) -> str:
    resumo = _resumo_catalogo(catalogo)
    catalogo_serializado = json.dumps(catalogo, ensure_ascii=False, indent=2)
    municipios_disponiveis = _normalizar_opcoes(catalogo.get('municipio', []))
    anexo_municipios = '\n'.join(f'- {cidade}' for cidade in municipios_disponiveis)

    return f"""
Tarefa:
Converta a solicitação em filtros estruturados para o dashboard de Pontos de Cultura.
Use rigor semântico e obedeça estritamente o schema.

Solicitação do usuário:
\"\"\"{solicitacao.strip()}\"\"\"

Resumo do catálogo carregado:
- Estados disponíveis: {resumo['estados']}
- Regiões disponíveis: {resumo['regioes']}
- Municípios disponíveis: {resumo['municipios']}
- Faixas populacionais: {resumo['faixas_populacionais']}
- Ações estruturantes: {resumo['acoes_estruturantes']}
- Linguagens artísticas: {resumo['linguagens_artisticas']}
- Faixas de receita: {resumo['faixas_receita']}

Regras adicionais de extração:
- Só preencha filtros mencionados direta ou indiretamente com alta confiança.
- Se a frase não configurar intenção de filtro do painel, retorne solicitacao_valida=false.
- Não misture categorias (ex.: estado em município, linguagem em ação etc.).
- Não preencha campos com "aproximações" fora do catálogo.
- Se o usuário pedir "capitais de uma região", retorne os municípios-capitais disponíveis no catálogo.
- Para o campo municipio, use exclusivamente nomes do anexo de municípios disponíveis.
- Preserve a escrita dos municípios exatamente como aparece no anexo.

Catálogo oficial completo (valores permitidos):
{catalogo_serializado}

Anexo: Municípios disponíveis para seleção (use somente estes nomes no campo municipio)
{anexo_municipios}

Retorne somente o objeto JSON estruturado conforme schema.
""".strip()


def _expandir_capitais_por_solicitacao(solicitacao: str, municipios_disponiveis: list[str]) -> list[str]:
    texto = normalizar_texto(solicitacao)
    if 'capital' not in texto:
        return []

    regioes = [reg for reg in _CAPITAIS_POR_REGIAO if normalizar_texto(reg) in texto]
    if not regioes and (
        'capitais do brasil' in texto
        or 'capitais brasileiras' in texto
        or 'todas as capitais' in texto
    ):
        regioes = list(_CAPITAIS_POR_REGIAO.keys())

    if not regioes:
        return []

    candidatas = []
    for regiao in regioes:
        candidatas.extend(_CAPITAIS_POR_REGIAO[regiao])

    return _mapear_lista(candidatas, municipios_disponiveis)


def _validar_municipios_retorno(municipios_llm: list[str], municipios_disponiveis: list[str]) -> list[str]:
    """
    Sanitiza municípios retornados pelo LLM mantendo apenas os que existem
    na lista oficial de municípios disponíveis para seleção.
    """
    return _mapear_lista(municipios_llm, municipios_disponiveis)


def _criar_schema_filtros(catalogo: dict[str, Any]) -> Type[BaseModel]:
    if not _HAS_PYDANTIC:
        raise RuntimeError('pydantic não disponível.')

    op_estado = _normalizar_opcoes(catalogo.get('estado', []))
    op_regiao = _normalizar_opcoes(catalogo.get('regiao', []))
    op_municipio = _normalizar_opcoes(catalogo.get('municipio', []))
    op_faixa_pop = _normalizar_opcoes(catalogo.get('faixa_populacional', []))
    op_acoes = _normalizar_opcoes(catalogo.get('acoes_estruturantes', []))
    op_linguagem = _normalizar_opcoes(catalogo.get('linguagem_artistica', []))
    op_receita = _normalizar_opcoes(catalogo.get('faixa_receita', []))
    op_tipo = _normalizar_opcoes(catalogo.get('tipo_ponto', []))
    op_registro = _normalizar_opcoes(catalogo.get('registro', []))
    op_bool = _normalizar_opcoes(catalogo.get('filtros_booleanos', _SIM_NAO)) or _SIM_NAO

    campos = {
        'solicitacao_valida': (
            bool,
            Field(..., description='true quando a entrada for uma solicitação válida de filtros do dashboard.'),
        ),
        'justificativa': (
            str,
            Field(default='', description='Frase curta e objetiva explicando a interpretação.'),
        ),
        'estado': (
            _tipo_lista_restrita(op_estado),
            Field(default_factory=list, description='Estados selecionados exclusivamente do catálogo.'),
        ),
        'regiao': (
            _tipo_lista_restrita(op_regiao),
            Field(default_factory=list, description='Regiões selecionadas exclusivamente do catálogo.'),
        ),
        'municipio': (
            _tipo_lista_restrita(op_municipio),
            Field(default_factory=list, description='Municípios selecionados exclusivamente do catálogo.'),
        ),
        'faixa_populacional': (
            _tipo_lista_restrita(op_faixa_pop),
            Field(default_factory=list, description='Faixas populacionais exclusivamente do catálogo.'),
        ),
        'acoes_estruturantes': (
            _tipo_lista_restrita(op_acoes),
            Field(default_factory=list, description='Ações estruturantes exclusivamente do catálogo.'),
        ),
        'linguagem_artistica': (
            _tipo_lista_restrita(op_linguagem),
            Field(default_factory=list, description='Linguagens artísticas exclusivamente do catálogo.'),
        ),
        'faixa_receita': (
            _tipo_lista_restrita(op_receita),
            Field(default_factory=list, description='Faixas de receita exclusivamente do catálogo.'),
        ),
        'tipo_ponto': (
            _tipo_unico_restrito(op_tipo),
            Field(default=None, description='Tipo de reconhecimento (Ponto/Pontão) dentro do catálogo.'),
        ),
        'registro': (
            _tipo_unico_restrito(op_registro),
            Field(default=None, description='Tipo de cadastro jurídico dentro do catálogo.'),
        ),
        'rec_federal': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'rec_minc': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'rec_estadual': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'rec_municipal': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'pnab_estadual': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'pnab_municipal': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'tcc_est_ponto': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'tcc_est_pontao': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'tcc_mun_ponto': (_tipo_unico_restrito(op_bool), Field(default=None)),
        'tcc_mun_pontao': (_tipo_unico_restrito(op_bool), Field(default=None)),
    }

    return create_model(
        'FiltrosTextoEstruturadosDinamico',
        __base__=_SchemaBase,
        **campos,
    )


def _criar_thinking_config_low(types):
    try:
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
    except Exception:
        return types.ThinkingConfig(thinking_level=NIVEL_PENSAMENTO)


def _eh_erro_timeout(exc: Exception) -> bool:
    texto = str(exc).lower()
    sinais = ['timeout', 'timed out', 'deadline', 'tempo limite', 'request timed out']
    return any(sinal in texto for sinal in sinais)


def tem_algum_filtro(filtros: dict[str, Any]) -> bool:
    for valor in filtros.values():
        if isinstance(valor, list) and valor:
            return True
        if valor is not None and valor != '':
            return True
    return False


def interpretar_solicitacao_texto(
    solicitacao: str,
    catalogo: dict[str, Any],
) -> dict[str, Any]:
    solicitacao = (solicitacao or '').strip()
    if not solicitacao:
        return {
            'status': 'invalida',
            'mensagem': 'Escreva uma solicitação antes de aplicar filtros por texto.',
            'filtros': _resultado_vazio(),
            'modelo_usado': None,
        }

    if not _HAS_PYDANTIC:
        return {
            'status': 'erro',
            'mensagem': 'Dependência ausente: instale pydantic para usar texto -> filtros.',
            'filtros': _resultado_vazio(),
            'modelo_usado': None,
        }

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return {
            'status': 'erro',
            'mensagem': 'Dependência ausente: instale google-genai para usar texto -> filtros.',
            'filtros': _resultado_vazio(),
            'modelo_usado': None,
        }

    api_key = _obter_api_key()
    if not api_key:
        return {
            'status': 'erro',
            'mensagem': (
                'GEMINI_API_KEY não encontrado. Defina em st.secrets["GEMINI_API_KEY"].'
            ),
            'filtros': _resultado_vazio(),
            'modelo_usado': None,
        }

    try:
        schema_model = _criar_schema_filtros(catalogo)
    except Exception as exc:
        return {
            'status': 'erro',
            'mensagem': f'Falha ao criar schema dinâmico de filtros: {exc}',
            'filtros': _resultado_vazio(),
            'modelo_usado': None,
        }

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=60000),
    )
    prompt_usuario = _montar_prompt_usuario(solicitacao, catalogo)

    schema_json = schema_model.model_json_schema()

    config_kwargs = {
        'temperature': 0.0,
        'response_mime_type': 'application/json',
        'response_json_schema': schema_json,
        'system_instruction': _SYSTEM_INSTRUCTION,
    }
    try:
        config_kwargs['thinking_config'] = _criar_thinking_config_low(types)
    except Exception:
        pass

    config = types.GenerateContentConfig(**config_kwargs)

    try:
        resposta = client.models.generate_content(
            model=MODELO_GEMINI_TEXTO_FILTROS,
            contents=prompt_usuario,
            config=config,
        )
    except Exception as exc:
        if _eh_erro_timeout(exc):
            return {
                'status': 'erro',
                'mensagem': 'A solicitação demorou mais que o esperado. Tente novamente.',
                'filtros': _resultado_vazio(),
                'modelo_usado': MODELO_GEMINI_TEXTO_FILTROS,
            }
        return {
            'status': 'erro',
            'mensagem': f'Falha ao chamar Gemini: {exc}',
            'filtros': _resultado_vazio(),
            'modelo_usado': MODELO_GEMINI_TEXTO_FILTROS,
        }

    try:
        parsed = getattr(resposta, 'parsed', None)
        if parsed is None:
            texto_json = getattr(resposta, 'text', None)
            if not texto_json:
                raise ValueError('Resposta estruturada vazia.')
            parsed = schema_model.model_validate_json(texto_json)
        elif isinstance(parsed, dict):
            parsed = schema_model.model_validate(parsed)
    except Exception as exc:
        return {
            'status': 'erro',
            'mensagem': f'Falha ao interpretar output estruturado: {exc}',
            'filtros': _resultado_vazio(),
            'modelo_usado': MODELO_GEMINI_TEXTO_FILTROS,
        }

    if not parsed.solicitacao_valida:
        justificativa = (parsed.justificativa or '').strip()
        return {
            'status': 'invalida',
            'mensagem': justificativa or 'A entrada não parece uma solicitação válida de filtros.',
            'filtros': _resultado_vazio(),
            'modelo_usado': MODELO_GEMINI_TEXTO_FILTROS,
        }

    op_estado = _normalizar_opcoes(catalogo.get('estado', []))
    op_regiao = _normalizar_opcoes(catalogo.get('regiao', []))
    op_municipio = _normalizar_opcoes(catalogo.get('municipio', []))
    op_faixa_pop = _normalizar_opcoes(catalogo.get('faixa_populacional', []))
    op_acoes = _normalizar_opcoes(catalogo.get('acoes_estruturantes', []))
    op_linguagem = _normalizar_opcoes(catalogo.get('linguagem_artistica', []))
    op_receita = _normalizar_opcoes(catalogo.get('faixa_receita', []))
    op_tipo = _normalizar_opcoes(catalogo.get('tipo_ponto', []))
    op_registro = _normalizar_opcoes(catalogo.get('registro', []))

    municipios_llm = _validar_municipios_retorno(parsed.municipio, op_municipio)
    municipios_capitais = _expandir_capitais_por_solicitacao(solicitacao, op_municipio)
    municipios_final = _deduplicar_lista(municipios_llm + municipios_capitais)

    filtros = {
        'estado': _mapear_lista(parsed.estado, op_estado),
        'regiao': _mapear_lista(parsed.regiao, op_regiao),
        'municipio': municipios_final,
        'faixa_populacional': _mapear_lista(parsed.faixa_populacional, op_faixa_pop),
        'acoes_estruturantes': _mapear_lista(parsed.acoes_estruturantes, op_acoes),
        'linguagem_artistica': _mapear_lista(parsed.linguagem_artistica, op_linguagem),
        'faixa_receita': _mapear_lista(parsed.faixa_receita, op_receita),
        'tipo_ponto': _mapear_unico(parsed.tipo_ponto, op_tipo),
        'registro': _mapear_unico(parsed.registro, op_registro),
        'rec_federal': _mapear_unico(parsed.rec_federal, _SIM_NAO),
        'rec_minc': _mapear_unico(parsed.rec_minc, _SIM_NAO),
        'rec_estadual': _mapear_unico(parsed.rec_estadual, _SIM_NAO),
        'rec_municipal': _mapear_unico(parsed.rec_municipal, _SIM_NAO),
        'pnab_estadual': _mapear_unico(parsed.pnab_estadual, _SIM_NAO),
        'pnab_municipal': _mapear_unico(parsed.pnab_municipal, _SIM_NAO),
        'tcc_est_ponto': _mapear_unico(parsed.tcc_est_ponto, _SIM_NAO),
        'tcc_est_pontao': _mapear_unico(parsed.tcc_est_pontao, _SIM_NAO),
        'tcc_mun_ponto': _mapear_unico(parsed.tcc_mun_ponto, _SIM_NAO),
        'tcc_mun_pontao': _mapear_unico(parsed.tcc_mun_pontao, _SIM_NAO),
    }

    justificativa = (parsed.justificativa or '').strip()
    mensagem = justificativa or 'Solicitação interpretada com sucesso.'

    return {
        'status': 'ok',
        'mensagem': mensagem,
        'filtros': filtros,
        'modelo_usado': MODELO_GEMINI_TEXTO_FILTROS,
    }
