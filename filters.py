import streamlit as st

from config import FAIXAS_RECEITA, ORDEM_FAIXA_POPULACIONAL
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


def renderizar_painel_filtros(df):
    """
    Renderiza o painel de filtros e salva em st.session_state['filtros_globais'].
    Também exibe um resumo da seleção na barra lateral.
    """

    ui_version = st.session_state.get('_filtros_ui_version', 0)

    def get_key(base):
        return f'input_{ui_version}_{base}'

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

        c1, c2, c3 = st.columns(3)
        sel_estados = c1.multiselect('Estado', options=sorted(df['estado'].dropna().unique()), placeholder='Todos', key=get_key('estado'))

        cidades_disponiveis = df['cidade'].dropna().unique()
        if sel_estados:
            cidades_disponiveis = df[df['estado'].isin(sel_estados)]['cidade'].dropna().unique()

        sel_cidades = c1.multiselect('Município', options=sorted(cidades_disponiveis), placeholder='Todos', key=get_key('municipio'))
        sel_regiao = c3.pills('Região', options=sorted(df['regiao'].dropna().unique()), selection_mode='multi', key=get_key('regiao'))

        opcoes_faixa_pop = [f for f in ORDEM_FAIXA_POPULACIONAL if f in df['faixa_populacional'].unique()]
        sel_pop = c1.multiselect('Faixa populacional', options=opcoes_faixa_pop, placeholder='Todas', key=get_key('pop'))

        sel_acao = c2.multiselect('Ação estruturante', options=colunas_acao, format_func=rotulo_acao, placeholder='Todas', key=get_key('acao'))
        sel_linguagem = c2.multiselect('Linguagem artística', options=opcoes_linguagens, placeholder='Todas', key=get_key('linguagem'))
        sel_receita = c2.multiselect('Faixa de receita anual', options=FAIXAS_RECEITA, placeholder='Todas', key=get_key('receita'))

        sel_tipo = c3.pills('Tipo de reconhecimento', options=sorted(df['tipo_ponto'].dropna().unique()), selection_mode='single', key=get_key('tipo'))
        sel_registro = c3.pills('Cadastro jurídico', options=sorted(df['registro'].dropna().unique()), selection_mode='single', key=get_key('registro'))

        st.markdown('---')
        st.caption('Filtros Específicos')

        b1, b2, b3, b4, b5, b6, b7, b8, b9, b10 = st.columns(10)
        rec_federal = b1.pills('Rec. Federal', ['Sim', 'Não'], key=get_key('rec_fed'))
        rec_minc = b2.pills('Rec. MinC', ['Sim', 'Não'], key=get_key('rec_minc'))
        rec_estadual = b3.pills('Rec. Estadual', ['Sim', 'Não'], key=get_key('rec_est'))
        rec_municipal = b4.pills('Rec. Municipal', ['Sim', 'Não'], key=get_key('rec_mun'))
        pnab_estadual = b5.pills('PNAB Est.', ['Sim', 'Não'], key=get_key('pnab_est'))
        pnab_municipal = b6.pills('PNAB Mun.', ['Sim', 'Não'], key=get_key('pnab_mun'))
        tcc_est_ponto = b7.pills('TCC Est. Ponto', ['Sim', 'Não'], key=get_key('tcc_est_p'))
        tcc_est_pontao = b8.pills('TCC Est. Pontão', ['Sim', 'Não'], key=get_key('tcc_est_pt'))
        tcc_mun_ponto = b9.pills('TCC Mun. Ponto', ['Sim', 'Não'], key=get_key('tcc_mun_p'))
        tcc_mun_pontao = b10.pills('TCC Mun. Pontão', ['Sim', 'Não'], key=get_key('tcc_mun_pt'))

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
                st.write(f"**Região:** {', '.join(sel_regiao)}")
            if sel_estados:
                st.write(f"**Estado:** {', '.join(sel_estados)}")
            if sel_cidades:
                st.write(f'**Município:** {len(sel_cidades)} cidades selecionadas')
            if sel_pop:
                st.write(f'**População:** {len(sel_pop)} faixas')
            if sel_tipo:
                st.write(f'**Tipo:** {sel_tipo}')
            if sel_registro:
                st.write(f'**Jurídico:** {sel_registro}')
            if sel_acao:
                st.write(f'**Ação Estruturante:** {len(sel_acao)} selec.')
            if sel_linguagem:
                st.write(f'**Linguagem:** {len(sel_linguagem)} selec.')
            if sel_receita:
                st.write(f'**Receita:** {len(sel_receita)} faixas')

            bool_active = []
            if rec_federal in ['Sim', 'Não']:
                bool_active.append(f"Rec. Federal: {rec_federal}")
            if rec_minc in ['Sim', 'Não']:
                bool_active.append(f"Rec. MinC: {rec_minc}")
            if rec_estadual in ['Sim', 'Não']:
                bool_active.append(f"Rec. Estadual: {rec_estadual}")
            if rec_municipal in ['Sim', 'Não']:
                bool_active.append(f"Rec. Municipal: {rec_municipal}")
            if pnab_estadual in ['Sim', 'Não']:
                bool_active.append(f"PNAB Est.: {pnab_estadual}")
            if pnab_municipal in ['Sim', 'Não']:
                bool_active.append(f"PNAB Mun.: {pnab_municipal}")
            if tcc_est_ponto in ['Sim', 'Não']:
                bool_active.append(f"TCC Est. Ponto: {tcc_est_ponto}")
            if tcc_est_pontao in ['Sim', 'Não']:
                bool_active.append(f"TCC Est. Pontão: {tcc_est_pontao}")
            if tcc_mun_ponto in ['Sim', 'Não']:
                bool_active.append(f"TCC Mun. Ponto: {tcc_mun_ponto}")
            if tcc_mun_pontao in ['Sim', 'Não']:
                bool_active.append(f"TCC Mun. Pontão: {tcc_mun_pontao}")

            if bool_active:
                st.write("**Específicos:**")
                for item in bool_active:
                    st.write(f"- {item}")

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

        if st.button('Resetar filtros', use_container_width=True, disabled=not any_filter_active):
            keys_reset = [k for k in st.session_state.keys() if k.startswith('input_')]
            for key in keys_reset:
                st.session_state.pop(key, None)
            st.session_state.pop('filtros_globais', None)
            st.session_state['_filtros_ui_version'] = st.session_state.get('_filtros_ui_version', 0) + 1
            st.rerun()

    return filtros
