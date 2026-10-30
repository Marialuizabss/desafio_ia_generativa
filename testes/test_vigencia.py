"""Vigência dos trechos (RF19): testes com trechos reais do acervo, sem API.

As regras são gerais: nenhuma cita uma pergunta, um curso ou uma data. Os trechos
vêm de `dados_vigencia.py`, cópias do texto real extraído dos PDFs.
"""

import json
from types import SimpleNamespace

import pytest

import src.rf19_complemento as rf19
from src.vigencia import (
    analisar_vigencia,
    avisos_de_vigencia,
    citacao_substituida,
)
from testes.dados_vigencia import TRECHOS

CATALOGO = {
    "ACV-01": {"doc_id": "ACV-01", "ordem": 0, "altera": []},
    "ACV-04": {"doc_id": "ACV-04", "ordem": 3,
               "altera": [{"doc_id": "ACV-01", "itens": ["5"], "escopo": "Cronograma, por inteiro"}]},
    "ACV-06": {"doc_id": "ACV-06", "ordem": 5,
               "altera": [{"doc_id": "ACV-01", "itens": ["5"], "escopo": "Linhas do cronograma"}]},
    "ACV-07": {"doc_id": "ACV-07", "ordem": 6,
               "altera": [{"doc_id": "ACV-01", "itens": ["5"], "escopo": "Início das aulas"}]},
}


def evidencias(*chunk_ids):
    return [
        {"chunk_id": cid, "texto": TRECHOS[cid]["texto"], "metadados": TRECHOS[cid]["metadados"],
         "distancia": 0.2}
        for cid in chunk_ids
    ]


def itens_do(vigencia, chunk_id, tipo=None):
    return [i for i in vigencia.get(chunk_id, []) if tipo in (None, i["tipo"])]


# ------------------------------------------------------------- detecção

def test_linha_do_cronograma_substituida_por_retificacao_mais_recente():
    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)

    linhas = itens_do(vig, "ACV-04-p2-s1-c1", "linha_substituida")
    efetivacao = [i for i in linhas if "Efetivação das matrículas" in i["texto"]]

    assert len(efetivacao) == 1
    assert "23 e 24/07/2026" in efetivacao[0]["texto"]
    assert efetivacao[0]["substituido_por"]["doc_id"] == "ACV-06"
    assert "08/07/2026" in efetivacao[0]["substituido_por"]["texto"]


def test_versao_antiga_sob_onde_se_le():
    vig = analisar_vigencia(evidencias("ACV-06-p1-s1-c2"), CATALOGO)

    antigos = itens_do(vig, "ACV-06-p1-s1-c2", "onde_se_le")

    assert len(antigos) == 1
    assert "23 e 24/07/2026" in antigos[0]["texto"]


def test_linha_igual_nos_dois_documentos_nao_e_substituida():
    # "Início das aulas 21/07/2026" aparece igual no ACV-04 e no ACV-06.
    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)

    assert not [
        i for i in itens_do(vig, "ACV-04-p2-s1-c1") if "Início das aulas" in i["texto"]
    ]


def test_documento_mais_antigo_nunca_substitui_o_mais_novo():
    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)

    assert not itens_do(vig, "ACV-06-p2-s1-c1", "linha_substituida")


def test_documentos_sem_ligacao_no_catalogo_nao_se_substituem():
    catalogo = {
        "ACV-04": {**CATALOGO["ACV-04"], "altera": [{"doc_id": "OUTRO", "itens": ["9"], "escopo": "x"}]},
        "ACV-06": CATALOGO["ACV-06"],
    }

    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), catalogo)

    assert not itens_do(vig, "ACV-04-p2-s1-c1")


def test_documento_sem_ordem_e_ignorado():
    catalogo = {"ACV-04": {**CATALOGO["ACV-04"], "ordem": None}, "ACV-06": CATALOGO["ACV-06"]}

    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), catalogo)

    assert not itens_do(vig, "ACV-04-p2-s1-c1")


