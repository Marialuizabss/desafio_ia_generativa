"""Testes do adaptador de provedor (RF21)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.provider_adapter import (
    carregar_configuracao_llm,
    consultar_llm,
)


def test_configuracoes():
    principal = carregar_configuracao_llm("principal")
    alternativa = carregar_configuracao_llm("alternativa")

    assert principal.provedor == "openai"
    assert principal.modelo == "gpt-4o-mini"
    assert alternativa.temperatura == 0.5


def test_consulta_simulada():
    resposta = SimpleNamespace(
        output_text="Resposta de teste",
        usage=SimpleNamespace(
            input_tokens=20,
            output_tokens=10,
            total_tokens=30,
        ),
    )

    with patch("src.provider_adapter.OpenAI") as cliente_mock:
        cliente_mock.return_value.responses.create.return_value = resposta

        texto, auditoria = consultar_llm(
            instrucoes="Responda de forma objetiva.",
            entrada="Qual é o prazo?",
        )

    assert texto == "Resposta de teste"
    assert auditoria["provedor"] == "openai"
    assert auditoria["modelo"] == "gpt-4o-mini"
    assert auditoria["tokens_total"] == 30
    assert auditoria["custo_estimado_usd"] == 0.000009
    assert auditoria["status"] == "sucesso"


def test_entrada_vazia():
    with pytest.raises(ValueError, match="não podem estar vazias"):
        consultar_llm("", "Pergunta de teste")


def test_configuracao_inexistente():
    with pytest.raises(ValueError, match="Configuração LLM desconhecida"):
        carregar_configuracao_llm("inexistente")


def test_falha_na_api():
    with patch("src.provider_adapter.OpenAI") as cliente_mock:
        cliente_mock.return_value.responses.create.side_effect = RuntimeError(
            "Falha simulada na API"
        )

        with pytest.raises(RuntimeError, match="Falha simulada na API"):
            consultar_llm(
                instrucoes="Responda objetivamente.",
                entrada="Qual é o prazo?",
            )


def test_erro_conexao_openai():
    from openai import APIConnectionError
    import httpx

    requisicao = httpx.Request(
        "POST",
        "https://api.openai.com/v1/responses",
    )

    erro = APIConnectionError(request=requisicao)

    with patch("src.provider_adapter.OpenAI") as cliente_mock:
        cliente_mock.return_value.responses.create.side_effect = erro

        with pytest.raises(ValueError, match="Não foi possível conectar"):
            consultar_llm(
                instrucoes="Responda objetivamente.",
                entrada="Qual é o prazo?",
            )
