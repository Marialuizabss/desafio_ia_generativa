"""Telas do RF20: acervo, ficha, consulta, fontes e decisão do servidor.

As regras ficam em ``consulta_acervo``. Este módulo só desenha e chama o que já existe.
"""

from hashlib import sha256

import streamlit as st

try:
    from audit import registrar_decisao, registrar_execucao, traduzir_decisao
    from consulta_acervo import (
        MENSAGEM_SEM_FONTES,
        classificar_consulta,
        classificar_ficha,
        combinar_estado,
        minuta_do_atendimento,
        opcoes_de_exclusao,
        pendentes_de_indexar,
        pendentes_de_remover,
        preparar_acervo,
        resumo_do_indice,
        transicionar,
    )
except ImportError:
    from src.audit import registrar_decisao, registrar_execucao, traduzir_decisao
    from src.consulta_acervo import (
        MENSAGEM_SEM_FONTES,
        classificar_consulta,
        classificar_ficha,
        combinar_estado,
        minuta_do_atendimento,
        opcoes_de_exclusao,
        pendentes_de_indexar,
        pendentes_de_remover,
        preparar_acervo,
        resumo_do_indice,
        transicionar,
    )


AREAS = (
    ("atendimento", "Atendimento"),
    ("acervo", "Acervo"),
    ("ficha", "Ficha"),
    ("consulta", "Consulta"),
    ("fontes", "Fontes"),
    ("painel", "Painel"),
)

ROTULOS_ESTADO = {
    "pendente": "Pendente",
    "aprovada": "Aprovada",
    "rejeitada": "Rejeitada",
    "revisar": "Revisar",
}

ROTULOS_TIPO = {
    "fundamentada": "Fundamentada",
    "sem_evidencia": "Sem evidência",
    "conflito": "Conflito",
    "falha": "Falha",
    "bloqueio": "Bloqueada",
    "indice_desatualizado": "Índice desatualizado",
}


def seletor() -> str:
    """Área da barra lateral. O padrão continua sendo o atendimento do Desafio 1."""
    rotulos = dict(AREAS)
    return st.sidebar.radio(
        "Área",
        [chave for chave, _ in AREAS],
        format_func=lambda chave: rotulos[chave],
        key="rf20_area",
    )


def renderizar_area(area: str) -> None:
    if area == "acervo":
        _tela_acervo()
    elif area == "ficha":
        _tela_ficha()
    elif area == "consulta":
        _tela_consulta()
    elif area == "fontes":
        _tela_fontes()
    elif area == "painel":
        _tela_painel()


def _tela_acervo() -> None:
    st.markdown(
        """
        <header class="topo">
          <p class="selo">Acervo</p>
          <h1>Documentos institucionais</h1>
          <p class="apoio">Selecione documentos para indexar ou inclua um TXT ou PDF fictício. A indexação não chama o modelo de geração.</p>
        </header>
        """,
        unsafe_allow_html=True,
    )
    try:
        from ingestion import carregar_catalogo, validar_documentos
    except ImportError:
        from src.ingestion import carregar_catalogo, validar_documentos
    conferencia = _conferencia_do_indice()
    try:
        catalogo = carregar_catalogo()
        linhas = preparar_acervo(catalogo, validar_documentos(catalogo), conferencia)
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível ler o acervo. {erro}")
        return
    _mostrar_resumo_do_indice(conferencia)
    if not linhas:
        st.info("O catálogo não tem documentos.")
    else:
        for linha in linhas:
            st.markdown(
                f"**{linha['doc_id']}** · {linha['titulo']}\n\n"
                f"Versão: {linha['versao']} · Formato: {linha['formato']}\n\n"
                f"Hash: `{linha['sha256']}`"
            )
            if linha["aviso"]:
                st.warning(f"{linha['doc_id']}: {linha['aviso']}")
            if linha["indice"] in ("nao_indexado", "desatualizado"):
                st.warning(linha["texto_indice"])
            elif linha["indice"]:
                st.caption(linha["texto_indice"])
        _remover_do_indice(conferencia)
        _indexar_acervo(linhas, pendentes_de_indexar(conferencia))
        _excluir_ou_restaurar(linhas)
    _incluir_documento()


