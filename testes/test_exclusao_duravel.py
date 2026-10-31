"""Exclusão que dura e restauração, pelo terminal e pela tela (RF24, T14).

Rodam offline: codificador falso, índice numa pasta temporária e registro de
exclusões temporário (conftest). Nada toca o índice nem o registro reais.
"""

import json
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src import audit, rag, vector_store
from src.acervo_operacao import indexar_ids, situacao_do_indice
from src.consulta_acervo import opcoes_de_exclusao, preparar_acervo
from src.indexar import excluir_e_registrar, indexar_acervo, main as indexar_main, restaurar_e_registrar
from src.ingestion import (
    PASTA_ACERVO,
    carregar_catalogo,
    carregar_exclusoes,
    gravar_exclusoes,
    registrar_exclusao,
    validar_documentos,
)
from src.vector_store import conferir_indice, obter_colecao
from testes.test_rf17_indice import CodificadorFalso


@pytest.fixture()
def registro(tmp_path, monkeypatch):
    arquivo = tmp_path / "execucoes.jsonl"
    monkeypatch.setattr(audit, "ARQUIVO_REGISTRO", arquivo)
    return arquivo


@pytest.fixture()
def indice(tmp_path, monkeypatch):
    """Índice temporário com o acervo real, no lugar do índice real."""
    pasta = tmp_path / "indice"
    monkeypatch.setattr(vector_store, "PASTA_INDICE", pasta)
    colecao = obter_colecao(pasta=pasta)
    indexar_acervo(CodificadorFalso(), colecao, catalogo=carregar_catalogo())
    return colecao


def _eventos(registro, nome):
    linhas = registro.read_text(encoding="utf-8").splitlines()
    return [e for e in map(json.loads, linhas) if e["evento"] == nome]


def _trechos(colecao, doc_id):
    return colecao.get(where={"doc_id": doc_id})["ids"]


# Terminal e funções

def test_excluir_registra_data_motivo_e_responsavel(indice, registro):
    resultado = excluir_e_registrar(indice, "ACV-09", "retenção encerrada", responsavel="Ana")

    registro_exclusao = carregar_exclusoes()["ACV-09"]
    evento = _eventos(registro, "exclusao_documento")[0]

    assert resultado["chunks_removidos"] == 5
    assert _trechos(indice, "ACV-09") == []
    assert registro_exclusao["motivo"] == "retenção encerrada"
    assert registro_exclusao["responsavel"] == "Ana"
    assert registro_exclusao["data"]
    assert evento["responsavel"] == "Ana"


