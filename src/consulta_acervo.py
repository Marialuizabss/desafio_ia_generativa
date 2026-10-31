"""RF20 — regras das telas de acervo, consulta, ficha e fontes.

Sem Streamlit e sem chamada ao modelo. A interface só exibe o que este módulo devolve.
"""

from src.schemas import CAMPOS_ANULAVEIS, para_exibicao

STATUS_FUNDAMENTADA = "fundamentada"
STATUS_SEM_EVIDENCIA = "sem_evidencia"
STATUS_CONFLITO = "conflito"


ESTADOS_ABERTOS = ("pendente", "revisar")
ESTADOS_FINAIS = ("aprovada", "rejeitada")

MENSAGEM_INDICE = "O índice está desatualizado. Reindexe o acervo antes de consultar."
MENSAGEM_SEM_EVIDENCIA = "Não há evidências suficientes para responder com segurança."
MENSAGEM_CONFLITO = "Há informações documentais divergentes. É necessária revisão humana."
MENSAGEM_SEM_FONTES = "Ainda não há fontes: faça uma consulta ao acervo."
MENSAGEM_MINUTA_BLOQUEADA = (
    "A minuta não será montada. A ficha ficou incompleta ou incoerente e o caso vai para revisão."
)
MENSAGEM_MINUTA_SEM_FICHA = "Analise a solicitação para montar a minuta."
MENSAGEM_ORIENTACAO_PENDENTE = (
    "As orientações institucionais ainda não foram consultadas no acervo. "
    "Nenhum documento, prazo ou local foi preenchido."
)
MARCA_ORIENTACOES = "**Orientações**"
MARCA_CIENCIA = "**Ciência das regras de matrícula**"
MENSAGEM_FALHA = "Não foi possível concluir a operação."
MENSAGEM_FALHA_INESPERADA = "Não foi possível consultar o acervo agora. Tente de novo em instantes."
JUSTIFICATIVA_FALHA_INESPERADA = "Falha técnica na consulta. O detalhe está no registro da consulta."
MENSAGEM_BLOQUEIO = "A entrada foi bloqueada."

MENSAGENS_BLOQUEIO = {
    "entrada_vazia": "A entrada está vazia.",
    "tipo_nao_aceito": "O tipo do arquivo não é aceito.",
    "tamanho_excedido": "O arquivo passa do tamanho permitido.",
    "texto_longo": "O texto passa do limite de caracteres.",
    "pedido_segredo": "O pedido tenta obter um segredo e foi bloqueado.",
    "saida_com_segredo": "A resposta foi bloqueada porque trazia um segredo.",
    "teto_chamadas": "O limite de chamadas deste atendimento foi atingido.",
    "teto_tokens": "O limite de tokens deste atendimento foi atingido.",
    "instrucao_na_entrada": "A entrada contém uma instrução ao sistema e segue para revisão.",
}

AVISOS_ACERVO = {
    "arquivo_ausente": "Arquivo ausente no acervo.",
    "hash_divergente": "O hash do arquivo não confere com o catálogo.",
}

# Situação de cada documento na conferência catálogo × índice (vector_store.conferir_indice).
SITUACOES_INDICE = {
    "indexado": "indexado",
    "nao_indexado": "não indexado",
    "desatualizado": "desatualizado: o documento mudou depois da indexação",
    "excluido": "excluído do índice",
    "excluido_no_indice": "excluído, mas continua no índice",
    "fora_do_catalogo": "está no índice, mas não no catálogo",
}
SITUACOES_A_INDEXAR = ("nao_indexado", "desatualizado")
SITUACOES_A_REMOVER = ("fora_do_catalogo", "excluido_no_indice")

ROTULOS_CAMPOS = {
    "protocolo": "Protocolo",
    "data_solicitacao": "Data da solicitação",
    "solicitante": "Solicitante",
    "assunto": "Assunto",
    "pedido": "Pedido",
    "curso": "Curso",
    "eixo": "Eixo",
    "carga_horaria": "Carga horária",
    "turno": "Turno",
    "data_inicio": "Data de início",
    "regras_ciencia": "Ciência das regras",
}

