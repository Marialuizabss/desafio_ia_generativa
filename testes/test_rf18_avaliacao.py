"""Testes da avaliação de chunking do RF18 (offline, com codificador falso)."""

import json

import pytest

from src.avaliacao_rf18 import (
    CONFIGURACOES,
    VALORES_K,
    carregar_perguntas_respondiveis,
    cobertura_referencias,
    executar,
    posicao_da_primeira_referencia,
    trecho_e_referencia,
)
from testes.test_rf17_indice import CodificadorFalso

REF = {"doc_id": "ACV-01", "pagina": 10, "frase": "apresentar presencialmente no local"}


def test_usa_as_cinco_perguntas_respondiveis_do_gabarito():
    perguntas = carregar_perguntas_respondiveis()

    assert [p["id"] for p in perguntas] == ["P01", "P02", "P03", "P04", "P05"]
    assert all(p["referencias"] for p in perguntas)
    assert "matrícula" in perguntas[0]["pergunta"]


def test_regra_de_acerto_exige_documento_pagina_e_frase():
    texto = "O candidato deverá  APRESENTAR\npresencialmente no local indicado."

    assert trecho_e_referencia("ACV-01", 10, texto, REF)
    assert not trecho_e_referencia("ACV-02", 10, texto, REF)
    assert not trecho_e_referencia("ACV-01", 9, texto, REF)
    assert not trecho_e_referencia("ACV-01", 10, "apresentar a distância", REF)
    # Sem página no gabarito, qualquer página serve.
    assert trecho_e_referencia("ACV-01", 3, texto, {**REF, "pagina": None})


def test_posicao_da_primeira_referencia():
    def resultado(doc, pagina, texto):
        return {"texto": texto, "metadados": {"doc_id": doc, "pagina": pagina}}

    resultados = [
        resultado("ACV-02", 10, "apresentar presencialmente no local"),
        resultado("ACV-01", 10, "outro assunto"),
        resultado("ACV-01", 10, "deve apresentar presencialmente no local"),
    ]

    assert posicao_da_primeira_referencia(resultados, [REF]) == 3
    assert posicao_da_primeira_referencia(resultados[:2], [REF]) is None


def test_todas_as_frases_de_referencia_cabem_em_algum_chunk():
    perguntas = carregar_perguntas_respondiveis()
    cobertura = cobertura_referencias(perguntas)

    assert set(cobertura) == set(CONFIGURACOES)

    for nome, dados in cobertura.items():
        assert dados["referencias_total"] == 7
        assert dados["referencias_cobertas"] == 7, nome


def test_execucao_completa_gera_resultados_por_pergunta(tmp_path):
    resultado, destino = executar(
        CodificadorFalso(),
        pasta_indice=tmp_path / "indice",
        pasta_saida=tmp_path / "saida",
        modelo_nome="codificador-falso",
    )

    assert resultado["perguntas"] == ["P01", "P02", "P03", "P04", "P05"]
    assert set(resultado["configuracoes"]) == set(CONFIGURACOES)

    for nome, dados in resultado["configuracoes"].items():
        assert dados["parametros"]["unidade"] == "caracteres"
        assert dados["total_chunks"] > 0
        assert len(dados["por_pergunta"]) == 5

        for k in VALORES_K:
            taxa = dados["acerto_de_recuperacao"][str(k)]
            assert taxa["perguntas"] == 5
            assert 0 <= taxa["acertos"] <= 5
            assert taxa["taxa"] == pytest.approx(taxa["acertos"] / 5, abs=1e-4)

        # Quanto maior o k, nunca menos acertos.
        acertos = [dados["acerto_de_recuperacao"][str(k)]["acertos"] for k in VALORES_K]
        assert acertos == sorted(acertos)

    # Menos chunks quanto maior o tamanho.
    chunks = [resultado["configuracoes"][n]["total_chunks"] for n in ("pequena", "media", "grande")]
    assert chunks == sorted(chunks, reverse=True)

    salvo = json.loads((destino / "resultados_rf18.json").read_text(encoding="utf-8"))
    assert salvo["modelo_embeddings"] == "codificador-falso"
    relatorio = (destino / "relatorio_rf18.md").read_text(encoding="utf-8")
    assert "caracteres" in relatorio and "Acerto@5" in relatorio