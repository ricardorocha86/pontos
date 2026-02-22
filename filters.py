import html

import streamlit as st

from config import FAIXAS_RECEITA, ORDEM_FAIXA_POPULACIONAL, SIGLA_PARA_ESTADO_NOME
from texto_para_filtros import interpretar_solicitacao_texto, tem_algum_filtro
from utils import ACOES_ESTRUTURANTES, aplicar_filtros


def _fmt_int(valor):
    try:
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return str(valor)


def _card_status(label, atual, total):
    return f"""
    <div class="cv-status-card">
        <div class="cv-status-label">{label}</div>
        <div class="cv-status-value">{_fmt_int(atual)}</div>
        <div class="cv-status-note">de {_fmt_int(total)} na base</div>
    </div>
    """


def _limitar_itens(valores, max_itens=5):
    lista = [str(v) for v in valores if v is not None and str(v).strip()]
    if len(lista) <= max_itens:
        return lista, 0
    return lista[:max_itens], len(lista) - max_itens


def _renderizar_chips_sidebar(st_container, titulo, valores, max_itens=5):
    exibidos, restantes = _limitar_itens(valores, max_itens=max_itens)
    if not exibidos:
        return

    chips = ''.join(
        f'<span class="cv-chip">{html.escape(item)}</span>'
        for item in exibidos
    )
    if restantes > 0:
        chips += f'<span class="cv-chip cv-chip-more">... (+{restantes})</span>'

    st_container.markdown(f'<div class="cv-chip-title">{html.escape(titulo)}:</div>', unsafe_allow_html=True)
    st_container.markdown(f'<div class="cv-chip-wrap">{chips}</div>', unsafe_allow_html=True)


