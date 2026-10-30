"""Auditoria das consultas do RAG (RF21).

Cada consulta vira um evento `consulta_rag` em `resultados/logs/execucoes.jsonl`
(o mesmo registro do restante do projeto), com o necessário para conferir a
origem de uma resposta sem expor credenciais nem dados pessoais:

  - quando, quanto tempo levou e com qual configuração de geração;
  - versão do esquema da resposta, do prompt e do índice;
  - consulta (com identificadores mascarados) e trechos recuperados;
  - alertas de instrução em documento, resultado, erro, tokens e custo (ou a
    razão de não estarem disponíveis).

A decisão humana sobre a resposta continua sendo gravada por
`audit.registrar_decisao`, usando o mesmo `id_execucao` (o `id_consulta` que
`responder_rf19` devolve).
"""

import hashlib
import re
from uuid import uuid4

from src.audit import registrar_evento
from src.privacidade import minimizar_texto

VERSAO_ESQUEMA_RESPOSTA = "rag-1.1"

# Protocolos no formato 2026-000201
_PROTOCOLO = re.compile(r"\b\d{4}-\d{4,8}\b")


def versao_indice_atual() -> str:
    """Versão do conteúdo do índice vetorial em uso (hash curto)."""

    from src.vector_store import calcular_versao_indice, obter_colecao

    return calcular_versao_indice(obter_colecao())


def versao_do_prompt(*textos: str) -> str:
    """Identificador curto (hash) dos prompts usados na geração."""

    resumo = hashlib.sha256("\n---\n".join(textos).encode("utf-8")).hexdigest()

    return resumo[:12]


def mascarar_identificadores(texto: str) -> str:
    """Remove dados pessoais (RF12) e mascara protocolos antes de gravar o log."""

    return _PROTOCOLO.sub("[PROTOCOLO]", minimizar_texto(texto or ""))


def montar_evento(
    *,
    pergunta,
    top_k,
    resultado,
    rastro,
    inicio,
    fim,
    latencia_total,
    erro=None,
    versao_prompt=None,
    id_consulta=None,
):
    """Monta o evento a gravar. Não grava nada."""

    resultado = resultado or {}
    auditoria = resultado.get("auditoria") or {}
    evidencias = rastro.get("evidencias") or []
    id_consulta = id_consulta or str(uuid4())

    evento = {
        "id_execucao": id_consulta,
        "inicio": inicio,
        "fim": fim,
        "latencia_total_segundos": round(latencia_total, 3),
        "latencia_recuperacao_segundos": rastro.get("latencia_recuperacao"),
        "pergunta": mascarar_identificadores(pergunta),
        "top_k": top_k,
        "versao_esquema_resposta": VERSAO_ESQUEMA_RESPOSTA,
        "versao_prompt": versao_prompt,
        "versao_indice": rastro.get("versao_indice") or "indisponivel",
        "ids_recuperados": [
            {
                "chunk_id": e["chunk_id"],
                "distancia": round(e["distancia"], 4) if e.get("distancia") is not None else None,
            }
            for e in evidencias
        ],
        "ids_citados": [f.get("chunk_id") for f in resultado.get("fontes", [])],
        "alertas": [
            {"chunk_id": a.get("chunk_id"), "doc_id": a.get("doc_id"), "padroes": a.get("padroes")}
            for a in resultado.get("alertas", [])
        ],
        "status": resultado.get("status"),
        "decisao": resultado.get("decisao"),
        "erro": erro or auditoria.get("erro"),
        "geracao": {
            "provedor": auditoria.get("provedor"),
            "modelo": auditoria.get("modelo"),
            "configuracao": auditoria.get("configuracao") or rastro.get("configuracao"),
            "simulado": auditoria.get("simulado"),
            "status": auditoria.get("status") or "nao_chamada",
            "chamadas": auditoria.get("tentativas", 1 if auditoria else 0),
            "tempo_resposta_segundos": auditoria.get("tempo_resposta_segundos"),
            "tokens_entrada": auditoria.get("tokens_entrada"),
            "tokens_saida": auditoria.get("tokens_saida"),
            "tokens_total": auditoria.get("tokens_total"),
            "custo_estimado_usd": auditoria.get("custo_estimado_usd"),
            "metricas_indisponiveis": auditoria.get("metricas_indisponiveis"),
        },
    }

    if not auditoria:
        evento["geracao"]["metricas_indisponiveis"] = "Nenhuma chamada ao modelo nesta consulta."

    return evento


def registrar_consulta_rag(**campos) -> dict:
    """Grava o evento `consulta_rag` e devolve o que foi gravado."""

    return registrar_evento("consulta_rag", montar_evento(**campos))