def _conferencia_do_indice() -> dict | None:
    """Catálogo × índice. None quando o índice não pôde ser lido."""
    try:
        from acervo_operacao import situacao_do_indice
    except ImportError:
        from src.acervo_operacao import situacao_do_indice
    try:
        return situacao_do_indice()
    except Exception:
        return None


def _mostrar_resumo_do_indice(conferencia: dict | None) -> None:
    aviso = st.session_state.pop("rf20_aviso_acervo", None)
    if aviso:
        st.success(aviso)
    derivados = st.session_state.pop("rf20_derivados", None)
    if derivados and derivados[1]:
        doc_id, arquivos = derivados
        with st.expander(f"{len(arquivos)} resultado(s) derivado(s) citam {doc_id}: revisar"):
            st.markdown("\n".join(f"- `{arquivo}`" for arquivo in arquivos))
    if conferencia is None:
        st.warning("Não foi possível ler o índice. A consulta ao acervo pode não funcionar.")
    elif conferencia["completo"]:
        st.success(resumo_do_indice(conferencia))
    else:
        st.warning(resumo_do_indice(conferencia))


def _remover_do_indice(conferencia: dict | None) -> None:
    for item in pendentes_de_remover(conferencia):
        st.warning(f"{item['doc_id']}: {item['texto']}.")
        if not st.button("Remover do índice", key=f"rf20_remover_{item['doc_id']}"):
            continue
        try:
            from acervo_operacao import remover_do_indice
        except ImportError:
            from src.acervo_operacao import remover_do_indice
        try:
            resultado = remover_do_indice(item["doc_id"])
        except ValueError as erro:
            st.error(str(erro))
            return
        except Exception:
            st.error("Não foi possível remover o documento do índice.")
            return
        st.session_state["rf20_aviso_acervo"] = (
            f"{item['doc_id']} removido do índice ({resultado['chunks_removidos']} trechos)."
        )
        st.rerun()


def _indexar_acervo(linhas: list[dict], marcados: list[str]) -> None:
    st.markdown("**Indexar**")
    ids, _ = opcoes_de_exclusao(linhas)
    escolha = st.multiselect(
        "Documentos",
        ids,
        default=[doc_id for doc_id in marcados if doc_id in ids],
        key="rf20_indexar_ids",
    )
    if st.button("Indexar selecionados", key="rf20_indexar"):
        try:
            from acervo_operacao import indexar_ids
        except ImportError:
            from src.acervo_operacao import indexar_ids
        try:
            with st.spinner("Indexando o acervo..."):
                relatorio = indexar_ids(escolha)
        except ValueError as erro:
            st.error(str(erro))
            return
        except Exception:
            st.error("Não foi possível indexar. Confira se o modelo de embeddings está disponível.")
            return
        # Recarrega a tela para o resumo e os selos já mostrarem o índice novo.
        st.session_state["rf20_relatorio_indexacao"] = relatorio
        st.rerun()
    relatorio = st.session_state.pop("rf20_relatorio_indexacao", None)
    if relatorio:
        for item in relatorio["itens"]:
            st.markdown(f"- {item['doc_id']}: {item['status']} ({item['chunks']} trechos)")
        st.success(
            f"Índice com {relatorio['total_chunks']} trechos. Versão {relatorio['versao_indice']}."
        )


