"""Correções do RF19: contexto com acentos e validação de citações."""

import pytest

from src.rag import montar_contexto
from src.rf19_complemento import _validar_citacoes


def evidencia(chunk_id, texto, pagina=None, secao=None, doc_id="ACV-99"):
    return {
        "chunk_id": chunk_id,
        "texto": texto,
        "distancia": 0.1,
        "metadados": {
            "doc_id": doc_id,
            "titulo": "Documento de teste",
            "versao": "1.0",
            "sha256": "0" * 64,
            "pagina": pagina or 0,
            "secao": secao or "",
        },
    }


TEXTO = (
    "O candidato deve apresentar o original dos documentos. "
    "A matrícula será efetivada no prazo previsto no edital."
)


def test_contexto_tem_rotulos_acentuados():
    contexto = montar_contexto([
        evidencia("A-1", TEXTO, pagina=10),
        evidencia("B-1", TEXTO, secao="3. Trancamento", doc_id="ACV-08"),
    ])

    for rotulo in ("Documento:", "Versão:", "Página 10", "Seção 3. Trancamento",
                   "Localização:", "Classificação:", "Chunk ID: A-1"):
        assert rotulo in contexto

    assert "?" not in contexto.replace(TEXTO, "")


def test_contexto_secao_nao_identificada():
    contexto = montar_contexto([evidencia("A-1", TEXTO)])

    assert "Seção não identificada" in contexto


def test_citacao_literal_e_aceita():
    fontes = _validar_citacoes(
        [{"chunk_id": "A-1", "trecho": "O candidato deve apresentar o original dos documentos."}],
        [evidencia("A-1", TEXTO)],
    )

    assert fontes[0]["trecho_citado"].startswith("O candidato deve apresentar")


def test_citacao_quase_literal_e_trocada_pela_passagem_real():
    # Palavras da passagem fora da ordem: não é substring, mas todas as
    # palavras de conteúdo estão numa única frase da fonte.
    fontes = _validar_citacoes(
        [{"chunk_id": "A-1", "trecho": "candidato deve apresentar original documentos"}],
        [evidencia("A-1", TEXTO)],
    )

    # Devolve só a frase real, não o chunk inteiro.
    assert fontes[0]["trecho_citado"] == "O candidato deve apresentar o original dos documentos."


def test_parafrase_nao_vira_citacao():
    with pytest.raises(ValueError, match="não foi comprovado"):
        _validar_citacoes(
            [{"chunk_id": "A-1", "trecho": "candidato deve apresentar documentos originais do edital"}],
            [evidencia("A-1", TEXTO)],
        )


def test_citacao_inventada_e_rejeitada():
    with pytest.raises(ValueError, match="não foi comprovado"):
        _validar_citacoes(
            [{"chunk_id": "A-1", "trecho": "O prazo para recurso é de quinze dias corridos"}],
            [evidencia("A-1", TEXTO)],
        )


def test_citacao_com_chunk_inexistente_ou_curta():
    with pytest.raises(ValueError, match="Fonte inexistente"):
        _validar_citacoes(
            [{"chunk_id": "Z-9", "trecho": "O candidato deve apresentar o original"}],
            [evidencia("A-1", TEXTO)],
        )

    with pytest.raises(ValueError, match="curto"):
        _validar_citacoes(
            [{"chunk_id": "A-1", "trecho": "original"}],
            [evidencia("A-1", TEXTO)],
        )