ROTULOS_ENTIDADES = {
    "pessoas": "Pessoas",
    "orgaos": "Órgãos",
    "locais": "Locais",
    "datas": "Datas",
    "protocolos": "Protocolos",
}


def preparar_acervo(
    catalogo: dict, validacoes: list[dict], conferencia: dict | None = None
) -> list[dict]:
    """Junta o catálogo com a conferência de arquivo e hash e, se houver, com a do índice."""
    por_id = {item["doc_id"]: item["status"] for item in validacoes}
    no_indice = {
        item["doc_id"]: item for item in (conferencia or {}).get("documentos", [])
    }
    linhas = []
    for documento in catalogo.get("documentos", []):
        status = por_id.get(documento["doc_id"], "nao_conferido")
        indice = no_indice.get(documento["doc_id"])
        linhas.append({
            "doc_id": documento["doc_id"],
            "titulo": documento.get("titulo") or "",
            "versao": documento.get("versao") or "",
            "formato": documento.get("formato") or "",
            "sha256": documento.get("sha256") or "",
            "status": status,
            "aviso": AVISOS_ACERVO.get(status),
            "indice": indice["situacao"] if indice else None,
            "texto_indice": _texto_do_indice(indice),
        })
    return linhas


def _texto_do_indice(item: dict | None) -> str:
    if not item:
        return ""
    texto = f"Índice: {SITUACOES_INDICE.get(item['situacao'], item['situacao'])}"
    if item["situacao"] == "indexado":
        texto += f" ({item['chunks']} trechos)"
    return texto


def resumo_do_indice(conferencia: dict) -> str:
    """Uma linha para o topo da tela Acervo."""
    documentos = conferencia["documentos"]
    no_catalogo = [d for d in documentos if d["situacao"] != "fora_do_catalogo"]
    ativos = [d for d in no_catalogo if d["situacao"] not in ("excluido", "excluido_no_indice")]
    indexados = sum(d["situacao"] == "indexado" for d in ativos)
    excluidos = len(no_catalogo) - len(ativos)

    if conferencia["completo"]:
        texto = (
            f"Índice: {conferencia['total_chunks']} trechos · "
            f"{indexados} de {len(ativos)} documentos indexados"
        )
        return texto + (f" · {excluidos} excluído(s)" if excluidos else "")
    if conferencia["vazio"]:
        return (
            'Índice vazio: nenhum documento indexado. Use "Indexar selecionados" abaixo; '
            "os documentos pendentes já vêm marcados."
        )
    return (
        f"Índice incompleto: {len(conferencia['pendencias'])} pendência(s). "
        "A consulta ao acervo fica bloqueada até resolver."
    )


def pendentes_de_indexar(conferencia: dict | None) -> list[str]:
    """Documentos que já vêm marcados em "Indexar selecionados"."""
    return [
        item["doc_id"]
        for item in (conferencia or {}).get("pendencias", [])
        if item["situacao"] in SITUACOES_A_INDEXAR
    ]


def pendentes_de_remover(conferencia: dict | None) -> list[dict]:
    """Documentos que ganham o botão "Remover do índice"."""
    return [
        {"doc_id": item["doc_id"], "texto": SITUACOES_INDICE[item["situacao"]]}
        for item in (conferencia or {}).get("pendencias", [])
        if item["situacao"] in SITUACOES_A_REMOVER
    ]


