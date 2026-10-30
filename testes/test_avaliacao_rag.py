"""Testes da conferência das oito perguntas do RAG (offline, sem API)."""

import copy

from src.avaliacao_rag import (
    avaliar_item,
    carregar_itens,
    consolidar,
    executar,
    gerar_relatorio_md,
    gerar_relatorio_repeticoes_md,
    resumir,
)


def resultado_ideal(item):
    """Resposta que cumpre tudo o que o gabarito pede para aquele tipo."""

    refs = item["referencias"]
    fontes = [
        {
            "chunk_id": f"{ref['doc_id']}-c{i}",
            "doc_id": ref["doc_id"],
            "versao": "1",
            "pagina": ref["pagina"],
            "secao": None,
            "trecho": f"... {ref['frase']} ...",
            "trecho_citado": ref["frase"],
        }
        for i, ref in enumerate(refs)
    ]
    elementos = [
        (e[0] if isinstance(e, list) else e) for e in item["elementos_esperados"]
    ]

    if item["tipo"] == "respondivel":
        return {"status": "fundamentada", "decisao": "responder", "fontes": fontes,
                "resposta": "Resposta com " + " e ".join(elementos), "justificativa": "ok"}

    if item["tipo"] == "sem_resposta":
        return {"status": "sem_evidencia", "decisao": "revisar", "fontes": [],
                "resposta": "Sem evidências suficientes.", "justificativa": "ok"}

    return {"status": "conflito", "decisao": "revisar", "fontes": fontes,
            "resposta": "Divergência entre documentos.", "justificativa": " ".join(elementos)}


def responder_ideal(pergunta, top_k=15):
    item = next(i for i in carregar_itens() if i["pergunta"] == pergunta)
    return resultado_ideal(item)


def test_resposta_ideal_passa_nas_oito():
    avaliacoes, resumo = executar(responder_ideal)

    assert len(avaliacoes) == 8
    assert all(a["aprovado"] for a in avaliacoes), [
        (a["id"], a["verificacoes"]) for a in avaliacoes if not a["aprovado"]
    ]
    assert resumo["status_correto"] == {"numerador": 8, "denominador": 8}
    assert resumo["respondiveis_aprovadas"] == {"numerador": 5, "denominador": 5}
    assert resumo["abstencao_correta_sem_resposta"] == {"numerador": 2, "denominador": 2}
    assert resumo["conflito_tratado"] == {"numerador": 1, "denominador": 1}
    assert resumo["tokens_total"] is None
    assert "não informou tokens" in resumo["observacao_metricas"]


def _item(id_):
    return next(i for i in carregar_itens() if i["id"] == id_)


def test_status_errado_reprova():
    resultado = resultado_ideal(_item("P06"))
    resultado["status"] = "fundamentada"

    avaliacao = avaliar_item(_item("P06"), resultado)

    assert not avaliacao["aprovado"]
    assert avaliacao["verificacoes"]["status_correto"] is False


def test_resposta_sem_evidencia_inventada_em_pergunta_sem_resposta_reprova():
    resultado = resultado_ideal(_item("P07"))
    resultado.update(status="fundamentada", decisao="responder", resposta="Das 8h às 17h.")

    assert not avaliar_item(_item("P07"), resultado)["aprovado"]


def test_citacao_que_nao_esta_no_trecho_reprova():
    resultado = resultado_ideal(_item("P01"))
    resultado["fontes"][0]["trecho_citado"] = "frase que o trecho recuperado não contém"

    avaliacao = avaliar_item(_item("P01"), resultado)

    assert avaliacao["verificacoes"]["citacoes_rastreaveis"] is False
    assert not avaliacao["aprovado"]


def test_sem_citacao_reprova():
    resultado = resultado_ideal(_item("P01"))
    resultado["fontes"] = []

    assert not avaliar_item(_item("P01"), resultado)["aprovado"]


def test_valor_proibido_reprova():
    resultado = resultado_ideal(_item("P04"))
    resultado["resposta"] += " (o início era 21/07/2026)"

    avaliacao = avaliar_item(_item("P04"), resultado)

    assert avaliacao["verificacoes"]["sem_valor_proibido"] is False
    assert not avaliacao["aprovado"]


def test_citar_pagina_diferente_da_referencia_reprova():
    resultado = resultado_ideal(_item("P02"))
    resultado["fontes"][0]["pagina"] = 99

    avaliacao = avaliar_item(_item("P02"), resultado)

    assert avaliacao["verificacoes"]["cita_pagina_de_referencia"] is False


def test_elemento_esperado_ausente_reprova():
    resultado = resultado_ideal(_item("P05"))
    resultado["resposta"] = "O período não foi localizado."

    assert not avaliar_item(_item("P05"), resultado)["aprovado"]


