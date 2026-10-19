"""RF04 — falhas da API viram mensagem compreensível, sem a chave."""

import unittest
from unittest.mock import MagicMock, patch

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from src import llm_client

CHAVE = "sk-" + "chavefalsa1234567890abcdefghij"


def _requisicao():
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _resposta(status):
    return httpx.Response(status, request=_requisicao())


def _chamar_com_erro(erro):
    cliente = MagicMock()
    cliente.responses.create.side_effect = erro
    with patch.object(llm_client, "OpenAI", return_value=cliente):
        llm_client.extrair_campos("Pedido de matrícula.", "pedido.txt")


class TestRF04Falhas(unittest.TestCase):
    """Cada falha da API vira uma mensagem ao operador, e a chave não aparece."""

    def _conferir(self, erro, trecho):
        with self.assertRaises(ValueError) as contexto:
            _chamar_com_erro(erro)
        mensagem = str(contexto.exception)
        self.assertIn(trecho, mensagem)
        self.assertNotIn(CHAVE, mensagem)
        self.assertNotIn("sk-", mensagem)

    def test_chave_recusada(self):
        self._conferir(
            AuthenticationError(f"invalid {CHAVE}", response=_resposta(401), body=None),
            "ausente ou foi recusada",
        )

    def test_sem_permissao(self):
        self._conferir(
            PermissionDeniedError(f"denied {CHAVE}", response=_resposta(403), body=None),
            "ausente ou foi recusada",
        )

    def test_limite_de_requisicoes(self):
        self._conferir(
            RateLimitError(f"rate {CHAVE}", response=_resposta(429), body=None),
            "limite de requisições",
        )

    def test_tempo_limite(self):
        erro = APITimeoutError(_requisicao())
        erro.message = f"Request timed out. {CHAVE}"
        self._conferir(erro, "tempo limite")

    def test_sem_conexao(self):
        self._conferir(
            APIConnectionError(message=f"connection {CHAVE}", request=_requisicao()),
            "Não foi possível conectar",
        )

    def test_servico_indisponivel(self):
        self._conferir(
            APIStatusError(f"down {CHAVE}", response=_resposta(500), body=None),
            "indisponível",
        )