def classificar_consulta(resultado: dict | None = None, erro: BaseException | None = None) -> dict:
    """Traduz o retorno do RAG, ou a falha, na mensagem e no estado da tela.

    Índice desatualizado e falha não trazem resposta. Sem evidência e conflito
    encaminham para revisão. Resposta fundamentada fica pendente do servidor.
    Só ``ValueError`` (como a falha do provedor) traz mensagem para o usuário; outro
    erro é interno e o detalhe técnico fica só no registro da consulta.
    """
    if erro is not None:
        if type(erro).__name__ == "IndiceIncompletoError":
            # A mensagem já diz o que falta e o que fazer; não há resposta para decidir.
            return _consulta("indice_desatualizado", str(erro), None, None, [], "")
        if type(erro).__name__ == "IndiceDesatualizadoError":
            return _consulta("indice_desatualizado", MENSAGEM_INDICE, None, None, [], "")
        if not isinstance(erro, ValueError):
            return _consulta(
                "falha", MENSAGEM_FALHA_INESPERADA, "revisar", None, [],
                JUSTIFICATIVA_FALHA_INESPERADA,
            )
        motivo = str(erro).strip() or MENSAGEM_FALHA
        return _consulta("falha", f"{MENSAGEM_FALHA} {motivo}", "revisar", None, [], motivo)

    if not isinstance(resultado, dict):
        return _consulta(
            "falha",
            f"{MENSAGEM_FALHA} A consulta não devolveu resultado.",
            "revisar",
            None,
            [],
            "",
        )

    if resultado.get("decisao") == "bloquear":
        return _consulta(
            "bloqueio",
            mensagem_de_bloqueio(resultado.get("motivos_guardrail")),
            None,
            None,
            [],
            "",
        )

    status = resultado.get("status")
    fontes = list(resultado.get("fontes") or [])
    justificativa = _texto(resultado.get("justificativa"))
    resposta = _texto(resultado.get("resposta"))

    if status == STATUS_SEM_EVIDENCIA:
        return _consulta(
            "sem_evidencia",
            resposta or MENSAGEM_SEM_EVIDENCIA,
            "revisar",
            None,
            fontes,
            justificativa,
        )
    if status == STATUS_CONFLITO:
        return _consulta(
            "conflito",
            resposta or MENSAGEM_CONFLITO,
            "revisar",
            None,
            fontes,
            justificativa,
        )
    if status == STATUS_FUNDAMENTADA and resultado.get("decisao") == "responder":
        return _consulta("fundamentada", resposta, "pendente", resposta, fontes, justificativa)
    if status == STATUS_FUNDAMENTADA:
        return _consulta("fundamentada", resposta, "revisar", resposta, fontes, justificativa)
    return _consulta(
        "falha",
        f"{MENSAGEM_FALHA} Status desconhecido.",
        "revisar",
        None,
        fontes,
        justificativa,
    )


def mensagem_de_bloqueio(motivos) -> str:
    """Traduz os códigos do guardrail. O trecho casado não entra na frase."""
    textos = []
    for codigo in motivos or []:
        texto = MENSAGENS_BLOQUEIO.get(str(codigo))
        if texto and texto not in textos:
            textos.append(texto)
    return " ".join(textos) if textos else MENSAGEM_BLOQUEIO


def classificar_ficha(validacao, guardrail=None) -> dict:
    """Estado da ficha a partir da validação do RF14, sem montar minuta aqui.

    ``guardrail`` é a decisão do RF16. Bloqueio não vira revisão: não há
    resposta para o servidor aprovar.
    """
    if _decisao(guardrail) == "bloquear":
        return {
            "tipo": "bloqueio",
            "texto": mensagem_de_bloqueio(_motivos(guardrail)),
            "estado": None,
            "motivos": list(_motivos(guardrail)),
            "minuta_bloqueada": True,
            "linhas": None,
        }

    if validacao is None:
        return {
            "tipo": "falha",
            "texto": f"{MENSAGEM_FALHA} A análise não devolveu ficha.",
            "estado": "revisar",
            "motivos": [],
            "minuta_bloqueada": True,
            "linhas": None,
        }

    motivos = [str(motivo) for motivo in getattr(validacao, "motivos", [])]
    if _decisao(guardrail) == "revisar":
        aviso = mensagem_de_bloqueio(_motivos(guardrail))
        if aviso != MENSAGEM_BLOQUEIO and aviso not in motivos:
            motivos.insert(0, aviso)
    solicitacao = getattr(validacao, "solicitacao", None)
    linhas = linhas_da_ficha(solicitacao) if solicitacao is not None else None
    bloqueada = bool(getattr(validacao, "minuta_bloqueada", False))

    if bloqueada or getattr(validacao, "decisao", None) == "rejeitada":
        return {
            "tipo": "revisar",
            "texto": MENSAGEM_MINUTA_BLOQUEADA,
            "estado": "revisar",
            "motivos": motivos,
            "minuta_bloqueada": True,
            "linhas": linhas,
        }
    if getattr(validacao, "decisao", None) == "revisar":
        return {
            "tipo": "revisar",
            "texto": "A ficha pede revisão.",
            "estado": "revisar",
            "motivos": motivos,
            "minuta_bloqueada": False,
            "linhas": linhas,
        }
    return {
        "tipo": "aceita",
        "texto": "",
        "estado": "pendente",
        "motivos": motivos,
        "minuta_bloqueada": False,
        "linhas": linhas,
    }