def renderizar_painel_filtros(df):
    """
    Renderiza o painel de filtros e salva em st.session_state['filtros_globais'].
    Também exibe um resumo da seleção na barra lateral.
    """

    ui_version = st.session_state.get('_filtros_ui_version', 0)

    def get_key(base):
        return f'input_{ui_version}_{base}'

    pending_texto_filtros = st.session_state.pop('_texto_para_filtros_pending', None)
    if isinstance(pending_texto_filtros, dict):
        for base, valor in pending_texto_filtros.items():
            st.session_state[get_key(base)] = valor
    pending_texto_input = st.session_state.pop('_texto_para_filtros_input_pending', None)
    if isinstance(pending_texto_input, str):
        st.session_state['texto_para_filtros_input'] = pending_texto_input
    aplicar_texto_pending = st.session_state.pop('_texto_para_filtros_aplicar_pending', False)

    header_text = '🔎 Filtros Estratégicos da Base de Dados da Pesquisa'

    with st.expander(header_text, expanded=False):
        if 'linguagens_lista' in df.columns:
            contagem_linguagens = df['linguagens_lista'].explode().value_counts()
            opcoes_linguagens = sorted(contagem_linguagens[contagem_linguagens >= 10].index.tolist())
        else:
            opcoes_linguagens = []

        colunas_acao = []
        pergunta_acao = (
            '10. As atividades do Ponto de Cultura estão relacionadas diretamente '
            'com quais ações estruturante da Política Nacional de Cultura Viva?'
        )

        for coluna in df.columns:
            texto = str(coluna)
            if texto in ACOES_ESTRUTURANTES or 'ações estruturante' in texto or 'acoes estruturante' in texto:
                if texto.strip() == pergunta_acao:
                    continue
                colunas_acao.append(coluna)

        def rotulo_acao(coluna):
            texto = str(coluna)
            if '(' in texto and ')' in texto:
                return texto.split('(', 1)[1].rsplit(')', 1)[0].strip()
            return texto.replace(pergunta_acao, '').strip(' -')

        opcoes_estado = sorted(df['estado'].dropna().unique())
        opcoes_regiao = sorted(df['regiao'].dropna().unique())
        opcoes_municipio_todas = sorted(df['cidade'].dropna().unique())
        opcoes_tipo = sorted(df['tipo_ponto'].dropna().unique())
        opcoes_registro = sorted(df['registro'].dropna().unique())

        def _rotulo_registro(valor):
            txt = str(valor)
            txt = txt.replace('(como coletivo ou grupo)', '(como coletivo)')
            return txt

        def _rotulo_estado_sigla(sigla):
            return SIGLA_PARA_ESTADO_NOME.get(str(sigla), str(sigla))
        opcoes_acessos_recursos = [
            ('rec_federal', 'Recursos Federais'),
            ('rec_minc', 'Editais do Ministério da Cultura'),
            ('rec_estadual', 'Recursos Estaduais'),
            ('rec_municipal', 'Recursos Municipais'),
            ('pnab_estadual', 'PNAB Estadual'),
            ('pnab_municipal', 'PNAB Municipal'),
            ('tcc_est_ponto', 'TCC Estadual (Ponto)'),
            ('tcc_est_pontao', 'TCC Estadual (Pontão)'),
            ('tcc_mun_ponto', 'TCC Municipal (Ponto)'),
            ('tcc_mun_pontao', 'TCC Municipal (Pontão)'),
        ]
        mapa_label_recurso = {k: v for k, v in opcoes_acessos_recursos}

        mapa_acao_rotulo_coluna = {}
        for coluna_acao in colunas_acao:
            rotulo = rotulo_acao(coluna_acao)
            if rotulo and rotulo not in mapa_acao_rotulo_coluna:
                mapa_acao_rotulo_coluna[rotulo] = coluna_acao
        opcoes_acao_texto = list(mapa_acao_rotulo_coluna.keys())

        feedback_texto = st.session_state.pop('_texto_para_filtros_feedback', None)
        if isinstance(feedback_texto, dict) and feedback_texto.get('texto'):
            tipo_feedback = feedback_texto.get('tipo', 'info')
            texto_feedback = feedback_texto['texto']
            if tipo_feedback == 'success':
                st.toast(texto_feedback, icon='✅')
            elif tipo_feedback == 'warning':
                st.warning(texto_feedback)
            elif tipo_feedback == 'error':
                st.error(texto_feedback)
            else:
                st.info(texto_feedback)

        st.markdown(
            """
            <style>
            .st-key-assistente_filtros_texto {
                background: #e2efff;
                border: 1px solid #c9defb;
                border-radius: 0.75rem;
                padding: 0.9rem 0.9rem 0.55rem 0.9rem;
                margin-bottom: 0.8rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key='assistente_filtros_texto'):
            st.markdown(
                """
                <style>
                .st-key-exemplos_filtros_nl button[kind="secondary"] {
                    min-height: 84px !important;
                    height: clamp(84px, 12vh, 132px) !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }
                .st-key-exemplos_filtros_nl button[kind="secondary"] p {
                    font-size: 0.84rem !important;
                    color: #667085 !important;
                    font-style: italic !important;
                    line-height: 1.22 !important;
                    margin: 0 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            col_assistente, col_exemplos = st.columns([1, 1], gap='large')

            with col_assistente:
                st.markdown('#### 🧪 Assistente de Filtros por Texto')
                st.caption(
                    'Um modelo de linguagem natural interpreta sua solicitação e estima os filtros mais prováveis. '
                    'Como é um recurso em teste, pode haver erros e a resposta pode levar até 60 segundos. '
                    'Feedbacks são bem-vindos.'
                )
                texto_solicitacao = st.text_input(
                    'Descreva o seu filtro:',
                    key='texto_para_filtros_input',
                    placeholder='Ex.: pontões das capitais do Nordeste com recursos federais.',
                )
                aplicar_texto = st.button(
                    'Aplicar filtros',
                    key='aplicar_texto_para_filtros',
                    use_container_width=True,
                )
                if aplicar_texto_pending:
                    aplicar_texto = True

            with col_exemplos:
                st.markdown('**Exemplos de solicitações em linguagem natural**')
                with st.container(key='exemplos_filtros_nl'):
                    exemplos = [
                        "mostrar pontões nas capitais do Nordeste com acesso a recursos federais e receita acima de 100 mil",
                        "apenas pontos da Região Metropolitana de Salvador com ações para mulheres e diversidade de gênero",
                        "quero coletivos sem cadastro jurídico formal que atuam com dança e acessaram recursos estaduais",
                        "filtre pontões da região Norte com atuação em povos indígenas e acesso a editais do MinC",
                    ]
                    ex_c1, ex_c2 = st.columns(2, gap='small')
                    exemplo_escolhido = None

                    for idx, exemplo in enumerate(exemplos):
                        col_ex = ex_c1 if idx % 2 == 0 else ex_c2
                        if col_ex.button(
                            f'"{exemplo}"',
                            key=get_key(f'exemplo_texto_{idx}'),
                            use_container_width=True,
                        ):
                            exemplo_escolhido = exemplo

                if exemplo_escolhido:
                    st.session_state['_texto_para_filtros_input_pending'] = exemplo_escolhido
                    st.session_state['_texto_para_filtros_aplicar_pending'] = True
                    st.rerun()

            if aplicar_texto:
                if not texto_solicitacao.strip():
                    st.warning('Digite uma solicitação para aplicar os filtros automaticamente.')
                else:
                    catalogo_llm = {
                        'estado': opcoes_estado,
                        'regiao': opcoes_regiao,
                        'municipio': opcoes_municipio_todas,
                        'faixa_populacional': [f for f in ORDEM_FAIXA_POPULACIONAL if f in df['faixa_populacional'].unique()],
                        'acoes_estruturantes': opcoes_acao_texto,
                        'linguagem_artistica': opcoes_linguagens,
                        'faixa_receita': FAIXAS_RECEITA,
                        'tipo_ponto': opcoes_tipo,
                        'registro': opcoes_registro,
                        'filtros_booleanos': ['Sim', 'Não'],
                    }

                    with st.spinner('Analisando sua solicitação...', show_time=True):
                        resultado_llm = interpretar_solicitacao_texto(texto_solicitacao, catalogo_llm)

                    if resultado_llm['status'] == 'erro':
                        st.warning('Serviço com instabilidades no momento. Tente novamente mais tarde.')
                    elif resultado_llm['status'] == 'invalida':
                        st.warning(resultado_llm['mensagem'])
                    else:
                        filtros_llm = resultado_llm['filtros']
                        recursos_or_llm = []
                        if filtros_llm.get('rec_federal') == 'Sim':
                            recursos_or_llm.append('rec_federal')
                        if filtros_llm.get('rec_minc') == 'Sim':
                            recursos_or_llm.append('rec_minc')
                        if filtros_llm.get('rec_estadual') == 'Sim':
                            recursos_or_llm.append('rec_estadual')
                        if filtros_llm.get('rec_municipal') == 'Sim':
                            recursos_or_llm.append('rec_municipal')
                        if filtros_llm.get('pnab_estadual') == 'Sim':
                            recursos_or_llm.append('pnab_estadual')
                        if filtros_llm.get('pnab_municipal') == 'Sim':
                            recursos_or_llm.append('pnab_municipal')
                        if filtros_llm.get('tcc_est_ponto') == 'Sim':
                            recursos_or_llm.append('tcc_est_ponto')
                        if filtros_llm.get('tcc_est_pontao') == 'Sim':
                            recursos_or_llm.append('tcc_est_pontao')
                        if filtros_llm.get('tcc_mun_ponto') == 'Sim':
                            recursos_or_llm.append('tcc_mun_ponto')
                        if filtros_llm.get('tcc_mun_pontao') == 'Sim':
                            recursos_or_llm.append('tcc_mun_pontao')

                        selecao_widgets = {
                            'estado': filtros_llm['estado'],
                            'regiao': filtros_llm['regiao'],
                            'municipio': filtros_llm['municipio'],
                            'pop': filtros_llm['faixa_populacional'],
                            'acao': [
                                mapa_acao_rotulo_coluna[rotulo]
                                for rotulo in filtros_llm['acoes_estruturantes']
                                if rotulo in mapa_acao_rotulo_coluna
                            ],
                            'linguagem': filtros_llm['linguagem_artistica'],
                            'receita': filtros_llm['faixa_receita'],
                            'tipo': filtros_llm['tipo_ponto'],
                            'registro': filtros_llm['registro'],
                            'acessos_recursos_or': recursos_or_llm,
                        }

                        if selecao_widgets['estado']:
                            cidades_validas_estado = sorted(
                                df[df['estado'].isin(selecao_widgets['estado'])]['cidade'].dropna().unique()
                            )
                            selecao_widgets['municipio'] = [
                                cidade for cidade in selecao_widgets['municipio'] if cidade in cidades_validas_estado
                            ]

                        if not tem_algum_filtro(filtros_llm):
                            st.info(
                                'Não encontrei correspondência para essa solicitação com os filtros disponíveis na base atual.'
                            )
                        else:
                            st.session_state['_texto_para_filtros_pending'] = selecao_widgets
                            st.session_state['_texto_para_filtros_feedback'] = {
                                'tipo': 'success',
                                'texto': 'Solicitação aplicada com sucesso. Os filtros foram preenchidos automaticamente.',
                            }
                            st.session_state['_filtros_ui_version'] = st.session_state.get('_filtros_ui_version', 0) + 1
                            st.rerun()

        st.markdown('#### Filtros')
        col_1, col_2, col_3 = st.columns(3)

        with col_1:
            estados_preselecionados = st.session_state.get(get_key('estado'), [])
            cidades_disponiveis = df['cidade'].dropna().unique()
            if estados_preselecionados:
                cidades_disponiveis = df[df['estado'].isin(estados_preselecionados)]['cidade'].dropna().unique()
            sel_cidades = st.multiselect(
                'Município',
                options=sorted(cidades_disponiveis),
                placeholder='Todos',
                key=get_key('municipio'),
            )
            sel_estados = st.multiselect(
                'Estado',
                options=opcoes_estado,
                format_func=_rotulo_estado_sigla,
                placeholder='Todos',
                key=get_key('estado'),
            )
            sel_regiao = st.multiselect('Região', options=opcoes_regiao, placeholder='Todas', key=get_key('regiao'))

            opcoes_faixa_pop = [f for f in ORDEM_FAIXA_POPULACIONAL if f in df['faixa_populacional'].unique()]
            sel_pop = st.multiselect(
                'Faixa populacional',
                options=opcoes_faixa_pop,
                placeholder='Todas',
                key=get_key('pop'),
            )

        with col_2:
            sel_acao = st.multiselect(
                'Ação estruturante',
                options=colunas_acao,
                format_func=rotulo_acao,
                placeholder='Todas',
                key=get_key('acao'),
            )
            sel_linguagem = st.multiselect(
                'Linguagem artística',
                options=opcoes_linguagens,
                placeholder='Todas',
                key=get_key('linguagem'),
            )
            sel_receita = st.multiselect(
                'Faixa de receita anual',
                options=FAIXAS_RECEITA,
                placeholder='Todas',
                key=get_key('receita'),
            )
            sel_acessos_recursos = st.multiselect(
                'Acesso a recursos',
                options=[k for k, _ in opcoes_acessos_recursos],
                format_func=lambda k: mapa_label_recurso.get(k, k),
                placeholder='Todas',
                key=get_key('acessos_recursos_or'),
            )

        with col_3:
            sel_tipo = st.pills('Tipo de Estabelecimento', options=opcoes_tipo, selection_mode='single', key=get_key('tipo'))
            sel_registro = st.pills(
                'Cadastro jurídico',
                options=opcoes_registro,
                selection_mode='single',
                key=get_key('registro'),
                format_func=_rotulo_registro,
            )

    filtros = {
        'estado': sel_estados,
        'regiao': sel_regiao,
        'municipio': sel_cidades,
        'faixa_populacional': sel_pop,
        'tipo_ponto': [sel_tipo] if sel_tipo else [],
        'registro': [sel_registro] if sel_registro else [],
        'acoes_estruturantes': sel_acao,
        'linguagem_artistica': sel_linguagem,
        'faixa_receita': sel_receita,
        'filtros_booleanos': {},
        'acessos_recursos_or': sel_acessos_recursos,
    }

    st.session_state['filtros_globais'] = filtros

    filtrado = aplicar_filtros(df, filtros)
    count_filtros = len(filtrado)
    total_filtros = len(df)
    total_municipios_base = df['cidade'].nunique() if 'cidade' in df.columns else 0
    total_municipios_filtrados = filtrado['cidade'].nunique() if 'cidade' in filtrado.columns else 0

    with st.sidebar:
        st.header('Status da Seleção')
        st.markdown(
            """
            <style>
            .cv-chip-wrap {
                display: flex;
                flex-wrap: wrap;
                gap: 0.25rem;
                margin: 0.08rem 0 0.42rem 0;
            }
            .cv-chip-title {
                margin: 0.22rem 0 0 0;
                font-size: 0.86rem;
                font-weight: 600;
                color: #2f4664;
                line-height: 1.05rem;
            }
            .cv-chip {
                display: inline-block;
                padding: 0.08rem 0.52rem;
                border-radius: 999px;
                border: 1px solid #c9d2e0;
                background: #f2f5fa;
                color: #2f4664;
                font-size: 0.76rem;
                line-height: 1.05rem;
                white-space: nowrap;
            }
            .cv-chip-more {
                background: #e5ebf5;
                color: #334a68;
                font-weight: 600;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(_card_status('Amostra ativa', count_filtros, total_filtros), unsafe_allow_html=True)
        with c2:
            st.markdown(
                _card_status('Municípios presentes', total_municipios_filtrados, total_municipios_base),
                unsafe_allow_html=True,
            )

        if count_filtros < total_filtros:
            st.markdown('### Filtros Ativos:')

            if sel_regiao:
                _renderizar_chips_sidebar(st, 'Região', sel_regiao)
            if sel_estados:
                _renderizar_chips_sidebar(st, 'Estado', [_rotulo_estado_sigla(s) for s in sel_estados])
            if sel_cidades:
                _renderizar_chips_sidebar(st, 'Município', sel_cidades)
            if sel_pop:
                _renderizar_chips_sidebar(st, 'População', sel_pop)
            if sel_tipo:
                _renderizar_chips_sidebar(st, 'Tipo', [sel_tipo], max_itens=1)
            if sel_registro:
                _renderizar_chips_sidebar(st, 'Jurídico', [sel_registro], max_itens=1)
            if sel_acao:
                _renderizar_chips_sidebar(st, 'Ação Estruturante', [rotulo_acao(item) for item in sel_acao])
            if sel_linguagem:
                _renderizar_chips_sidebar(st, 'Linguagem', sel_linguagem)
            if sel_receita:
                _renderizar_chips_sidebar(st, 'Receita', sel_receita)

            bool_active = [mapa_label_recurso.get(chave, chave) for chave in (sel_acessos_recursos or [])]

            if bool_active:
                _renderizar_chips_sidebar(st, 'Específicos', bool_active)

        # Verificar se há qualquer filtro ativo para habilitar o reset
        any_filter_active = any([
            sel_estados, sel_regiao, sel_cidades, sel_pop, sel_acao, sel_linguagem, sel_receita,
            sel_tipo is not None,
            sel_registro is not None,
            bool(sel_acessos_recursos),
        ])

        st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
        if st.button('Resetar filtros', use_container_width=True, disabled=not any_filter_active):
            keys_reset = [k for k in st.session_state.keys() if k.startswith('input_')]
            for key in keys_reset:
                st.session_state.pop(key, None)
            st.session_state.pop('filtros_globais', None)
            st.session_state.pop('_texto_para_filtros_pending', None)
            st.session_state.pop('_texto_para_filtros_feedback', None)
            st.session_state['_filtros_ui_version'] = st.session_state.get('_filtros_ui_version', 0) + 1
            st.rerun()

    return filtros