def _excluir_ou_restaurar(linhas: list[dict]) -> None:
    st.markdown("**Excluir ou restaurar documento**")
    st.caption(
        "A exclusão tira o documento das consultas até ser restaurado (RF24) e fica registrada "
        "com data, motivo e responsável. A tela não tem login: o responsável é declarado."
    )
    ativos, excluidos = opcoes_de_exclusao(linhas)
    erro = st.session_state.pop("rf20_erro_exclusao", None)
    if erro:
        st.error(erro)
    if ativos:
        doc_id = st.selectbox("Documento a excluir", ativos, key="rf20_excluir_id")
        st.text_input("Servidor(a) responsável", key="rf20_excluir_responsavel")
        st.text_input("Motivo da exclusão", key="rf20_excluir_motivo")
        st.checkbox(
            f"Confirmo que {doc_id} sai das consultas até ser restaurado",
            key="rf20_excluir_confirma",
        )
        st.button("Excluir do índice", key="rf20_excluir", on_click=_ao_excluir)
    if excluidos:
        doc_id = st.selectbox("Documento a restaurar", excluidos, key="rf20_restaurar_id")
        st.text_input("Servidor(a) responsável", key="rf20_restaurar_responsavel")
        if st.button("Restaurar", key="rf20_restaurar"):
            try:
                from acervo_operacao import restaurar_pela_tela
            except ImportError:
                from src.acervo_operacao import restaurar_pela_tela
            try:
                with st.spinner(f"Restaurando e indexando {doc_id}..."):
                    resultado = restaurar_pela_tela(
                        doc_id, st.session_state.get("rf20_restaurar_responsavel") or ""
                    )
            except ValueError as erro:
                st.error(str(erro))
                return
            except Exception:
                st.error("Não foi possível restaurar. Confira se o modelo de embeddings está disponível.")
                return
            st.session_state["rf20_aviso_acervo"] = (
                f"{doc_id} restaurado e indexado ({resultado['chunks']} trechos)."
            )
            st.rerun()


def _ao_excluir() -> None:
    """Roda antes de a tela ser redesenhada: o resumo já sai atualizado e os campos limpos."""
    estado = st.session_state
    doc_id = estado.get("rf20_excluir_id")
    if not (estado.get("rf20_excluir_responsavel") or "").strip():
        estado["rf20_erro_exclusao"] = "Informe o(a) servidor(a) responsável pela exclusão."
        return
    if not (estado.get("rf20_excluir_motivo") or "").strip():
        estado["rf20_erro_exclusao"] = "Informe o motivo da exclusão."
        return
    if not estado.get("rf20_excluir_confirma"):
        estado["rf20_erro_exclusao"] = f"Marque a confirmação para excluir {doc_id}."
        return
    try:
        from acervo_operacao import excluir_pela_tela
    except ImportError:
        from src.acervo_operacao import excluir_pela_tela
    try:
        resultado = excluir_pela_tela(
            doc_id, estado["rf20_excluir_motivo"], estado["rf20_excluir_responsavel"]
        )
    except ValueError as erro:
        estado["rf20_erro_exclusao"] = str(erro)
        return
    except Exception:
        estado["rf20_erro_exclusao"] = "Não foi possível excluir o documento."
        return
    estado["rf20_aviso_acervo"] = (
        f"{doc_id} excluído do índice ({resultado['chunks_removidos']} trechos removidos)."
    )
    estado["rf20_derivados"] = (doc_id, resultado["derivados_a_revisar"])
    estado["rf20_excluir_motivo"] = ""
    estado["rf20_excluir_confirma"] = False


def _incluir_documento() -> None:
    st.markdown("**Incluir documento**")
    st.caption("O arquivo entra no catálogo como documento fictício da equipe e pode ser indexado em seguida.")
    st.text_input("Título", key="rf20_novo_titulo")
    st.text_input("Versão", key="rf20_nova_versao")
    arquivo = st.file_uploader("TXT ou PDF", type=["txt", "pdf"], key="rf20_novo_arquivo")
    if st.button("Incluir no acervo", key="rf20_incluir"):
        if arquivo is None:
            st.error("Escolha um arquivo TXT ou PDF.")
            return
        try:
            from acervo_operacao import incluir_no_acervo, indexar_ids
        except ImportError:
            from src.acervo_operacao import incluir_no_acervo, indexar_ids
        try:
            documento = incluir_no_acervo(
                arquivo.getvalue(),
                arquivo.name,
                st.session_state.get("rf20_novo_titulo") or "",
                st.session_state.get("rf20_nova_versao") or "",
            )
            with st.spinner("Indexando o documento incluído..."):
                relatorio = indexar_ids([documento["doc_id"]])
        except ValueError as erro:
            st.error(str(erro))
            return
        except Exception:
            st.error("O documento foi conferido, mas a indexação não concluiu.")
            return
        st.success(f"{documento['doc_id']} entrou no acervo e na indexação.")
        for item in relatorio["itens"]:
            st.markdown(f"- {item['doc_id']}: {item['status']} ({item['chunks']} trechos)")


