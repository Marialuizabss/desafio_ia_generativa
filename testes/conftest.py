"""Isolamento dos testes que executam o RAG.

`responder_rf19` grava a consulta na trilha de auditoria e consulta a versão do
índice. Nesses testes, o log e o índice reais não devem ser tocados.
"""

import pytest

MODULOS_COM_RAG = (
    "testes.test_rf16",
    "testes.test_rf19",
    "testes.test_rf21",
    "testes.test_vigencia",
)


@pytest.fixture(autouse=True)
def _isolar_exclusoes(tmp_path, monkeypatch):
    """Nenhum teste grava no registro real de exclusões (RF24) nem salva minuta aprovada."""
    monkeypatch.setattr("src.ingestion.CAMINHO_EXCLUSOES", tmp_path / "exclusoes.json")
    monkeypatch.setattr("src.consulta_acervo.PASTA_MINUTAS_APROVADAS", tmp_path / "minutas_rf20")


@pytest.fixture(autouse=True)
def _isolar_auditoria_e_indice(request, tmp_path, monkeypatch):
    if not request.module.__name__.startswith(MODULOS_COM_RAG):
        return

    from src import audit

    monkeypatch.setattr(audit, "ARQUIVO_REGISTRO", tmp_path / "execucoes_teste.jsonl")
    monkeypatch.setattr(
        "src.rf19_complemento.versao_indice_atual", lambda: "indice-de-teste"
    )
