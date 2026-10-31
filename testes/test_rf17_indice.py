"""Testes do índice vetorial (RF17: T06) e da exclusão de documento (RF24: T14).

Rodam offline: usam um codificador determinístico no lugar do modelo de
embeddings e uma pasta temporária no lugar do índice real. O que se valida é o
comportamento do índice (persistência, ausência de duplicatas, rastreabilidade,
troca de modelo e exclusão), não a qualidade semântica do modelo.
"""

import copy
import hashlib
import json
import re

import numpy as np
import pytest

from src import audit
from src.indexar import excluir_e_registrar, indexar_acervo, localizar_derivados
from src.ingestion import carregar_catalogo
from src.vector_store import (
    DIMENSAO_EMBEDDINGS,
    IndiceDesatualizadoError,
    buscar_chunks,
    calcular_versao_indice,
    excluir_documento,
    listar_documentos_indexados,
    obter_colecao,
)


class CodificadorFalso:
    """Bag-of-words por hash, normalizado. Determinístico e sem rede."""

    def __init__(self, dimensao=DIMENSAO_EMBEDDINGS):
        self.dimensao = dimensao
        self.chamadas = 0

    def encode(self, textos):
        self.chamadas += 1
        vetores = np.zeros((len(textos), self.dimensao), dtype="float32")

        for i, texto in enumerate(textos):
            for palavra in re.findall(r"\w+", texto.casefold()):
                h = int(hashlib.md5(palavra.encode()).hexdigest(), 16)
                vetores[i, h % self.dimensao] += 1.0

            norma = np.linalg.norm(vetores[i])
            if norma:
                vetores[i] /= norma

        return vetores


@pytest.fixture()
def pasta(tmp_path):
    return tmp_path / "indice"


@pytest.fixture()
def registro(tmp_path, monkeypatch):
    arquivo = tmp_path / "execucoes.jsonl"
    monkeypatch.setattr(audit, "ARQUIVO_REGISTRO", arquivo)
    return arquivo


@pytest.fixture(scope="module")
def catalogo():
    return carregar_catalogo()


def _indexar(pasta, catalogo, modelo=None):
    modelo = modelo or CodificadorFalso()
    colecao = obter_colecao(pasta=pasta)
    relatorio = indexar_acervo(modelo, colecao, catalogo=catalogo)
    return modelo, colecao, relatorio


# ---------------------------------------------------------------- T06 / RF17

def test_t06_reindexar_nao_duplica(pasta, catalogo):
    modelo, colecao, primeira = _indexar(pasta, catalogo)
    total = colecao.count()
    ids = set(colecao.get()["ids"])

    assert total > 0
    assert {r["status"] for r in primeira} == {"indexado"}

    chamadas = modelo.chamadas
    segunda = indexar_acervo(modelo, colecao, catalogo=catalogo)

    assert {r["status"] for r in segunda} == {"sem_alteracoes"}
    assert colecao.count() == total
    assert set(colecao.get()["ids"]) == ids
    assert len(ids) == total
    # Sem alteração, nem os embeddings são recalculados.
    assert modelo.chamadas == chamadas


def test_t06_indice_reutilizado_apos_reinicio(pasta, catalogo):
    modelo, colecao, _ = _indexar(pasta, catalogo)
    total = colecao.count()
    versao = calcular_versao_indice(colecao)
    del colecao

    # "Reinício": nova conexão com a mesma pasta, sem reindexar.
    colecao2 = obter_colecao(pasta=pasta)

    assert colecao2.count() == total
    assert calcular_versao_indice(colecao2) == versao

    achados = buscar_chunks(
        "faltas nos primeiros dias de aula cancelamento da matrícula",
        modelo, colecao2, top_k=3,
    )

    assert len(achados) == 3
    assert achados[0]["metadados"]["doc_id"] == "ACV-08"

    # Rastreabilidade: documento, versão, hash, página/seção e id do trecho.
    meta = achados[0]["metadados"]
    assert {"doc_id", "versao", "sha256", "pagina", "secao", "titulo"} <= set(meta)
    assert len(meta["sha256"]) == 64
    assert achados[0]["chunk_id"].startswith("ACV-08-")

    # Reindexar depois do reinício também não duplica.
    indexar_acervo(modelo, colecao2, catalogo=catalogo)
    assert colecao2.count() == total


def test_t06_modelo_e_dimensao_registrados(pasta, catalogo):
    _, colecao, _ = _indexar(pasta, catalogo)

    assert colecao.metadata["dimensao"] == DIMENSAO_EMBEDDINGS
    assert "MiniLM" in colecao.metadata["modelo_embeddings"]


def test_t06_troca_de_modelo_exige_reindexacao(pasta, catalogo):
    _indexar(pasta, catalogo)

    with pytest.raises(IndiceDesatualizadoError, match="Reindexe"):
        obter_colecao(pasta=pasta, modelo_embeddings="outro/modelo")

    with pytest.raises(IndiceDesatualizadoError):
        obter_colecao(pasta=pasta, dimensao=768)