def _tela_ficha() -> None:
    st.markdown(
        """
        <header class="topo">
          <p class="selo">Ficha</p>
          <h1>Compreensão da solicitação</h1>
          <p class="apoio">Ausência aparece como "não localizado". A análise só roda ao pedir.</p>
        </header>
        """,
        unsafe_allow_html=True,
    )
    st.text_area("Texto da solicitação", key="rf20_texto_ficha", height=160)
    if st.button("Analisar solicitação", key="rf20_analisar"):
        with st.spinner("Analisando a solicitação..."):
            _executar_ficha()
    classificacao = st.session_state.get("rf20_ficha_classificacao")
    if classificacao:
        _mostrar_ficha(classificacao)
    _formulario_decisao()


def _tela_consulta() -> None:
    st.markdown(
        """
        <header class="topo">
          <p class="selo">Consulta</p>
          <h1>Pergunta ao acervo</h1>
          <p class="apoio">A resposta só aparece quando o acervo a sustenta.</p>
        </header>
        """,
        unsafe_allow_html=True,
    )
    st.text_area("Pergunta", key="rf20_pergunta", height=120)
    if st.button("Consultar o acervo", key="rf20_consultar"):
        # Cada consulta recarrega o modelo de embeddings; sem aviso, parecia travada.
        with st.spinner("Consultando o acervo... Cada consulta leva alguns segundos."):
            _executar_consulta()
    classificacao = st.session_state.get("rf20_consulta_classificacao")
    if classificacao:
        _mostrar_consulta(classificacao)
    _formulario_decisao()


def _tela_fontes() -> None:
    st.markdown(
        """
        <header class="topo">
          <p class="selo">Fontes</p>
          <h1>Trechos citados</h1>
          <p class="apoio">O que a última consulta usou para responder.</p>
        </header>
        """,
        unsafe_allow_html=True,
    )
    classificacao = st.session_state.get("rf20_consulta_classificacao")
    if not classificacao:
        st.info(MENSAGEM_SEM_FONTES)
        return
    fontes = classificacao.get("fontes") or []
    if not fontes:
        st.info("Esta consulta não trouxe fontes.")
        if classificacao.get("texto"):
            _mostrar_mensagem(classificacao)
        return
    for fonte in fontes:
        local = _local_da_fonte(fonte)
        st.markdown(
            f"**{fonte.get('doc_id', 'documento')}** · {fonte.get('titulo', '')}\n\n"
            f"Versão: {fonte.get('versao') or 'não informada'} · {local}\n\n"
            f"Trecho `{fonte.get('chunk_id', '')}`"
        )
        trecho = fonte.get("trecho_citado") or fonte.get("trecho") or ""
        if trecho:
            st.markdown(f"> {trecho}")


def _executar_ficha() -> None:
    texto = (st.session_state.get("rf20_texto_ficha") or "").strip()
    if not texto:
        st.session_state["rf20_ficha_classificacao"] = _aviso_local(
            "Informe o texto da solicitação."
        )
        return
    try:
        try:
            from nlp import analisar_solicitacao
        except ImportError:
            from src.nlp import analisar_solicitacao
        analise = analisar_solicitacao(texto, "texto-da-ficha")
        classificacao = classificar_ficha(analise.validacao, analise.guardrail)
    except Exception as erro:
        classificacao = classificar_ficha(None)
        classificacao["texto"] = f"{classificacao['texto']} {erro}".strip()
    st.session_state["rf20_ficha_classificacao"] = classificacao
    st.session_state["rf20_travado"] = False
    _aplicar_estado("ficha", classificacao)


