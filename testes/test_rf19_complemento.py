"""Testes automatizados do complemento RF19."""

import json

import src.rf19_complemento as rf19


def evidencia(doc_id="ACV-01", chunk_id="chunk-01"):
    return {
        "chunk_id": chunk_id,
        "texto": (
            "A matrícula deverá ser realizada presencialmente "
            "na Escola Técnica Estadual."
        ),
        "metadados": {
            "doc_id": doc_id,
            "titulo": "Edital",
            "versao": "1.0",
            "pagina": 10,
            "secao": "10.4",
        },
    }


def preparar_mocks(monkeypatch, evidencias, resposta_llm):
    monkeypatch.setattr(
        rf19,
        "recuperar_evidencias",
        lambda pergunta, top_k=15: evidencias,
    )

    monkeypatch.setattr(
        rf19,
        "montar_contexto",
        lambda evidencias: "Contexto simulado.",
    )

    monkeypatch.setattr(
        rf19,
        "obter_documentos_catalogados",
        lambda: {
            "ACV-01": {
                "doc_id": "ACV-01",
                "ordem": 0,
                "altera": [],
            }
        },
    )

    monkeypatch.setattr(
        rf19,
        "formatar_fonte",
        lambda e: {
            "doc_id": e["metadados"]["doc_id"],
            "chunk_id": e["chunk_id"],
            "pagina": e["metadados"]["pagina"],
        },
    )

    monkeypatch.setattr(
        rf19,
        "consultar_llm",
        lambda **kwargs: (
            json.dumps(resposta_llm, ensure_ascii=False),
            {"tokens_total": 100, "status": "sucesso"},
        ),
    )


def resposta_base(status, citacoes=None):
    return {
        "status": status,
        "resposta": "A matrícula é presencial.",
        "justificativa": "Informação verificada.",
        "citacoes": citacoes or [],
        "prevalencia": {
            "item": None,
            "escopo_aplicado": "",
            "documentos_considerados": ["ACV-01"],
            "resolvida": True,
        },
    }


def test_sem_evidencias_nao_chama_llm(monkeypatch):
    monkeypatch.setattr(
        rf19,
        "recuperar_evidencias",
        lambda pergunta, top_k=15: [],
    )

    def falhar(**kwargs):
        raise AssertionError("LLM não deveria ser chamado.")

    monkeypatch.setattr(rf19, "consultar_llm", falhar)

    resultado = rf19.responder_rf19("Pergunta sem evidências")

    assert resultado["status"] == rf19.STATUS_SEM_EVIDENCIA
    assert resultado["decisao"] == "revisar"


def test_resposta_fundamentada(monkeypatch):
    e = evidencia()

    resposta = resposta_base(
        rf19.STATUS_FUNDAMENTADA,
        [
            {
                "chunk_id": "chunk-01",
                "trecho": (
                    "A matrícula deverá ser realizada presencialmente"
                ),
            }
        ],
    )

    preparar_mocks(monkeypatch, [e], resposta)

    resultado = rf19.responder_rf19(
        "A matrícula precisa ser presencial?"
    )

    assert resultado["status"] == rf19.STATUS_FUNDAMENTADA
    assert resultado["decisao"] == "responder"
    assert len(resultado["fontes"]) == 1


def test_citacao_inventada_gera_abstencao(monkeypatch):
    e = evidencia()

    resposta = resposta_base(
        rf19.STATUS_FUNDAMENTADA,
        [
            {
                "chunk_id": "chunk-inexistente",
                "trecho": "O prazo para recurso é de quinze dias corridos",
            }
        ],
    )

    preparar_mocks(monkeypatch, [e], resposta)

    resultado = rf19.responder_rf19("Pergunta")

    assert resultado["status"] == rf19.STATUS_SEM_EVIDENCIA
    assert resultado["decisao"] == "revisar"


def test_trecho_verdadeiro_com_chunk_id_inexistente_e_atribuido_ao_chunk_certo(monkeypatch):
    e = evidencia()

    resposta = resposta_base(
        rf19.STATUS_FUNDAMENTADA,
        [
            {
                "chunk_id": "chunk-inexistente",
                "trecho": "A matrícula deverá ser realizada presencialmente",
            }
        ],
    )

    preparar_mocks(monkeypatch, [e], resposta)

    resultado = rf19.responder_rf19("Pergunta")

    assert resultado["status"] == rf19.STATUS_FUNDAMENTADA
    assert resultado["fontes"][0]["chunk_id"] == "chunk-01"
    assert resultado["fontes"][0]["chunk_id_corrigido_de"] == "chunk-inexistente"


def test_conflito_exige_documentos_distintos(monkeypatch):
    e = evidencia()

    resposta = resposta_base(
        rf19.STATUS_CONFLITO,
        [
            {
                "chunk_id": "chunk-01",
                "trecho": "A matrícula deverá ser realizada presencialmente",
            }
        ],
    )

    preparar_mocks(monkeypatch, [e], resposta)

    resultado = rf19.responder_rf19("Existe conflito?")

    assert resultado["status"] == rf19.STATUS_SEM_EVIDENCIA
    assert resultado["decisao"] == "revisar"


def test_auditoria_preservada_em_erro(monkeypatch):
    e = evidencia()

    resposta = resposta_base(
        "status_invalido",
    )

    preparar_mocks(monkeypatch, [e], resposta)

    resultado = rf19.responder_rf19("Pergunta")

    assert resultado["status"] == rf19.STATUS_SEM_EVIDENCIA
    assert resultado["auditoria"]["tokens_total"] == 100