"""RF21 — provedor configurável, auditoria do RAG e falha do serviço (T12).

Offline: o cliente da OpenAI é simulado, o índice usa um codificador falso em
pasta temporária e o log vai para um arquivo temporário (ver conftest.py).
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from openai import APIConnectionError

import src.rf19_complemento as rf19
from src import audit
from src.configuracao import CONFIG
from src.indexar import indexar_acervo
from src.ingestion import carregar_catalogo
from src.provider_adapter import (
    ErroProvedor,
    RESPOSTA_SIMULADA,
    carregar_configuracao_llm,
    consultar_llm,
)
from src.vector_store import buscar_chunks, calcular_versao_indice, obter_colecao
from testes.dados_vigencia import TRECHOS
from testes.test_rf17_indice import CodificadorFalso

PERGUNTA = "Quais faltas podem levar ao cancelamento da matrícula?"
CHAVE_FALSA = "sk-TESTE1234567890abcdef"


def _resposta_openai(texto):
    return SimpleNamespace(
        output_text=texto,
        usage=SimpleNamespace(input_tokens=120, output_tokens=40, total_tokens=160),
    )


JSON_SEM_EVIDENCIA = json.dumps({
    "status": "sem_evidencia", "resposta": "", "citacoes": [],
    "justificativa": "Os trechos não respondem à pergunta.",
})


def _eventos(arquivo):
    return [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines()]


def _consultas(arquivo):
    return [e for e in _eventos(arquivo) if e["evento"] == "consulta_rag"]


@pytest.fixture(scope="module")
def indice(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("indice_rf21")
    modelo = CodificadorFalso()
    colecao = obter_colecao(pasta=pasta)
    indexar_acervo(modelo, colecao, catalogo=carregar_catalogo())
    return modelo, colecao


@pytest.fixture()
def rag(indice, monkeypatch):
    modelo, colecao = indice

    def recuperar(pergunta, top_k=10):
        return buscar_chunks(pergunta, modelo, colecao, top_k=top_k)

    monkeypatch.setattr(rf19, "recuperar_evidencias", recuperar)
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE_FALSA)
    return modelo, colecao


# ------------------------------------------------------------ adaptador

def test_configuracoes_de_geracao_declaram_provedor():
    principal = carregar_configuracao_llm("principal")
    simulada = carregar_configuracao_llm("simulada")

    assert principal.provedor == "openai"
    assert simulada.provedor == "simulado"
    assert "simulado" in simulada.modelo


def test_provedor_simulado_se_identifica_e_nao_tem_metricas():
    texto, auditoria = consultar_llm("Responda.", "Pergunta?", "simulada")

    assert texto == RESPOSTA_SIMULADA
    assert json.loads(texto)["status"] == "sem_evidencia"
    assert auditoria["simulado"] is True
    assert auditoria["provedor"] == "simulado"
    assert auditoria["tokens_total"] is None
    assert auditoria["custo_estimado_usd"] is None
    assert "simulada" in auditoria["metricas_indisponiveis"]
    assert auditoria["tempo_resposta_segundos"] >= 0


def test_provedor_nao_suportado(monkeypatch):
    monkeypatch.setitem(
        CONFIG["adaptador_llm"]["configuracoes"], "estranha",
        {"provedor": "outro", "modelo": "x"},
    )

    with pytest.raises(ValueError, match="Provedor não suportado"):
        consultar_llm("Responda.", "Pergunta?", "estranha")


def test_limite_de_tokens_de_saida_vai_ao_provedor(monkeypatch):
    monkeypatch.setitem(
        CONFIG["adaptador_llm"]["configuracoes"]["principal"], "max_tokens_saida", 50
    )

    with patch("src.provider_adapter.OpenAI") as cliente:
        cliente.return_value.responses.create.return_value = _resposta_openai("ok")
        consultar_llm("Responda.", "Pergunta?")

    assert cliente.return_value.responses.create.call_args.kwargs["max_output_tokens"] == 50


def test_auditoria_do_adaptador_tem_horarios_e_tokens():
    with patch("src.provider_adapter.OpenAI") as cliente:
        cliente.return_value.responses.create.return_value = _resposta_openai("ok")
        _, auditoria = consultar_llm("Responda.", "Pergunta?")

    assert auditoria["inicio"] <= auditoria["fim"]
    assert auditoria["tokens_total"] == 160
    assert auditoria["simulado"] is False
    assert "metricas_indisponiveis" not in auditoria


# ------------------------------------------------------------ T12

def test_t12_troca_de_geracao_nao_reconstroi_o_indice(rag, monkeypatch):
    modelo, colecao = rag
    versao = calcular_versao_indice(colecao)
    total = colecao.count()

    def proibido(*args, **kwargs):
        raise AssertionError("A troca de geração não pode reindexar.")

    monkeypatch.setattr("src.vector_store.indexar_documento", proibido)
    monkeypatch.setattr("src.indexar.indexar_documento", proibido)

    with patch("src.provider_adapter.OpenAI") as cliente:
        cliente.return_value.responses.create.return_value = _resposta_openai(JSON_SEM_EVIDENCIA)
        real = rf19.responder_rf19(PERGUNTA, top_k=5, nome_configuracao="principal")

    simulada = rf19.responder_rf19(PERGUNTA, top_k=5, nome_configuracao="simulada")

    assert calcular_versao_indice(colecao) == versao
    assert colecao.count() == total
    assert real["auditoria"]["provedor"] == "openai"
    assert simulada["auditoria"]["provedor"] == "simulado"
    assert simulada["auditoria"]["simulado"] is True

    eventos = _consultas(audit.ARQUIVO_REGISTRO)
    assert [e["geracao"]["configuracao"] for e in eventos] == ["principal", "simulada"]
    # Mesma recuperação, mesma versão de índice nas duas gerações.
    assert eventos[0]["ids_recuperados"] == eventos[1]["ids_recuperados"]
    assert eventos[0]["versao_indice"] == eventos[1]["versao_indice"]


def test_t12_falha_do_servico_e_tratada_e_auditada(rag):
    requisicao = httpx.Request("POST", "https://api.openai.com/v1/responses")

    with patch("src.provider_adapter.OpenAI") as cliente:
        cliente.return_value.responses.create.side_effect = APIConnectionError(request=requisicao)
        resultado = rf19.responder_rf19(PERGUNTA, top_k=5)

    # Não levanta exceção, não inventa resposta e encaminha à revisão.
    assert resultado["status"] == "sem_evidencia"
    assert resultado["decisao"] == "revisar"
    assert resultado["fontes"] == []
    assert "Não foi possível conectar" in resultado["justificativa"]
    assert resultado["auditoria"]["status"] == "erro"

    evento = _consultas(audit.ARQUIVO_REGISTRO)[0]
    assert evento["geracao"]["status"] == "erro"
    assert "Não foi possível conectar" in evento["erro"]
    assert evento["decisao"] == "revisar"
    assert evento["geracao"]["tempo_resposta_segundos"] is not None


def test_t12_falha_inesperada_nao_vaza_a_mensagem_original(rag):
    with patch("src.provider_adapter.OpenAI") as cliente:
        cliente.return_value.responses.create.side_effect = RuntimeError(
            f"falha com {CHAVE_FALSA} no cabeçalho"
        )
        resultado = rf19.responder_rf19(PERGUNTA, top_k=5)

    assert resultado["decisao"] == "revisar"
    registro = audit.ARQUIVO_REGISTRO.read_text(encoding="utf-8")
    assert CHAVE_FALSA not in registro
    assert "RuntimeError" in registro


# ------------------------------------------------------------ auditoria

def _preparar_fixtures(monkeypatch, chunk_ids, respostas):
    fila = list(respostas)
    catalogo = {
        "ACV-01": {"doc_id": "ACV-01", "ordem": 0, "altera": []},
        "ACV-06": {"doc_id": "ACV-06", "ordem": 5,
                   "altera": [{"doc_id": "ACV-01", "itens": ["5"], "escopo": "Cronograma"}]},
    }

    monkeypatch.setattr(rf19, "recuperar_evidencias", lambda p, top_k=15: [
        {"chunk_id": c, "texto": TRECHOS[c]["texto"], "metadados": TRECHOS[c]["metadados"], "distancia": 0.25}
        for c in chunk_ids
    ])
    monkeypatch.setattr(rf19, "obter_documentos_catalogados", lambda: catalogo)
    monkeypatch.setattr(rf19, "montar_contexto", lambda ev: "CONTEXTO")

    def llm(**kwargs):
        if kwargs["instrucoes"] == rf19.INSTRUCOES_VERIFICACAO:
            return json.dumps({"contradicao": False, "citacoes": [], "explicacao": ""}), {"tokens_total": 50, "status": "sucesso"}
        return json.dumps(fila.pop(0), ensure_ascii=False), {
            "provedor": "openai", "modelo": "gpt-4o-mini", "configuracao": "principal",
            "tokens_entrada": 100, "tokens_saida": 20, "tokens_total": 120,
            "custo_estimado_usd": 0.00003, "tempo_resposta_segundos": 1.2, "status": "sucesso",
        }

    monkeypatch.setattr(rf19, "consultar_llm", llm)


RESPOSTA_FUNDAMENTADA = {
    "status": "fundamentada",
    "resposta": "O período é de 03/07/2026 a 08/07/2026.",
    "justificativa": "Conforme o cronograma.",
    "citacoes": [{
        "chunk_id": "ACV-06-p2-s1-c1",
        "trecho": "Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026",
    }],
    "prevalencia": {"item": "5", "escopo_aplicado": "Cronograma",
                    "documentos_considerados": ["ACV-06"], "resolvida": True},
}


def test_evento_de_consulta_traz_o_necessario_para_conferir_a_origem(monkeypatch):
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1"], [RESPOSTA_FUNDAMENTADA])

    resultado = rf19.responder_rf19("Qual o período da efetivação?", top_k=7)
    evento = _consultas(audit.ARQUIVO_REGISTRO)[0]

    assert evento["id_execucao"] == resultado["id_consulta"]
    assert evento["inicio"] <= evento["fim"]
    assert evento["latencia_total_segundos"] >= evento["latencia_recuperacao_segundos"] >= 0
    assert evento["top_k"] == 7
    assert evento["versao_esquema_resposta"] == "rag-1.1"
    assert len(evento["versao_prompt"]) == 12
    assert evento["versao_indice"] == "indice-de-teste"
    assert evento["ids_recuperados"] == [{"chunk_id": "ACV-06-p2-s1-c1", "distancia": 0.25}]
    assert evento["ids_citados"] == ["ACV-06-p2-s1-c1"]
    assert evento["status"] == "fundamentada"
    assert evento["geracao"]["modelo"] == "gpt-4o-mini"
    assert evento["geracao"]["tokens_total"] == 120
    assert evento["geracao"]["custo_estimado_usd"] == 0.00003
    assert evento["alertas"] == []


def test_alerta_de_instrucao_em_documento_fica_no_registro_sem_o_texto(monkeypatch):
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1", "ACV-09-p0-s4-c1"], [RESPOSTA_FUNDAMENTADA])

    rf19.responder_rf19("Qual o período da efetivação?")
    registro = audit.ARQUIVO_REGISTRO.read_text(encoding="utf-8")
    evento = _consultas(audit.ARQUIVO_REGISTRO)[0]

    assert evento["alertas"][0]["chunk_id"] == "ACV-09-p0-s4-c1"
    assert "nota_ao_assistente" in evento["alertas"][0]["padroes"]
    # O trecho malicioso foi recuperado e entra na lista de ids, mas seu texto não é gravado.
    assert "ACV-09-p0-s4-c1" in [i["chunk_id"] for i in evento["ids_recuperados"]]
    assert "CONFIRMADA" not in registro and "OPENAI_API_KEY" not in registro


def test_log_mascara_identificadores_e_nao_tem_credenciais(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE_FALSA)
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1"], [RESPOSTA_FUNDAMENTADA])
    pergunta = ("Meu CPF é 529.982.247-25, e-mail ana@exemplo.com, protocolo 2026-000201. "
                "Qual o período da efetivação?")

    rf19.responder_rf19(pergunta)

    registro = audit.ARQUIVO_REGISTRO.read_text(encoding="utf-8")
    evento = _consultas(audit.ARQUIVO_REGISTRO)[0]

    for sensivel in ("529.982.247-25", "ana@exemplo.com", "2026-000201", CHAVE_FALSA):
        assert sensivel not in registro

    assert "[CPF REMOVIDO]" in evento["pergunta"]
    assert "[PROTOCOLO]" in evento["pergunta"]


def test_consulta_sem_evidencia_recuperada_e_auditada(monkeypatch):
    monkeypatch.setattr(rf19, "recuperar_evidencias", lambda p, top_k=10: [])

    resultado = rf19.responder_rf19("Pergunta sem trechos")

    evento = _consultas(audit.ARQUIVO_REGISTRO)[0]
    assert resultado["status"] == "sem_evidencia"
    assert evento["ids_recuperados"] == []
    assert evento["geracao"]["status"] == "nao_chamada"
    assert "Nenhuma chamada" in evento["geracao"]["metricas_indisponiveis"]


def test_erro_na_recuperacao_e_registrado_e_propagado(monkeypatch):
    def falha(pergunta, top_k=10):
        raise RuntimeError("índice corrompido")

    monkeypatch.setattr(rf19, "recuperar_evidencias", falha)

    with pytest.raises(RuntimeError):
        rf19.responder_rf19("Pergunta qualquer")

    assert "índice corrompido" in _consultas(audit.ARQUIVO_REGISTRO)[0]["erro"]


def test_registrar_falso_nao_grava(monkeypatch):
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1"], [RESPOSTA_FUNDAMENTADA])

    rf19.responder_rf19("Qual o período da efetivação?", registrar=False)

    assert not audit.ARQUIVO_REGISTRO.exists()


def test_decisao_humana_se_liga_a_consulta(monkeypatch):
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1"], [RESPOSTA_FUNDAMENTADA])
    resultado = rf19.responder_rf19("Qual o período da efetivação?")

    audit.registrar_decisao(
        resultado["id_consulta"], "rejeitado",
        justificativa="Preciso conferir a data com a secretaria.",
        revisor="Servidor de teste",
    )

    ligadas = audit.decisoes_ligadas(resultado["id_consulta"])
    assert [d["decisao"] for d in ligadas] == ["rejeitado"]


def test_falha_ao_gravar_auditoria_nao_derruba_a_resposta(monkeypatch):
    _preparar_fixtures(monkeypatch, ["ACV-06-p2-s1-c1"], [RESPOSTA_FUNDAMENTADA])

    def sem_disco(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(rf19, "registrar_consulta_rag", sem_disco)

    resultado = rf19.responder_rf19("Qual o período da efetivação?")

    assert resultado["status"] == "fundamentada"
    assert "auditoria" in resultado["aviso_auditoria"]