def _executar_consulta() -> None:
    pergunta = (st.session_state.get("rf20_pergunta") or "").strip()
    if not pergunta:
        st.session_state["rf20_consulta_resultado"] = None
        st.session_state["rf20_consulta_classificacao"] = _aviso_local("Informe a pergunta.")
        return
    resultado = None
    try:
        try:
            from rf19_complemento import responder_rf19
        except ImportError:
            from src.rf19_complemento import responder_rf19
        resultado = responder_rf19(pergunta)
        classificacao = classificar_consulta(resultado=resultado)
    except Exception as erro:
        classificacao = classificar_consulta(erro=erro)
    st.session_state["rf20_consulta_resultado"] = resultado
    st.session_state["rf20_consulta_classificacao"] = classificacao
    if isinstance(resultado, dict) and resultado.get("id_consulta"):
        st.session_state["rf20_id_consulta"] = resultado["id_consulta"]
    st.session_state["rf20_travado"] = False
    _aplicar_estado("consulta", classificacao)


def _mostrar_ficha(classificacao: dict) -> None:
    _mostrar_mensagem(classificacao)
    if classificacao.get("motivos"):
        st.markdown("**Motivos**")
        for motivo in classificacao["motivos"]:
            st.markdown(f"- {motivo}")
    linhas = classificacao.get("linhas")
    if not linhas:
        return
    st.markdown(f"**Categoria:** {linhas['categoria']}")
    st.markdown(f"**Resumo:** {linhas['resumo']}")
    itens = "".join(f"<dt>{rotulo}</dt><dd>{valor}</dd>" for rotulo, valor in linhas["campos"])
    st.markdown(f'<dl class="ficha">{itens}</dl>', unsafe_allow_html=True)
    if linhas["entidades"]:
        st.markdown("**Entidades**")
        for entidade in linhas["entidades"]:
            st.markdown(f"- {entidade['tipo']}: {entidade['texto']} ({entidade['origem']})")
    _mostrar_minuta(classificacao)


def _mostrar_consulta(classificacao: dict) -> None:
    tipo = ROTULOS_TIPO.get(classificacao["tipo"], classificacao["tipo"])
    st.markdown(f"**Status:** {tipo}")
    _mostrar_mensagem(classificacao)
    if classificacao.get("resposta"):
        st.markdown(classificacao["resposta"])
    if classificacao.get("justificativa"):
        st.markdown(f"**Justificativa:** {classificacao['justificativa']}")
    ficha = st.session_state.get("rf20_ficha_classificacao")
    if ficha:
        _mostrar_minuta(ficha)


def _mostrar_minuta(ficha: dict) -> None:
    consulta = st.session_state.get("rf20_consulta_classificacao")
    minuta = minuta_do_atendimento(ficha, consulta)
    st.markdown("**Minuta**")
    st.markdown(minuta["texto"])
    st.caption("Nenhuma resposta é enviada automaticamente.")


def _tela_painel() -> None:
    st.markdown(
        """
        <header class="topo">
          <p class="selo">Painel</p>
          <h1>Sentimentos das avaliações</h1>
          <p class="apoio">Os totais são contados pelo código. A confiança do modelo não entra no percentual.</p>
        </header>
        """,
        unsafe_allow_html=True,
    )
    try:
        from painel import carregar_ultima_execucao, ler_avaliacoes, montar_visao
    except ImportError:
        from src.painel import carregar_ultima_execucao, ler_avaliacoes, montar_visao

    resumo, classificacoes = carregar_ultima_execucao()
    if resumo is None:
        st.info("Ainda não há classificação das avaliações. O painel fica sem dados.")
        painel = montar_visao([], [], None)
        _mostrar_painel(painel, None)
        return

    modo = "simulada" if resumo.get("simulado") else "real"
    st.caption(f"Execução {modo}: {resumo.get('pasta', '')}. A confiança é estimativa não calibrada.")
    conjunto = st.selectbox(
        "Conjunto",
        ["oficiais", "duplicadas"],
        format_func=lambda valor: "12 avaliações" if valor == "oficiais" else "Com duplicata",
        key="rf20_conjunto",
    )
    canal = st.selectbox(
        "Canal",
        ["todos", "presencial", "telefone", "e-mail", "whatsapp"],
        key="rf20_canal",
    )
    filtro = None if canal == "todos" else {"canal": canal}
    painel = montar_visao(classificacoes, ler_avaliacoes(conjunto), filtro)
    acuracia = resumo.get("acuracia_polaridade") if conjunto == "oficiais" and canal == "todos" else None
    _mostrar_painel(painel, acuracia)


