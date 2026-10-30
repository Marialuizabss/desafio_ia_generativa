
from src.rf19_complemento import _retificacoes_do_item


def documento(doc_id, ordem, alteracoes=None):
    return {
        "doc_id": doc_id,
        "ordem": ordem,
        "altera": alteracoes or [],
    }


def alteracao(item, escopo):
    return {
        "doc_id": "DOC-BASE",
        "itens": [item],
        "escopo": escopo,
    }


def test_localiza_retificacao_integral():
    catalogo = {
        "DOC-BASE": documento("DOC-BASE", 0),
        "RET-01": documento(
            "RET-01", 1,
            [alteracao("7", "Substitui o item 7 por inteiro")],
        ),
    }

    resultado = _retificacoes_do_item(catalogo, "7")

    assert [d["doc_id"] for d in resultado] == ["RET-01"]


def test_localiza_retificacoes_parciais():
    catalogo = {
        "DOC-BASE": documento("DOC-BASE", 0),
        "RET-01": documento(
            "RET-01", 1,
            [alteracao("5", "Altera apenas o prazo de inscrição")],
        ),
        "RET-02": documento(
            "RET-02", 2,
            [alteracao("5", "Altera apenas o início das aulas")],
        ),
    }

    resultado = _retificacoes_do_item(catalogo, "5")

    assert {d["doc_id"] for d in resultado} == {
        "RET-01", "RET-02"
    }


def test_nao_confunde_itens_diferentes():
    catalogo = {
        "RET-01": documento(
            "RET-01", 1,
            [alteracao("3.1", "Altera documentos exigidos")],
        ),
        "RET-02": documento(
            "RET-02", 2,
            [alteracao("3.2", "Altera horário de atendimento")],
        ),
    }

    resultado = _retificacoes_do_item(catalogo, "3.1")

    assert [d["doc_id"] for d in resultado] == ["RET-01"]


def test_retificacao_sem_alteracao_nao_substitui_base():
    catalogo = {
        "DOC-BASE": documento("DOC-BASE", 0),
        "COMUNICADO": documento("COMUNICADO", None),
    }

    assert _retificacoes_do_item(catalogo, "5") == []