def test_conflito_exige_as_duas_datas_e_os_dois_documentos():
    resultado = resultado_ideal(_item("P08"))
    resultado["fontes"] = resultado["fontes"][:1]

    avaliacao = avaliar_item(_item("P08"), resultado)

    assert avaliacao["verificacoes"]["cita_os_dois_documentos"] is False
    assert not avaliacao["aprovado"]


def test_erro_em_uma_pergunta_nao_interrompe_as_demais():
    def responder(pergunta, top_k=15):
        if "Mimoso" in pergunta:
            raise RuntimeError("falha na recuperação")
        return responder_ideal(pergunta)

    avaliacoes, resumo = executar(responder)

    p04 = next(a for a in avaliacoes if a["id"] == "P04")
    assert "RuntimeError" in p04["erro_execucao"]
    assert p04["aprovado"] is False
    assert resumo["respondiveis_aprovadas"] == {"numerador": 4, "denominador": 5}
    assert sum(a["aprovado"] for a in avaliacoes) == 7


def test_tokens_e_custo_sao_somados_quando_informados():
    def responder(pergunta, top_k=15):
        resultado = copy.deepcopy(responder_ideal(pergunta))
        resultado["auditoria"] = {"tokens_total": 100, "custo_estimado_usd": 0.0001}
        return resultado

    _, resumo = executar(responder)

    assert resumo["tokens_total"] == 800
    assert resumo["custo_estimado_usd"] == 0.0008


def test_relatorio_markdown_tem_metricas_e_fontes():
    avaliacoes, resumo = executar(responder_ideal)
    texto = gerar_relatorio_md({
        "data_hora": "2026-10-30T00:00:00-04:00", "top_k": 15, "configuracao": "principal",
        "resumo": resumo, "avaliacoes": avaliacoes,
    })

    assert "Respondíveis aprovadas" in texto
    assert "8/8" in texto and "5/5" in texto
    assert "P08" in texto and "ACV-06" in texto


def test_citacao_com_reticencias_e_rastreavel_por_fragmento():
    resultado = resultado_ideal(_item("P04"))
    fonte = resultado["fontes"][0]
    fonte["trecho"] = "Fica alterada para o dia 05 de outubro de 2026 ... Cuiabá Agropecuária Mimoso"
    fonte["trecho_citado"] = "Fica alterada para o dia 05 de outubro de 2026 ... Agropecuária ... Mimoso"

    assert avaliar_item(_item("P04"), resultado)["verificacoes"]["citacoes_rastreaveis"] is True

    fonte["trecho_citado"] = "Fica alterada ... fragmento que não existe no trecho"

    assert avaliar_item(_item("P04"), resultado)["verificacoes"]["citacoes_rastreaveis"] is False


def test_alerta_de_instrucao_no_acervo_nao_reprova_a_decisao():
    resultado = resultado_ideal(_item("P02"))
    resultado["decisao"] = "revisar"
    resultado["alertas"] = [{"tipo": "instrucao_em_documento", "chunk_id": "x", "doc_id": "ACV-09"}]

    avaliacao = avaliar_item(_item("P02"), resultado)

    assert avaliacao["verificacoes"]["decisao_correta"] is True
    assert avaliacao["alertas"] == 1


def test_revisar_sem_alerta_continua_reprovando_respondivel():
    resultado = resultado_ideal(_item("P02"))
    resultado["decisao"] = "revisar"

    assert avaliar_item(_item("P02"), resultado)["verificacoes"]["decisao_correta"] is False


def test_consolidar_conta_em_quantas_execucoes_cada_pergunta_passou():
    boa, _ = executar(responder_ideal)

    def responder_ruim_na_p04(pergunta, top_k=15):
        if "Mimoso" in pergunta:
            return {"status": "sem_evidencia", "decisao": "revisar", "fontes": [],
                    "resposta": "Sem evidência.", "justificativa": "x"}
        return responder_ideal(pergunta)

    ruim, _ = executar(responder_ruim_na_p04)

    consolidado = consolidar([boa, ruim, boa])
    p04 = next(q for q in consolidado["perguntas"] if q["id"] == "P04")
    p01 = next(q for q in consolidado["perguntas"] if q["id"] == "P01")

    assert consolidado["rodadas"] == 3
    assert p04["aprovadas"] == 2 and p04["execucoes"] == 3
    assert p04["status_obtidos"] == ["fundamentada", "sem_evidencia", "fundamentada"]
    assert p04["falhas_por_verificacao"]["status_correto"] == 1
    assert p01["aprovadas"] == 3
    assert consolidado["aprovacoes_por_rodada"] == [8, 7, 8]

    texto = gerar_relatorio_repeticoes_md(consolidado, 15)
    assert "2/3" in texto and "P04" in texto and "status_correto (1x)" in texto