def _mostrar_painel(painel: dict, acuracia: dict | None) -> None:
    st.markdown(
        f"Registros lidos: {painel['registros']} · únicos: {painel['unicos']} · "
        f"duplicados: {', '.join(painel['duplicados']) or '—'}"
    )
    st.markdown(f"**Denominador:** {painel['denominador']}")
    st.markdown(f"Rejeitadas (fora dos totais): {painel['rejeitadas']} · Revisão: {painel['revisao']}")
    if painel["mensagem"]:
        st.info(painel["mensagem"])
        return
    for polaridade in ("positiva", "negativa", "neutra", "indeterminada"):
        st.markdown(
            f"- {polaridade}: {painel['totais'][polaridade]} "
            f"({painel['fracoes'][polaridade]}, {painel['percentuais'][polaridade]}%)"
        )
    _grafico_de_barras(painel)
    if acuracia:
        st.markdown(
            f"**Acurácia da polaridade:** {acuracia['numerador']}/{acuracia['denominador']}"
        )


def _grafico_de_barras(painel: dict) -> None:
    """Barras em HTML. O gráfico do Streamlit depende de uma biblioteca que falha neste Python."""
    maior = max(painel["totais"].values()) or 1
    barras = ['<div class="grafico-painel">']
    for polaridade in ("positiva", "negativa", "neutra", "indeterminada"):
        total = painel["totais"][polaridade]
        largura = round(100 * total / maior)
        barras.append(
            f'<p class="grafico-rotulo">{polaridade}: {total}</p>'
            f'<div class="grafico-trilho"><div class="grafico-barra" style="width:{largura}%"></div></div>'
        )
    barras.append("</div>")
    st.markdown(
        """
        <style>
          .grafico-rotulo { margin: 0.55rem 0 0.15rem; font-size: 0.85rem; }
          .grafico-trilho { background: #E7E2D6; border-radius: 6px; height: 14px; }
          .grafico-barra { background: #165C3F; border-radius: 6px; height: 14px; }
        </style>
        """ + "".join(barras),
        unsafe_allow_html=True,
    )


def _aviso_local(texto: str) -> dict:
    """Erro de preenchimento: mostra a mensagem e não abre atendimento."""
    return {
        "tipo": "falha",
        "texto": texto,
        "estado": None,
        "resposta": None,
        "fontes": [],
        "justificativa": "",
        "motivos": [],
    }


def _mostrar_mensagem(classificacao: dict) -> None:
    texto = classificacao.get("texto") or ""
    if not texto:
        return
    if classificacao["tipo"] in {"falha", "indice_desatualizado", "bloqueio"}:
        st.error(texto)
    elif classificacao["tipo"] in {"sem_evidencia", "conflito", "revisar"}:
        st.warning(texto)
    else:
        st.info(texto)