def linhas_da_ficha(solicitacao) -> dict:
    """Campos da ficha com ausência exibida como "não localizado"."""
    valores = solicitacao.valores()
    entidades = []
    for tipo, itens in solicitacao.entidades.model_dump().items():
        for item in itens:
            entidades.append({
                "tipo": ROTULOS_ENTIDADES.get(tipo, tipo),
                "texto": item["texto"],
                "origem": item["origem"],
            })
    return {
        "categoria": para_exibicao(solicitacao.categoria),
        "resumo": para_exibicao(solicitacao.resumo),
        "campos": [
            (ROTULOS_CAMPOS.get(nome, nome), para_exibicao(valores.get(nome)))
            for nome in CAMPOS_ANULAVEIS
        ],
        "entidades": entidades,
    }


def minuta_do_atendimento(ficha: dict | None, consulta: dict | None) -> dict:
    """Monta a minuta com os fatos da ficha e, se houver, a resposta do acervo.

    Documento, prazo e local não saem da solicitação. Sem consulta fundamentada,
    a seção de orientações diz a limitação e não inventa conteúdo institucional.
    A participação da IA permanece no rodapé do modelo.
    """
    if not ficha or not ficha.get("linhas"):
        texto = ficha.get("texto") if ficha and ficha.get("minuta_bloqueada") else MENSAGEM_MINUTA_SEM_FICHA
        if ficha and ficha.get("minuta_bloqueada"):
            texto = MENSAGEM_MINUTA_BLOQUEADA
        return {"pronta": False, "texto": texto}

    if ficha.get("minuta_bloqueada"):
        return {"pronta": False, "texto": MENSAGEM_MINUTA_BLOQUEADA}

    from src.llm_client import montar_minuta

    minuta = montar_minuta(_valores_da_ficha(ficha["linhas"]))
    bloco = _bloco_de_orientacao(consulta)
    minuta = _trocar_orientacoes(minuta, bloco)
    return {"pronta": True, "texto": minuta}


def _valores_da_ficha(linhas: dict) -> dict:
    inverso = {rotulo: nome for nome, rotulo in ROTULOS_CAMPOS.items()}
    valores = {}
    for rotulo, valor in linhas.get("campos") or []:
        nome = inverso.get(rotulo)
        if not nome:
            continue
        valores[nome] = "" if valor == "não localizado" else valor
    return valores


def _bloco_de_orientacao(consulta: dict | None) -> str:
    if not isinstance(consulta, dict):
        return MENSAGEM_ORIENTACAO_PENDENTE
    tipo = consulta.get("tipo")
    if tipo in {None, ""}:
        return MENSAGEM_ORIENTACAO_PENDENTE
    if tipo == "bloqueio":
        return consulta.get("texto") or MENSAGEM_BLOQUEIO
    if tipo == "indice_desatualizado":
        return consulta.get("texto") or MENSAGEM_INDICE
    if tipo == "falha":
        return consulta.get("texto") or MENSAGEM_FALHA
    if tipo in {"sem_evidencia", "conflito"}:
        return consulta.get("texto") or (
            MENSAGEM_SEM_EVIDENCIA if tipo == "sem_evidencia" else MENSAGEM_CONFLITO
        )
    if tipo == "fundamentada":
        resposta = (consulta.get("resposta") or "").strip()
        fontes = _linhas_de_fonte(consulta.get("fontes") or [])
        partes = [resposta or "A consulta não trouxe o texto da resposta."]
        if fontes:
            partes.append("Fontes conferíveis:\n" + "\n".join(fontes))
        return "\n\n".join(partes)
    return MENSAGEM_ORIENTACAO_PENDENTE


