import html

import streamlit as st

from config import FAIXAS_RECEITA, ORDEM_FAIXA_POPULACIONAL
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

    header_text = 'Painel de Filtros'

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
            st.markdown('#### 🧪 Assistente de Filtros por Texto')
            st.caption('Escreva o recorte que deseja analisar. O assistente interpreta sua solicitação e preenche os filtros automaticamente.')
            texto_solicitacao = st.text_input(
                'Descreva o seu filtro:',
                key='texto_para_filtros_input',
                placeholder='Ex.: pontões das capitais do Nordeste com recursos federais.',
            )
            col_botao_texto, _ = st.columns([1, 4])
            aplicar_texto = col_botao_texto.button(
                'Aplicar filtros',
                key='aplicar_texto_para_filtros',
                use_container_width=True,
            )

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
                        st.error(resultado_llm['mensagem'])
                    elif resultado_llm['status'] == 'invalida':
                        st.warning(resultado_llm['mensagem'])
                    else:
                        filtros_llm = resultado_llm['filtros']
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
                            'rec_fed': filtros_llm['rec_federal'],
                            'rec_minc': filtros_llm['rec_minc'],
                            'rec_est': filtros_llm['rec_estadual'],
                            'rec_mun': filtros_llm['rec_municipal'],
                            'pnab_est': filtros_llm['pnab_estadual'],
                            'pnab_mun': filtros_llm['pnab_municipal'],
                            'tcc_est_p': filtros_llm['tcc_est_ponto'],
                            'tcc_est_pt': filtros_llm['tcc_est_pontao'],
                            'tcc_mun_p': filtros_llm['tcc_mun_ponto'],
                            'tcc_mun_pt': filtros_llm['tcc_mun_pontao'],
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

        st.markdown('#### Dados de Cadastro')
        c1, c2, c3 = st.columns(3)
        sel_estados = c1.multiselect('Estado', options=opcoes_estado, placeholder='Todos', key=get_key('estado'))

        cidades_disponiveis = df['cidade'].dropna().unique()
        if sel_estados:
            cidades_disponiveis = df[df['estado'].isin(sel_estados)]['cidade'].dropna().unique()

        sel_cidades = c1.multiselect('Município', options=sorted(cidades_disponiveis), placeholder='Todos', key=get_key('municipio'))
        sel_regiao = c3.pills('Região', options=opcoes_regiao, selection_mode='multi', key=get_key('regiao'))

        opcoes_faixa_pop = [f for f in ORDEM_FAIXA_POPULACIONAL if f in df['faixa_populacional'].unique()]
        sel_pop = c1.multiselect('Faixa populacional', options=opcoes_faixa_pop, placeholder='Todas', key=get_key('pop'))

        sel_acao = c2.multiselect('Ação estruturante', options=colunas_acao, format_func=rotulo_acao, placeholder='Todas', key=get_key('acao'))
        sel_linguagem = c2.multiselect('Linguagem artística', options=opcoes_linguagens, placeholder='Todas', key=get_key('linguagem'))
        sel_receita = c2.multiselect('Faixa de receita anual', options=FAIXAS_RECEITA, placeholder='Todas', key=get_key('receita'))

        sel_tipo = c3.pills('Tipo de reconhecimento', options=opcoes_tipo, selection_mode='single', key=get_key('tipo'))
        sel_registro = c3.pills('Cadastro jurídico', options=opcoes_registro, selection_mode='single', key=get_key('registro'))

        st.markdown('#### Acesso a Recursos')

        linha_1 = st.columns(5)
        linha_2 = st.columns(5)
        opcoes_bool = ['Sim', 'Não']

        rec_federal = linha_1[0].pills(
            'Recursos Federais',
            opcoes_bool,
            key=get_key('rec_fed'),
            help='Indica se o Ponto de Cultura acessou recursos federais nos últimos 24 meses.',
            width='stretch',
        )
        rec_minc = linha_1[1].pills(
            'Editais do Ministério da Cultura',
            opcoes_bool,
            key=get_key('rec_minc'),
            help='Indica se o Ponto de Cultura acessou editais do Ministério da Cultura (MinC).',
            width='stretch',
        )
        rec_estadual = linha_1[2].pills(
            'Recursos Estaduais',
            opcoes_bool,
            key=get_key('rec_est'),
            help='Indica se o Ponto de Cultura acessou recursos estaduais nos últimos 24 meses.',
            width='stretch',
        )
        rec_municipal = linha_1[3].pills(
            'Recursos Municipais',
            opcoes_bool,
            key=get_key('rec_mun'),
            help='Indica se o Ponto de Cultura acessou recursos municipais nos últimos 24 meses.',
            width='stretch',
        )
        pnab_estadual = linha_1[4].pills(
            'PNAB Estadual',
            opcoes_bool,
            key=get_key('pnab_est'),
            help='Indica se o Ponto de Cultura acessou editais estaduais da PNAB (Política Nacional Aldir Blanc de Fomento à Cultura).',
            width='stretch',
        )

        pnab_municipal = linha_2[0].pills(
            'PNAB Municipal',
            opcoes_bool,
            key=get_key('pnab_mun'),
            help='Indica se o Ponto de Cultura acessou editais municipais da PNAB (Política Nacional Aldir Blanc de Fomento à Cultura).',
            width='stretch',
        )
        tcc_est_ponto = linha_2[1].pills(
            'TCC Estadual (Ponto)',
            opcoes_bool,
            key=get_key('tcc_est_p'),
            help='Indica se o Ponto de Cultura acessou a modalidade TCC estadual para Ponto de Cultura.',
            width='stretch',
        )
        tcc_est_pontao = linha_2[2].pills(
            'TCC Estadual (Pontão)',
            opcoes_bool,
            key=get_key('tcc_est_pt'),
            help='Indica se o Ponto de Cultura acessou a modalidade TCC estadual para Pontão de Cultura.',
            width='stretch',
        )
        tcc_mun_ponto = linha_2[3].pills(
            'TCC Municipal (Ponto)',
            opcoes_bool,
            key=get_key('tcc_mun_p'),
            help='Indica se o Ponto de Cultura acessou a modalidade TCC municipal para Ponto de Cultura.',
            width='stretch',
        )
        tcc_mun_pontao = linha_2[4].pills(
            'TCC Municipal (Pontão)',
            opcoes_bool,
            key=get_key('tcc_mun_pt'),
            help='Indica se o Ponto de Cultura acessou a modalidade TCC municipal para Pontão de Cultura.',
            width='stretch',
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
        'filtros_booleanos': {
            'rec_federal': 'rec_federal',
            'rec_minc': 'rec_minc',
            'rec_estadual': 'rec_estadual',
            'rec_municipal': 'rec_municipal',
            'pnab_estadual': 'pnab_estadual',
            'pnab_municipal': 'pnab_municipal',
            'tcc_est_ponto': 'tcc_est_ponto',
            'tcc_est_pontao': 'tcc_est_pontao',
            'tcc_mun_ponto': 'tcc_mun_ponto',
            'tcc_mun_pontao': 'tcc_mun_pontao',
        },
        'rec_federal': rec_federal,
        'rec_minc': rec_minc,
        'rec_estadual': rec_estadual,
        'rec_municipal': rec_municipal,
        'pnab_estadual': pnab_estadual,
        'pnab_municipal': pnab_municipal,
        'tcc_est_ponto': tcc_est_ponto,
        'tcc_est_pontao': tcc_est_pontao,
        'tcc_mun_ponto': tcc_mun_ponto,
        'tcc_mun_pontao': tcc_mun_pontao,
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
                _renderizar_chips_sidebar(st, 'Estado', sel_estados)
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

            bool_active = []
            if rec_federal in ['Sim', 'Não']:
                bool_active.append(f"Recursos Federais: {rec_federal}")
            if rec_minc in ['Sim', 'Não']:
                bool_active.append(f"Editais do Ministério da Cultura: {rec_minc}")
            if rec_estadual in ['Sim', 'Não']:
                bool_active.append(f"Recursos Estaduais: {rec_estadual}")
            if rec_municipal in ['Sim', 'Não']:
                bool_active.append(f"Recursos Municipais: {rec_municipal}")
            if pnab_estadual in ['Sim', 'Não']:
                bool_active.append(f"PNAB Estadual: {pnab_estadual}")
            if pnab_municipal in ['Sim', 'Não']:
                bool_active.append(f"PNAB Municipal: {pnab_municipal}")
            if tcc_est_ponto in ['Sim', 'Não']:
                bool_active.append(f"TCC Estadual (Ponto): {tcc_est_ponto}")
            if tcc_est_pontao in ['Sim', 'Não']:
                bool_active.append(f"TCC Estadual (Pontão): {tcc_est_pontao}")
            if tcc_mun_ponto in ['Sim', 'Não']:
                bool_active.append(f"TCC Municipal (Ponto): {tcc_mun_ponto}")
            if tcc_mun_pontao in ['Sim', 'Não']:
                bool_active.append(f"TCC Municipal (Pontão): {tcc_mun_pontao}")

            if bool_active:
                _renderizar_chips_sidebar(st, 'Específicos', bool_active)

        # Verificar se há qualquer filtro ativo para habilitar o reset
        any_filter_active = any([
            sel_estados, sel_regiao, sel_cidades, sel_pop, sel_acao, sel_linguagem, sel_receita,
            sel_tipo is not None,
            sel_registro is not None,
            rec_federal in ['Sim', 'Não'],
            rec_minc in ['Sim', 'Não'],
            rec_estadual in ['Sim', 'Não'],
            rec_municipal in ['Sim', 'Não'],
            pnab_estadual in ['Sim', 'Não'],
            pnab_municipal in ['Sim', 'Não'],
            tcc_est_ponto in ['Sim', 'Não'],
            tcc_est_pontao in ['Sim', 'Não'],
            tcc_mun_ponto in ['Sim', 'Não'],
            tcc_mun_pontao in ['Sim', 'Não'],
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