def test_linha_do_edital_base_substituida_pela_retificacao():
    vig = analisar_vigencia(evidencias("ACV-01-p8-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)

    assert any(
        "Efetivação das matrículas" in i["texto"] and i["substituido_por"]["doc_id"] == "ACV-06"
        for i in itens_do(vig, "ACV-01-p8-s1-c1", "linha_substituida")
    )


def test_avisos_dizem_o_que_foi_substituido_e_pelo_que():
    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)

    aviso = avisos_de_vigencia(vig)

    assert aviso.startswith("[AVISOS DE VIGÊNCIA]")
    assert "SUBSTITUÍDA" in aviso and "ACV-06" in aviso and "08/07/2026" in aviso
    assert avisos_de_vigencia({}) == ""


def test_citacao_da_linha_substituida_e_identificada():
    vig = analisar_vigencia(evidencias("ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"), CATALOGO)
    itens = vig["ACV-04-p2-s1-c1"]

    antiga = "Efetivação das matrículas da 4º chamada das vagas remanescentes 23 e 24/07/2026"
    vigente = "Início das aulas 21/07/2026"

    assert citacao_substituida(antiga, [antiga], itens) is not None
    assert citacao_substituida(vigente, [vigente], itens) is None


# ------------------------------------------------------------- fluxo completo

SEM_CONTRADICAO = {"contradicao": False, "citacoes": [], "explicacao": ""}


def _preparar(monkeypatch, chunk_ids, respostas, verificacoes=None):
    """Simula o modelo: `respostas` são as respostas à pergunta, `verificacoes`
    as respostas da segunda leitura (se faltarem, não há contradição)."""

    chamadas = SimpleNamespace(pedidos=[], verificacoes=[])
    fila = list(respostas)
    fila_verificacao = list(verificacoes or [])

    monkeypatch.setattr(rf19, "recuperar_evidencias", lambda p, top_k=15: evidencias(*chunk_ids))
    monkeypatch.setattr(rf19, "obter_documentos_catalogados", lambda: CATALOGO)
    monkeypatch.setattr(rf19, "montar_contexto", lambda ev: "CONTEXTO")

    def llm(**kwargs):
        pedido = json.loads(kwargs["entrada"])

        if kwargs["instrucoes"] == rf19.INSTRUCOES_VERIFICACAO:
            chamadas.verificacoes.append(pedido)
            resposta = fila_verificacao.pop(0) if fila_verificacao else SEM_CONTRADICAO
            texto = resposta if isinstance(resposta, str) else json.dumps(resposta, ensure_ascii=False)
        else:
            chamadas.pedidos.append(pedido)
            texto = json.dumps(fila.pop(0), ensure_ascii=False)

        return texto, {"tokens_total": 100, "status": "sucesso"}

    monkeypatch.setattr(rf19, "consultar_llm", llm)

    return chamadas


def _resposta(texto, chunk_id, trecho, item="5"):
    return {
        "status": "fundamentada",
        "resposta": texto,
        "justificativa": "Conforme o cronograma.",
        "citacoes": [{"chunk_id": chunk_id, "trecho": trecho}],
        "prevalencia": {"item": item, "escopo_aplicado": "Cronograma",
                        "documentos_considerados": ["ACV-04", "ACV-06"], "resolvida": True},
    }


ANTIGA = _resposta(
    "O período é de 23 e 24/07/2026.", "ACV-04-p2-s1-c1",
    "Efetivação das matrículas da 4º chamada das vagas remanescentes 23 e 24/07/2026",
)
VIGENTE = _resposta(
    "O período é de 03/07/2026 a 08/07/2026.", "ACV-06-p2-s1-c1",
    "Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026",
)
CHUNKS = ["ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1"]


def test_resposta_com_versao_vigente_passa_na_primeira(monkeypatch):
    c = _preparar(monkeypatch, CHUNKS, [VIGENTE])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"
    assert len(c.pedidos) == 1
    assert "correcao_de_vigencia" not in c.pedidos[0]
    # O modelo foi avisado, antes de responder, do que está substituído.
    assert "AVISOS DE VIGÊNCIA" in c.pedidos[0]["fontes_nao_confiaveis"]


def test_resposta_com_versao_substituida_recebe_uma_correcao(monkeypatch):
    c = _preparar(monkeypatch, CHUNKS, [ANTIGA, VIGENTE])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"
    assert "08/07/2026" in resultado["resposta"]
    assert [f["doc_id"] for f in resultado["fontes"]] == ["ACV-06"]
    assert len(c.pedidos) == 2
    assert "SUBSTITUÍDA" in c.pedidos[1]["correcao_de_vigencia"]


def test_se_o_modelo_insiste_na_versao_substituida_vai_para_revisao(monkeypatch):
    c = _preparar(monkeypatch, CHUNKS, [ANTIGA, ANTIGA])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "conflito"
    assert resultado["decisao"] == "revisar"
    assert "substituído" in resultado["justificativa"]
    assert len(c.pedidos) == 2
    assert not c.verificacoes


def test_citar_chunk_errado_com_trecho_verdadeiro_e_corrigido(monkeypatch):
    errada = _resposta(
        "O período é de 03/07/2026 a 08/07/2026.", "ACV-04-p2-s1-c1",
        "Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026",
    )
    _preparar(monkeypatch, CHUNKS, [errada])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"
    assert resultado["fontes"][0]["chunk_id"] == "ACV-06-p2-s1-c1"
    assert resultado["fontes"][0]["chunk_id_corrigido_de"] == "ACV-04-p2-s1-c1"


def test_citacao_inventada_continua_indo_para_revisao(monkeypatch):
    inventada = _resposta(
        "O período é de 10/07/2026 a 12/07/2026.", "ACV-06-p2-s1-c1",
        "Efetivação das matrículas da 4ª chamada das vagas remanescentes 10/07/2026 a 12/07/2026",
    )
    _preparar(monkeypatch, CHUNKS, [inventada])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "sem_evidencia"
    assert resultado["decisao"] == "revisar"


def test_data_na_resposta_que_nao_esta_na_citacao_e_bloqueada(monkeypatch):
    errada = _resposta(VIGENTE["resposta"] + " Início em 01/01/2027.", "ACV-06-p2-s1-c1",
                       VIGENTE["citacoes"][0]["trecho"])
    _preparar(monkeypatch, CHUNKS, [errada])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["decisao"] == "revisar"
    assert "não comprovadas" in resultado["justificativa"]


# ------------------------------------------------------------- segunda leitura

DIVULGACAO = _resposta(
    "A lista será divulgada em 09/07/2026.", "ACV-06-p2-s1-c1",
    "Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 09/07/2026",
    item="5",
)
LINHA_ACV06 = {
    "chunk_id": "ACV-06-p2-s1-c1",
    "trecho": "Divulgação/organização das matrículas efetivadas da 4ª chamada pelas Escolas Técnicas Estaduais 09/07/2026",
}
LINHA_ACV01 = {
    "chunk_id": "ACV-01-p13-s1-c1",
    "trecho": "A lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão divulgadas no mural das Escolas Técnicas no dia 11/06/2026.",
}
CHUNKS_DIVULGACAO = ["ACV-06-p2-s1-c1", "ACV-01-p13-s1-c1"]


def test_documentos_com_datas_diferentes_para_o_mesmo_fato_viram_conflito(monkeypatch):
    contradicao = {"contradicao": True, "citacoes": [LINHA_ACV06, LINHA_ACV01],
                   "explicacao": "As datas de divulgação divergem."}
    c = _preparar(monkeypatch, CHUNKS_DIVULGACAO, [DIVULGACAO], [contradicao])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre divulgação")

    assert resultado["status"] == "conflito"
    assert resultado["decisao"] == "revisar"
    assert {f["doc_id"] for f in resultado["fontes"]} == {"ACV-06", "ACV-01"}
    assert "ACV-01 e ACV-06" in resultado["justificativa"]
    assert "11/06/2026" in resultado["fontes"][1]["trecho_citado"]
    assert len(c.verificacoes) == 1
    assert resultado["auditoria"]["tentativas"] == 2
    assert resultado["auditoria"]["tokens_total"] == 200


def test_sem_contradicao_a_resposta_segue_fundamentada(monkeypatch):
    c = _preparar(monkeypatch, CHUNKS_DIVULGACAO, [DIVULGACAO])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre divulgação")

    assert resultado["status"] == "fundamentada"
    assert len(c.verificacoes) == 1


def test_contradicao_alegada_mas_com_os_mesmos_numeros_e_ignorada(monkeypatch):
    linha_a = {"chunk_id": "ACV-04-p2-s1-c1", "trecho": "Início das aulas 21/07/2026"}
    linha_b = {"chunk_id": "ACV-06-p2-s1-c1", "trecho": "Início das aulas 21/07/2026"}
    alegacao = {"contradicao": True, "citacoes": [linha_a, linha_b], "explicacao": "Divergem."}
    _preparar(monkeypatch, CHUNKS, [VIGENTE], [alegacao])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"


def test_contradicao_com_linha_substituida_e_ignorada(monkeypatch):
    antiga = {"chunk_id": "ACV-04-p2-s1-c1",
              "trecho": "Efetivação das matrículas da 4º chamada das vagas remanescentes 23 e 24/07/2026"}
    nova = {"chunk_id": "ACV-06-p2-s1-c1",
            "trecho": "Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026"}
    alegacao = {"contradicao": True, "citacoes": [antiga, nova], "explicacao": "Divergem."}
    _preparar(monkeypatch, CHUNKS, [VIGENTE], [alegacao])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"


def test_contradicao_com_citacao_inventada_e_ignorada(monkeypatch):
    inventada = {"chunk_id": "ACV-01-p13-s1-c1", "trecho": "A lista será divulgada no dia 15/06/2026 no site"}
    alegacao = {"contradicao": True, "citacoes": [LINHA_ACV06, inventada], "explicacao": "Divergem."}
    _preparar(monkeypatch, CHUNKS_DIVULGACAO, [DIVULGACAO], [alegacao])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre divulgação")

    assert resultado["status"] == "fundamentada"


def test_falha_da_segunda_leitura_nao_derruba_a_resposta(monkeypatch):
    _preparar(monkeypatch, CHUNKS_DIVULGACAO, [DIVULGACAO], ["isto não é json"])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre divulgação")

    assert resultado["status"] == "fundamentada"


def test_com_um_unico_documento_nao_ha_segunda_leitura(monkeypatch):
    c = _preparar(monkeypatch, ["ACV-06-p2-s1-c1"], [VIGENTE])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"
    assert not c.verificacoes


# ------------------------------------------------------------- instruções em documentos

def test_trecho_com_instrucao_ao_assistente_e_detectado():
    padroes = rf19._instrucao_suspeita(TRECHOS["ACV-09-p0-s4-c1"]["texto"])

    assert "nota_ao_assistente" in padroes
    assert "desconsiderar_regras" in padroes
    assert "pedir_segredo" in padroes


def test_trechos_legitimos_do_acervo_nao_sao_sinalizados():
    legitimos = [c for c in TRECHOS if c != "ACV-09-p0-s4-c1"]

    for chunk_id in legitimos:
        assert rf19._instrucao_suspeita(TRECHOS[chunk_id]["texto"]) == [], chunk_id


def test_trecho_suspeito_sai_do_contexto_e_vira_alerta(monkeypatch):
    c = _preparar(monkeypatch, ["ACV-06-p2-s1-c1", "ACV-09-p0-s4-c1"], [VIGENTE])
    contextos = []
    monkeypatch.setattr(rf19, "montar_contexto", lambda ev: contextos.append([e["chunk_id"] for e in ev]) or "CTX")

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert contextos == [["ACV-06-p2-s1-c1"]]
    assert resultado["status"] == "fundamentada"
    # A resposta não cita o documento alertado: segue como resposta, com o alerta registrado.
    assert resultado["decisao"] == "responder"
    assert resultado["alertas"][0]["chunk_id"] == "ACV-09-p0-s4-c1"
    assert resultado["alertas"][0]["doc_id"] == "ACV-09"
    assert "aviso" in resultado
    # O alerta guarda o motivo, não o texto da instrução.
    assert "CONFIRMADA" not in json.dumps(resultado["alertas"], ensure_ascii=False)
    assert len(c.pedidos) == 1


def test_so_trecho_suspeito_recuperado_nao_chama_o_modelo(monkeypatch):
    c = _preparar(monkeypatch, ["ACV-09-p0-s4-c1"], [])

    resultado = rf19.responder_rf19("Como vai funcionar a pesquisa?")

    assert resultado["status"] == "sem_evidencia"
    assert resultado["decisao"] == "revisar"
    assert resultado["alertas"]
    assert not c.pedidos


def test_partes_legitimas_do_mesmo_documento_continuam_usaveis(monkeypatch):
    resposta = {
        "status": "fundamentada",
        "resposta": "A participação é obrigatória para os alunos matriculados.",
        "justificativa": "Item 2.2 do comunicado.",
        "citacoes": [{"chunk_id": "ACV-09-p0-s3-c1",
                      "trecho": "A participação é obrigatória para os alunos matriculados"}],
        "prevalencia": {"item": None, "escopo_aplicado": "", "documentos_considerados": ["ACV-09"],
                        "resolvida": True},
    }
    _preparar(monkeypatch, ["ACV-09-p0-s3-c1", "ACV-09-p0-s4-c1"], [resposta])

    resultado = rf19.responder_rf19("A pesquisa socioeconômica é obrigatória?")

    assert resultado["status"] == "fundamentada"
    assert resultado["fontes"][0]["chunk_id"] == "ACV-09-p0-s3-c1"
    assert resultado["decisao"] == "revisar"


def test_contradicao_alegada_sobre_assuntos_diferentes_e_ignorada(monkeypatch):
    # Números diferentes, mas os trechos não tratam do mesmo fato.
    presencial = {"chunk_id": "ACV-01-p10-s1-c3",
                  "trecho": "o candidato deverá apresentar presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I"}
    aula = {"chunk_id": "ACV-06-p2-s1-c1", "trecho": "Início das aulas 21/07/2026"}
    alegacao = {"contradicao": True, "citacoes": [presencial, aula], "explicacao": "Divergem."}
    _preparar(monkeypatch, ["ACV-01-p10-s1-c3", "ACV-06-p2-s1-c1"], [VIGENTE], [alegacao])

    resultado = rf19.responder_rf19("Pergunta qualquer sobre o cronograma")

    assert resultado["status"] == "fundamentada"


def test_prompt_pede_resposta_completa_e_citacao_por_chunk():
    assert "sem omitir nenhum" in rf19.INSTRUCOES
    assert "UM único chunk" in rf19.INSTRUCOES


def test_resposta_que_cita_o_documento_alertado_vai_para_revisao(monkeypatch):
    resposta = {
        "status": "fundamentada",
        "resposta": "A participação é obrigatória para os alunos matriculados.",
        "justificativa": "Item 2.2 do comunicado.",
        "citacoes": [{"chunk_id": "ACV-09-p0-s3-c1",
                      "trecho": "A participação é obrigatória para os alunos matriculados"}],
        "prevalencia": {"item": None, "escopo_aplicado": "", "documentos_considerados": ["ACV-09"],
                        "resolvida": True},
    }
    _preparar(monkeypatch, ["ACV-09-p0-s3-c1", "ACV-09-p0-s4-c1"], [resposta])

    resultado = rf19.responder_rf19("A pesquisa socioeconômica é obrigatória?")

    assert resultado["status"] == "fundamentada"
    assert resultado["decisao"] == "revisar"
    assert resultado["alertas"]