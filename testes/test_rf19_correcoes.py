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
    # Identificador inventado e trecho que não existe em nenhum chunk recuperado.
    with pytest.raises(ValueError, match="Fonte inexistente"):
        _validar_citacoes(
            [{"chunk_id": "Z-9", "trecho": "O prazo para recurso é de quinze dias corridos"}],
            [evidencia("A-1", TEXTO)],
        )

    with pytest.raises(ValueError, match="curto"):
        _validar_citacoes(
            [{"chunk_id": "A-1", "trecho": "original"}],
            [evidencia("A-1", TEXTO)],
        )


TEXTO_PDF = (
    "10.4. Para efetivação da matrícula, OBRIGATORIAMENTE, o candidato deverá apresentar \n"
    "presencialmente no local onde se inscreveu conforme endereços disponíveis no Anexo I, toda \n"
    "a documentação listada no item 10.5. \n"
    "10.5.  Para a efetivação da MATRÍCULA, serão necessárias a entrega de 01 cópia simples + a \n"
    "apresentação do documento original conforme relação a seguir: \n"
)


def test_citacao_aproximada_em_texto_de_pdf_com_quebras_de_linha():
    # O PDF quebra a linha no meio da frase; a citação omite palavras do meio.
    fontes = _validar_citacoes(
        [{"chunk_id": "A-1",
          "trecho": "o candidato deverá apresentar presencialmente toda a documentação listada no item 10.5"}],
        [evidencia("A-1", TEXTO_PDF)],
    )

    trecho = fontes[0]["trecho_citado"]
    assert "\n" not in trecho
    assert "presencialmente no local onde se inscreveu" in trecho
    # Devolve só a frase do item 10.4, não o chunk inteiro.
    assert "10.5.  Para a efetivação" not in trecho


def test_citacao_com_chunk_id_errado_e_atribuida_ao_chunk_certo():
    outro = "Texto de outro assunto, sem relação com a pergunta feita."
    fontes = _validar_citacoes(
        [{"chunk_id": "A-1", "trecho": "O candidato deve apresentar o original dos documentos."}],
        [evidencia("A-1", outro), evidencia("B-1", TEXTO, pagina=7)],
    )

    assert fontes[0]["chunk_id"] == "B-1"
    assert fontes[0]["pagina"] == 7
    assert fontes[0]["chunk_id_corrigido_de"] == "A-1"


def test_citacao_no_chunk_certo_nao_e_corrigida():
    fontes = _validar_citacoes(
        [{"chunk_id": "A-1", "trecho": "O candidato deve apresentar o original dos documentos."}],
        [evidencia("A-1", TEXTO)],
    )

    assert fontes[0]["chunk_id_corrigido_de"] is None


def test_citacao_com_reticencias_exige_cada_fragmento_literal():
    tabela = (
        "Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas "
        "dos seguintes cursos: \nCuiabá Agropecuária Mimoso \nCuiabá Informática Centro"
    )

    fontes = _validar_citacoes(
        [{"chunk_id": "A-1",
          "trecho": "Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas "
                    "dos seguintes cursos: ... Agropecuária ... Mimoso"}],
        [evidencia("A-1", tabela)],
    )

    assert "..." in fontes[0]["trecho_citado"]


def test_citacao_com_reticencias_e_fragmento_inventado_e_rejeitada():
    tabela = (
        "Fica alterada para o dia 05 de outubro de 2026 a data de início das aulas "
        "dos seguintes cursos: Cuiabá Agropecuária Mimoso"
    )

    with pytest.raises(ValueError, match="não foi comprovado"):
        _validar_citacoes(
            [{"chunk_id": "A-1",
              "trecho": "Fica alterada para o dia 05 de outubro de 2026 a data de início "
                        "das aulas ... com prazo de recurso de dez dias"}],
            [evidencia("A-1", tabela)],
        )


def test_citacao_que_junta_dois_chunks_e_rejeitada():
    primeiro = "A matrícula exige: a) Comprovante de Escolaridade; b) Documento Oficial de Identificação;"
    segundo = "c) CPF; d) Certidão de Nascimento; e) 01 foto 3x4 atual."

    with pytest.raises(ValueError, match="não foi comprovado"):
        _validar_citacoes(
            [{"chunk_id": "A-1",
              "trecho": "A matrícula exige: a) Comprovante de Escolaridade; b) Documento Oficial de "
                        "Identificação; c) CPF; d) Certidão de Nascimento; e) 01 foto 3x4 atual."}],
            [evidencia("A-1", primeiro), evidencia("B-1", segundo)],
        )


def test_chunk_id_inventado_com_trecho_verdadeiro_e_atribuido_ao_chunk_certo():
    fontes = _validar_citacoes(
        [{"chunk_id": "Z-9", "trecho": "O candidato deve apresentar o original dos documentos."}],
        [evidencia("A-1", TEXTO)],
    )

    assert fontes[0]["chunk_id"] == "A-1"
    assert fontes[0]["chunk_id_corrigido_de"] == "Z-9"