def _formulario_decisao() -> None:
    estado = st.session_state.get("rf20_estado")
    if st.session_state.get("rf20_bloqueado"):
        st.caption("A entrada foi bloqueada. Não há resposta para aprovar.")
        return
    if not estado and not _id_atual():
        return
    st.markdown('<p class="rotulo">Decisão do servidor</p>', unsafe_allow_html=True)
    if estado:
        st.markdown(f"**Estado:** {ROTULOS_ESTADO.get(estado, traduzir_decisao(estado))}")
    if estado in {"aprovada", "rejeitada"}:
        st.caption("Este atendimento está encerrado. A decisão registrada não é alterada.")
        return
    st.text_input("Servidor(a) responsável", key="rf20_revisor")
    st.text_input("Cargo / Setor", key="rf20_cargo")
    st.text_area("Justificativa", key="rf20_justificativa", height=80)
    aprovar, rejeitar, revisar = st.columns(3)
    with aprovar:
        st.button("Aprovar", key="rf20_aprovar", on_click=_decidir, args=("aprovar",))
    with rejeitar:
        st.button("Rejeitar", key="rf20_rejeitar", on_click=_decidir, args=("rejeitar",))
    with revisar:
        st.button("Pedir revisão", key="rf20_revisar", on_click=_decidir, args=("revisar",))
    if estado == "revisar":
        st.button("Retomar como pendente", key="rf20_retomar", on_click=_decidir, args=("retomar",))
    erro = st.session_state.get("rf20_decisao_erro")
    if erro:
        st.error(erro)


def _decidir(acao: str) -> None:
    try:
        novo = transicionar(
            st.session_state.get("rf20_estado"),
            acao,
            st.session_state.get("rf20_justificativa") or "",
            st.session_state.get("rf20_revisor") or "",
            st.session_state.get("rf20_cargo") or "",
        )
        id_execucao = _id_atual()
        if not id_execucao:
            raise ValueError("A execução avaliada não foi identificada.")
        registrar_decisao(
            id_execucao,
            novo,
            justificativa=st.session_state.get("rf20_justificativa") or "",
            revisor=st.session_state.get("rf20_revisor") or "",
            cargo_setor=st.session_state.get("rf20_cargo") or "",
        )
    except ValueError as erro:
        st.session_state["rf20_decisao_erro"] = str(erro)
        return
    st.session_state["rf20_estado"] = novo
    st.session_state["rf20_travado"] = True
    st.session_state["rf20_decisao_erro"] = None


def _aplicar_estado(origem: str, classificacao: dict) -> None:
    if classificacao.get("tipo") == "bloqueio":
        st.session_state["rf20_bloqueado"] = True
        if not st.session_state.get("rf20_travado") and st.session_state.get("rf20_estado") not in {
            "aprovada", "rejeitada",
        }:
            st.session_state["rf20_estado"] = None
        return
    st.session_state["rf20_bloqueado"] = False
    novo = classificacao.get("estado")
    combinado = combinar_estado(
        st.session_state.get("rf20_estado"),
        novo,
        travado=bool(st.session_state.get("rf20_travado")),
    )
    st.session_state["rf20_estado"] = combinado
    if combinado not in {"pendente", "revisar"}:
        return
    id_execucao = _id_para(origem)
    justificativa = ""
    if combinado == "revisar":
        motivos = classificacao.get("motivos") or []
        justificativa = classificacao.get("justificativa") or classificacao.get("texto") or ""
        if motivos:
            justificativa = "; ".join(motivos)
        justificativa = justificativa.strip() or "Encaminhado para revisão."
    marca = (id_execucao, combinado, origem)
    if st.session_state.get("rf20_auto") == marca:
        return
    registrar_decisao(id_execucao, combinado, justificativa=justificativa)
    st.session_state["rf20_auto"] = marca


def _id_para(origem: str) -> str:
    if origem == "consulta" and st.session_state.get("rf20_id_consulta"):
        return st.session_state["rf20_id_consulta"]
    if st.session_state.get("rf20_id_ficha"):
        return st.session_state["rf20_id_ficha"]
    texto = st.session_state.get("rf20_texto_ficha") or st.session_state.get("rf20_pergunta") or ""
    novo = registrar_execucao({
        "origem": "rf20",
        "etapa": origem,
        "sha256_texto": sha256(texto.encode("utf-8")).hexdigest(),
    })
    st.session_state["rf20_id_ficha"] = novo
    return novo


def _id_atual() -> str | None:
    return st.session_state.get("rf20_id_consulta") or st.session_state.get("rf20_id_ficha")


def _local_da_fonte(fonte: dict) -> str:
    if fonte.get("pagina"):
        return f"página {fonte['pagina']}"
    if fonte.get("secao"):
        return f"seção {fonte['secao']}"
    return "sem página"
