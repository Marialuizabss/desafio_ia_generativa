"""Conferência catálogo × índice antes da consulta (RF17, RF19 e RF20).

Rodam offline: o índice fica numa pasta temporária com vetores falsos, nenhum
modelo de embeddings é carregado e o índice real não é tocado.
"""

import json
from unittest.mock import patch

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from src import audit, rag, vector_store
from src.acervo_operacao import remover_do_indice
from src.consulta_acervo import (
    classificar_consulta,
    pendentes_de_indexar,
    pendentes_de_remover,
    preparar_acervo,
    resumo_do_indice,
)
from src.indexar import main as indexar_main
from src.ingestion import carregar_catalogo
from src.vector_store import (
    DIMENSAO_EMBEDDINGS,
    IndiceDesatualizadoError,
    IndiceIncompletoError,
    conferir_indice,
    mensagem_de_pendencias,
    obter_colecao,
    obter_colecao_se_existir,
)

CATALOGO = {"documentos": [
    {"doc_id": "ACV-01", "sha256": "h1", "titulo": "Edital"},
    {"doc_id": "ACV-02", "sha256": "h2", "titulo": "Retificação nº 01"},
    {"doc_id": "ACV-03", "sha256": "h3", "titulo": "Retificação nº 02"},
]}


def _vetor():
    vetor = [0.0] * DIMENSAO_EMBEDDINGS
    vetor[0] = 1.0
    return vetor


def _indexar(colecao, doc_id, sha256, chunks=2):
    colecao.upsert(
        ids=[f"{doc_id}-c{i}" for i in range(chunks)],
        embeddings=[_vetor() for _ in range(chunks)],
        documents=[f"trecho {i} de {doc_id}" for i in range(chunks)],
        metadatas=[{
            "doc_id": doc_id, "titulo": doc_id, "versao": "1",
            "sha256": sha256, "pagina": 1, "secao": "",
        } for _ in range(chunks)],
    )


def _indice_com_o_catalogo_real(pasta):
    colecao = obter_colecao(pasta=pasta)
    for documento in carregar_catalogo()["documentos"]:
        _indexar(colecao, documento["doc_id"], documento["sha256"])
    return colecao


class CodificadorFalso:
    def encode(self, textos):
        return np.array([_vetor() for _ in textos], dtype="float32")


@pytest.fixture
def colecao(tmp_path):
    return obter_colecao(pasta=tmp_path / "indice")


# Conferência e mensagem

def test_indice_vazio_bloqueia_e_diz_o_que_fazer_na_interface(colecao):
    conferencia = conferir_indice(CATALOGO, colecao)

    assert not conferencia["completo"]
    assert conferencia["vazio"]
    assert {d["situacao"] for d in conferencia["documentos"]} == {"nao_indexado"}

    mensagem = mensagem_de_pendencias(conferencia)
    assert mensagem.startswith("O índice está vazio")
    assert '"Indexar selecionados"' in mensagem
    assert "terminal" not in mensagem and "python" not in mensagem


def test_pasta_inexistente_conta_como_vazio_sem_criar_o_indice(tmp_path):
    pasta = tmp_path / "nao_existe"

    assert obter_colecao_se_existir(pasta) is None
    assert conferir_indice(CATALOGO, None)["vazio"]
    assert not pasta.exists()


def test_indice_completo_libera_a_consulta(colecao):
    for documento in CATALOGO["documentos"]:
        _indexar(colecao, documento["doc_id"], documento["sha256"])

    conferencia = conferir_indice(CATALOGO, colecao)

    assert conferencia["completo"]
    assert conferencia["total_chunks"] == 6
    assert mensagem_de_pendencias(conferencia) == ""


def test_indice_parcial_lista_os_documentos_que_faltam(colecao):
    # Edital sem as retificações: a resposta sairia com a regra antiga.
    _indexar(colecao, "ACV-01", "h1")

    conferencia = conferir_indice(CATALOGO, colecao)
    mensagem = mensagem_de_pendencias(conferencia)

    assert [p["doc_id"] for p in conferencia["pendencias"]] == ["ACV-02", "ACV-03"]
    assert mensagem.startswith("O índice está incompleto: ACV-02 não indexado; ACV-03 não indexado.")
    assert '"Indexar selecionados"' in mensagem