def test_indice_antigo_sem_modelo_registrado_e_atualizado(pasta):
    import chromadb

    cliente = chromadb.PersistentClient(path=str(pasta))
    antigo = cliente.get_or_create_collection(
        "acervo_ficdev", metadata={"hnsw:space": "cosine"}
    )
    antigo.add(
        ids=["X-1"],
        embeddings=[[0.1] * DIMENSAO_EMBEDDINGS],
        documents=["trecho"],
        metadatas=[{"doc_id": "X"}],
    )

    colecao = obter_colecao(pasta=pasta)

    assert colecao.metadata["dimensao"] == DIMENSAO_EMBEDDINGS
    assert colecao.count() == 1


def test_documento_com_hash_divergente_nao_e_indexado(pasta, catalogo):
    adulterado = copy.deepcopy(catalogo)
    adulterado["documentos"][0]["sha256"] = "0" * 64
    doc_id = adulterado["documentos"][0]["doc_id"]

    _, colecao, relatorio = _indexar(pasta, adulterado)

    status = {r["doc_id"]: r["status"] for r in relatorio}
    assert status[doc_id] == "hash_divergente"
    assert colecao.get(where={"doc_id": doc_id})["ids"] == []


def test_topk_configuravel_e_similaridade(pasta, catalogo):
    modelo, colecao, _ = _indexar(pasta, catalogo)

    um = buscar_chunks("trancamento de matrícula", modelo, colecao, top_k=1)
    cinco = buscar_chunks("trancamento de matrícula", modelo, colecao, top_k=5)

    assert len(um) == 1 and len(cinco) == 5
    assert [c["distancia"] for c in cinco] == sorted(c["distancia"] for c in cinco)
    assert cinco[0]["similaridade"] == pytest.approx(1 - cinco[0]["distancia"], abs=1e-5)

    with pytest.raises(ValueError):
        buscar_chunks("x", modelo, colecao, top_k=0)

    with pytest.raises(ValueError):
        buscar_chunks("   ", modelo, colecao, top_k=3)


# ---------------------------------------------------------------- T14 / RF24

def test_t14_exclusao_remove_trechos_da_busca(pasta, catalogo, registro):
    modelo, colecao, _ = _indexar(pasta, catalogo)
    total = colecao.count()
    consulta = "pesquisa socioeconômica aplicação e obrigatoriedade"

    antes = buscar_chunks(consulta, modelo, colecao, top_k=total)
    docs_antes = {c["metadados"]["doc_id"] for c in antes}
    chunks_acv09 = [c for c in antes if c["metadados"]["doc_id"] == "ACV-09"]

    assert "ACV-09" in docs_antes
    assert chunks_acv09

    resultado = excluir_e_registrar(
        colecao, "ACV-09", motivo="Teste T14: documento retirado do acervo."
    )

    assert resultado["status"] == "excluido"
    assert resultado["chunks_removidos"] == len(chunks_acv09)
    assert colecao.count() == total - len(chunks_acv09)

    # Mesmo pedindo todos os resultados, nenhum trecho do ACV-09 volta.
    depois = buscar_chunks(consulta, modelo, colecao, top_k=total)
    assert all(c["metadados"]["doc_id"] != "ACV-09" for c in depois)
    assert "ACV-09" not in {d["doc_id"] for d in listar_documentos_indexados(colecao)}


def test_t14_exclusao_e_registrada_sem_texto_do_documento(pasta, catalogo, registro):
    _, colecao, _ = _indexar(pasta, catalogo)
    versao_antes = calcular_versao_indice(colecao)

    excluir_e_registrar(colecao, "ACV-09", motivo="retenção encerrada")

    eventos = [json.loads(l) for l in registro.read_text(encoding="utf-8").splitlines()]
    exclusoes = [e for e in eventos if e["evento"] == "exclusao_documento"]

    assert len(exclusoes) == 1
    evento = exclusoes[0]
    assert evento["doc_id"] == "ACV-09"
    assert evento["chunks_removidos"] > 0
    assert evento["motivo"] == "retenção encerrada"
    assert evento["data_hora"]
    assert evento["versao_indice_apos"] != versao_antes
    # O registro guarda a ocorrência, não o conteúdo excluído.
    assert "texto" not in evento and "trecho" not in evento


def test_t14_excluir_documento_inexistente(pasta, catalogo):
    _, colecao, _ = _indexar(pasta, catalogo)
    total = colecao.count()

    resultado = excluir_documento(colecao, "NAO-EXISTE")

    assert resultado["status"] == "nao_encontrado"
    assert resultado["chunks_removidos"] == 0
    assert colecao.count() == total


def test_t14_exclusao_persiste_apos_reinicio(pasta, catalogo, registro):
    _, colecao, _ = _indexar(pasta, catalogo)
    excluir_e_registrar(colecao, "ACV-08", motivo="retenção encerrada")
    del colecao

    colecao2 = obter_colecao(pasta=pasta)

    assert colecao2.get(where={"doc_id": "ACV-08"})["ids"] == []


def test_t14_localiza_derivados_que_citam_o_documento(tmp_path):
    (tmp_path / "dados" / "resultados").mkdir(parents=True)
    (tmp_path / "dados" / "resultados" / "a.json").write_text(
        '{"documentos": ["ACV-09"]}', encoding="utf-8"
    )
    (tmp_path / "dados" / "resultados" / "b.json").write_text(
        '{"documentos": ["ACV-01"]}', encoding="utf-8"
    )

    assert localizar_derivados("ACV-09", raiz=tmp_path) == ["dados/resultados/a.json"]
    assert localizar_derivados("ACV-77", raiz=tmp_path) == []