def test_reindexar_nao_traz_o_excluido_de_volta(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")
    total = indice.count()

    relatorio = indexar_acervo(CodificadorFalso(), indice, catalogo=carregar_catalogo())

    assert {"doc_id": "ACV-09", "status": "excluido", "chunks": 0,
            "motivo": "retenção encerrada"} in relatorio
    assert _trechos(indice, "ACV-09") == []
    assert indice.count() == total


def test_indexar_tira_o_excluido_que_ficou_no_indice(indice):
    registrar_exclusao("ACV-09", "retenção encerrada", "Ana")
    catalogo = carregar_catalogo()

    assert not conferir_indice(catalogo, indice, carregar_exclusoes())["completo"]

    indexar_acervo(CodificadorFalso(), indice, catalogo=catalogo)

    assert _trechos(indice, "ACV-09") == []
    assert conferir_indice(catalogo, indice, carregar_exclusoes())["completo"]


def test_restaurar_volta_ao_indice_e_registra(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")

    resultado = restaurar_e_registrar(indice, "ACV-09", CodificadorFalso(), responsavel="Ana")
    evento = _eventos(registro, "restauracao_documento")[0]

    assert resultado["chunks"] == 5
    assert len(_trechos(indice, "ACV-09")) == 5
    assert carregar_exclusoes() == {}
    assert evento["responsavel"] == "Ana"
    assert evento["motivo_da_exclusao"] == "retenção encerrada"


def test_restaurar_documento_que_nao_esta_excluido_da_erro(indice):
    with pytest.raises(ValueError, match="não está excluído"):
        restaurar_e_registrar(indice, "ACV-09", CodificadorFalso())


@pytest.mark.parametrize("doc_id, motivo, mensagem", [
    ("ACV-99", "retenção encerrada", "não está no catálogo"),
    ("ACV-09", "   ", "Informe o motivo"),
])
def test_exclusao_invalida_nao_muda_nada(indice, doc_id, motivo, mensagem):
    total = indice.count()

    with pytest.raises(ValueError, match=mensagem):
        excluir_e_registrar(indice, doc_id, motivo)

    assert carregar_exclusoes() == {}
    assert indice.count() == total


def test_excluir_duas_vezes_nao_duplica(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")

    with pytest.raises(ValueError, match="já está excluído"):
        excluir_e_registrar(indice, "ACV-09", "outro motivo")

    assert list(carregar_exclusoes()) == ["ACV-09"]
    assert carregar_exclusoes()["ACV-09"]["motivo"] == "retenção encerrada"


def test_excluir_e_restaurar_devolve_o_registro_identico(indice, registro):
    from src import ingestion

    gravar_exclusoes({})
    inicial = ingestion.CAMINHO_EXCLUSOES.read_text(encoding="utf-8")

    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")
    restaurar_e_registrar(indice, "ACV-09", CodificadorFalso())

    assert ingestion.CAMINHO_EXCLUSOES.read_text(encoding="utf-8") == inicial
    # O arquivo do repositório está no mesmo formato: excluir e restaurar não deixa diferença no git.
    assert (PASTA_ACERVO / "exclusoes.json").read_text(encoding="utf-8") == inicial


def test_excluir_pelo_terminal_exige_motivo(tmp_path, capsys):
    with pytest.raises(SystemExit) as saida:
        indexar_main(["--excluir", "ACV-09", "--pasta", str(tmp_path / "indice")])

    assert saida.value.code == 2
    assert "--motivo" in capsys.readouterr().err
    assert carregar_exclusoes() == {}


# Conferência, consulta e indexação pela tela

def test_conferencia_libera_e_mostra_data_e_motivo(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")
    catalogo = carregar_catalogo()

    conferencia = situacao_do_indice()
    linhas = preparar_acervo(catalogo, validar_documentos(catalogo), conferencia)
    acv09 = next(linha for linha in linhas if linha["doc_id"] == "ACV-09")
    ativos, excluidos = opcoes_de_exclusao(linhas)

    assert conferencia["completo"]
    assert acv09["texto_indice"].startswith("Índice: excluído em ")
    assert acv09["texto_indice"].endswith("(motivo: retenção encerrada)")
    assert excluidos == ["ACV-09"]
    assert "ACV-09" not in ativos


def test_consulta_nao_bloqueia_e_nao_traz_o_excluido(indice, registro, monkeypatch):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")
    monkeypatch.setattr(rag, "carregar_modelo_embeddings", CodificadorFalso)

    evidencias = rag.recuperar_evidencias("pesquisa socioeconômica dos alunos", top_k=100)

    assert evidencias
    assert all(e["metadados"]["doc_id"] != "ACV-09" for e in evidencias)


def test_indexar_selecionados_pula_o_excluido(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")

    with patch("src.vector_store.carregar_modelo_embeddings", CodificadorFalso):
        relatorio = indexar_ids(["ACV-09"])

    assert relatorio["itens"] == [{"doc_id": "ACV-09", "status": "excluido", "chunks": 0}]
    assert _trechos(indice, "ACV-09") == []


# Tela Acervo

def _abrir_acervo():
    tela = AppTest.from_string(
        "from src.interface import renderizar\nrenderizar()\n", default_timeout=30
    )
    tela.run()
    tela.sidebar.radio(key="rf20_area").set_value("acervo").run()
    assert not tela.exception
    return tela


def _texto(colecao):
    return "\n".join(item.value for item in colecao)


def test_tela_exclui_so_com_responsavel_motivo_e_confirmacao(indice, registro):
    tela = _abrir_acervo()
    tela.selectbox(key="rf20_excluir_id").set_value("ACV-09").run()

    tela.button(key="rf20_excluir").click().run()
    assert "Informe o(a) servidor(a) responsável" in _texto(tela.error)

    tela.text_input(key="rf20_excluir_responsavel").input("Ana").run()
    tela.button(key="rf20_excluir").click().run()
    assert "Informe o motivo da exclusão." in _texto(tela.error)

    tela.text_input(key="rf20_excluir_motivo").input("retenção encerrada").run()
    tela.button(key="rf20_excluir").click().run()
    assert "Marque a confirmação para excluir ACV-09." in _texto(tela.error)
    assert carregar_exclusoes() == {}

    tela.checkbox(key="rf20_excluir_confirma").check().run()
    tela.button(key="rf20_excluir").click().run()

    sucesso = _texto(tela.success)
    assert "ACV-09 excluído do índice (5 trechos removidos)." in sucesso
    assert "1 excluído(s)" in sucesso
    assert carregar_exclusoes()["ACV-09"]["responsavel"] == "Ana"
    assert tela.selectbox(key="rf20_restaurar_id").options == ["ACV-09"]
    assert "ACV-09" not in tela.selectbox(key="rf20_excluir_id").options
    assert tela.text_input(key="rf20_excluir_motivo").value == ""


def test_tela_restaura_com_responsavel(indice, registro):
    excluir_e_registrar(indice, "ACV-09", "retenção encerrada")
    tela = _abrir_acervo()

    with patch("src.vector_store.carregar_modelo_embeddings", CodificadorFalso):
        tela.button(key="rf20_restaurar").click().run()
        assert "Informe o(a) servidor(a) responsável pela restauração." in _texto(tela.error)

        tela.text_input(key="rf20_restaurar_responsavel").input("Ana").run()
        tela.button(key="rf20_restaurar").click().run()

    assert "ACV-09 restaurado e indexado (5 trechos)." in _texto(tela.success)
    assert carregar_exclusoes() == {}
    assert len(_trechos(indice, "ACV-09")) == 5