def test_hash_diferente_do_catalogo_e_desatualizado(colecao):
    _indexar(colecao, "ACV-01", "hash-antigo")
    _indexar(colecao, "ACV-02", "h2")
    _indexar(colecao, "ACV-03", "h3")

    conferencia = conferir_indice(CATALOGO, colecao)

    assert conferencia["pendencias"] == [
        {"doc_id": "ACV-01", "situacao": "desatualizado", "chunks": 2}
    ]
    assert "ACV-01 desatualizado" in mensagem_de_pendencias(conferencia)


def test_documento_fora_do_catalogo_pede_remocao(colecao):
    for documento in CATALOGO["documentos"]:
        _indexar(colecao, documento["doc_id"], documento["sha256"])
    _indexar(colecao, "ACV-10", "h10")

    conferencia = conferir_indice(CATALOGO, colecao)
    mensagem = mensagem_de_pendencias(conferencia)

    assert conferencia["pendencias"][0]["situacao"] == "fora_do_catalogo"
    assert mensagem.startswith("O índice tem documento que não deveria estar nele")
    assert '"Remover do índice" ao lado de ACV-10' in mensagem
    assert "Indexar selecionados" not in mensagem


def test_pendencias_misturadas_pedem_as_duas_acoes(colecao):
    _indexar(colecao, "ACV-01", "h1")
    _indexar(colecao, "ACV-02", "h2")
    _indexar(colecao, "ACV-10", "h10")

    mensagem = mensagem_de_pendencias(conferir_indice(CATALOGO, colecao))

    assert '"Indexar selecionados"' in mensagem
    assert '"Remover do índice" ao lado de ACV-10' in mensagem


def test_excluido_de_proposito_nao_bloqueia(colecao):
    _indexar(colecao, "ACV-01", "h1")
    _indexar(colecao, "ACV-02", "h2")

    conferencia = conferir_indice(CATALOGO, colecao, excluidos={"ACV-03"})

    assert conferencia["completo"]
    assert conferencia["documentos"][2]["situacao"] == "excluido"


def test_excluido_que_continua_no_indice_bloqueia(colecao):
    for documento in CATALOGO["documentos"]:
        _indexar(colecao, documento["doc_id"], documento["sha256"])

    conferencia = conferir_indice(CATALOGO, colecao, excluidos={"ACV-03"})

    assert not conferencia["completo"]
    assert conferencia["pendencias"][0]["situacao"] == "excluido_no_indice"


# Recuperação

def test_recuperar_evidencias_bloqueia_sem_carregar_o_modelo(tmp_path, monkeypatch):
    pasta = tmp_path / "nao_existe"
    monkeypatch.setattr(vector_store, "PASTA_INDICE", pasta)

    def nao_pode_carregar():
        raise AssertionError("o modelo não deveria ser carregado")

    monkeypatch.setattr(rag, "carregar_modelo_embeddings", nao_pode_carregar)

    with pytest.raises(IndiceIncompletoError) as erro:
        rag.recuperar_evidencias("Quando começam as aulas de Agropecuária em Mimoso?")

    assert isinstance(erro.value, IndiceDesatualizadoError)
    assert str(erro.value).startswith("O índice está vazio")
    assert not pasta.exists()


def test_auditoria_sem_indice_nao_cria_a_pasta(tmp_path, monkeypatch):
    from src.auditoria_rag import versao_indice_atual

    pasta = tmp_path / "nao_existe"
    monkeypatch.setattr(vector_store, "PASTA_INDICE", pasta)

    assert versao_indice_atual() is None
    assert not pasta.exists()


def test_recuperar_evidencias_com_indice_completo_busca(tmp_path, monkeypatch):
    pasta = tmp_path / "indice"
    _indice_com_o_catalogo_real(pasta)
    monkeypatch.setattr(vector_store, "PASTA_INDICE", pasta)
    monkeypatch.setattr(rag, "carregar_modelo_embeddings", CodificadorFalso)

    evidencias = rag.recuperar_evidencias("Quando começam as aulas?", top_k=3)

    assert len(evidencias) == 3