def _linhas_de_fonte(fontes: list[dict]) -> list[str]:
    linhas = []
    for fonte in fontes:
        if not isinstance(fonte, dict):
            continue
        local = "sem página"
        if fonte.get("pagina"):
            local = f"página {fonte['pagina']}"
        elif fonte.get("secao"):
            local = f"seção {fonte['secao']}"
        linhas.append(
            f"- {fonte.get('doc_id', 'documento')} · {fonte.get('versao') or 'versão não informada'} · "
            f"{local} · {fonte.get('chunk_id', '')}"
        )
    return linhas


def _trocar_orientacoes(minuta: str, bloco: str) -> str:
    inicio = minuta.find(MARCA_ORIENTACOES)
    fim = minuta.find(MARCA_CIENCIA)
    if inicio < 0 or fim < 0 or fim <= inicio:
        return minuta.rstrip() + "\n\n**Orientações do acervo**\n" + bloco + "\n"
    return minuta[:inicio] + f"{MARCA_ORIENTACOES}\n{bloco}\n\n" + minuta[fim:]


def combinar_estado(atual: str | None, novo: str | None, travado: bool = False) -> str | None:
    """Revisão prevalece sobre pendente. Decisão do operador não é rebaixada."""
    if travado or atual in ESTADOS_FINAIS:
        return atual
    if atual == "revisar" or novo == "revisar":
        return "revisar"
    return novo or atual


def transicionar(
    estado_atual: str | None,
    acao: str,
    justificativa: str = "",
    revisor: str = "",
    cargo: str = "",
) -> str:
    """Aplica a decisão do operador. Aprovada e rejeitada encerram o atendimento."""
    if estado_atual in ESTADOS_FINAIS:
        raise ValueError("Este atendimento já foi encerrado.")
    if estado_atual not in ESTADOS_ABERTOS:
        raise ValueError("Ainda não há atendimento para decidir.")

    justificativa = (justificativa or "").strip()
    revisor = (revisor or "").strip()
    cargo = (cargo or "").strip()

    if acao == "aprovar":
        if not revisor:
            raise ValueError("Informe o nome do servidor.")
        if not cargo:
            raise ValueError("Informe o cargo do servidor.")
        return "aprovada"
    if acao == "rejeitar":
        if not justificativa:
            raise ValueError("Informe a justificativa.")
        return "rejeitada"
    if acao == "revisar":
        if not justificativa:
            raise ValueError("Informe a justificativa.")
        return "revisar"
    if acao == "retomar":
        if estado_atual != "revisar":
            raise ValueError("Só um atendimento em revisão volta a pendente.")
        return "pendente"
    raise ValueError("Decisão desconhecida.")


def _consulta(tipo, texto, estado, resposta, fontes, justificativa) -> dict:
    return {
        "tipo": tipo,
        "texto": texto,
        "estado": estado,
        "resposta": resposta,
        "fontes": fontes,
        "justificativa": justificativa,
    }


def _texto(valor) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def _decisao(guardrail) -> str | None:
    if guardrail is None:
        return None
    if isinstance(guardrail, dict):
        return guardrail.get("decisao")
    return getattr(guardrail, "decisao", None)


def _motivos(guardrail) -> tuple:
    if guardrail is None:
        return ()
    if isinstance(guardrail, dict):
        return tuple(guardrail.get("motivos") or ())
    return tuple(getattr(guardrail, "motivos", ()) or ())