def test_consulta_bloqueada_mostra_o_motivo_sem_abrir_decisao():
    mensagem = "O índice está incompleto: ACV-04 não indexado. Para consultar, vá à tela Acervo."
    saida = classificar_consulta(erro=IndiceIncompletoError(mensagem))

    assert saida["tipo"] == "indice_desatualizado"
    assert saida["texto"] == mensagem
    assert saida["resposta"] is None
    assert saida["estado"] is None


# Tela Acervo

def test_selos_resumo_e_pendentes_da_tela_acervo(colecao):
    _indexar(colecao, "ACV-01", "h1", chunks=12)
    _indexar(colecao, "ACV-10", "h10")
    conferencia = conferir_indice(CATALOGO, colecao)
    validacoes = [{"doc_id": d["doc_id"], "status": "valido"} for d in CATALOGO["documentos"]]

    linhas = preparar_acervo(CATALOGO, validacoes, conferencia)

    assert linhas[0]["texto_indice"] == "Índice: indexado (12 trechos)"
    assert linhas[1]["indice"] == "nao_indexado"
    assert resumo_do_indice(conferencia).startswith("Índice incompleto: 3 pendência(s).")
    assert pendentes_de_indexar(conferencia) == ["ACV-02", "ACV-03"]
    assert [item["doc_id"] for item in pendentes_de_remover(conferencia)] == ["ACV-10"]


def test_resumo_do_indice_completo_conta_trechos_e_excluidos(colecao):
    _indexar(colecao, "ACV-01", "h1")
    _indexar(colecao, "ACV-02", "h2")

    conferencia = conferir_indice(CATALOGO, colecao, excluidos={"ACV-03"})

    assert resumo_do_indice(conferencia) == (
        "Índice: 4 trechos · 2 de 2 documentos indexados · 1 excluído(s)"
    )


def test_tela_acervo_avisa_e_ja_marca_os_pendentes(tmp_path, monkeypatch):
    colecao = obter_colecao(pasta=tmp_path / "indice")
    _indexar(colecao, "ACV-01", carregar_catalogo()["documentos"][0]["sha256"])
    _indexar(colecao, "ACV-10", "h10")
    conferencia = conferir_indice(carregar_catalogo(), colecao)
    monkeypatch.setattr(audit, "ARQUIVO_REGISTRO", tmp_path / "execucoes.jsonl")

    with patch("src.acervo_operacao.situacao_do_indice", return_value=conferencia):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n", default_timeout=20
        )
        tela.run()
        tela.sidebar.radio(key="rf20_area").set_value("acervo").run()

    assert not tela.exception
    avisos = "\n".join(item.value for item in tela.warning)
    assert "Índice incompleto" in avisos
    assert "Índice: não indexado" in avisos
    assert "ACV-10: está no índice, mas não no catálogo." in avisos
    assert tela.multiselect(key="rf20_indexar_ids").value[0] == "ACV-02"
    assert "ACV-01" not in tela.multiselect(key="rf20_indexar_ids").value
    assert tela.button(key="rf20_remover_ACV-10").label == "Remover do índice"


def test_remover_do_indice_so_aceita_o_que_a_conferencia_aponta(tmp_path, monkeypatch):
    pasta = tmp_path / "indice"
    colecao = _indice_com_o_catalogo_real(pasta)
    _indexar(colecao, "ACV-10", "h10")
    log = tmp_path / "execucoes.jsonl"
    monkeypatch.setattr(vector_store, "PASTA_INDICE", pasta)
    monkeypatch.setattr(audit, "ARQUIVO_REGISTRO", log)

    with pytest.raises(ValueError):
        remover_do_indice("ACV-01")

    resultado = remover_do_indice("ACV-10")
    evento = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])

    assert resultado["chunks_removidos"] == 2
    assert evento["evento"] == "remocao_do_indice"
    assert evento["motivo"] == "fora_do_catalogo"
    assert conferir_indice(carregar_catalogo(), colecao)["completo"]


# Terminal

def test_status_do_indexar_traz_a_conferencia(tmp_path, capsys):
    indexar_main(["--status", "--pasta", str(tmp_path / "indice")])

    saida = json.loads(capsys.readouterr().out)

    assert saida["conferencia"]["vazio"]
    assert not saida["conferencia"]["completo"]
