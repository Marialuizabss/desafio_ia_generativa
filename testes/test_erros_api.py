"""Mensagens de falha da API em português (RF04) nos caminhos de áudio, voz e visão."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAIError,
    RateLimitError,
)

from src import audio, vision
from src.erros_api import mensagem_de_falha

_REQUISICAO = MagicMock()


def _erro_http(classe, status):
    resposta = MagicMock(status_code=status, headers={}, request=_REQUISICAO)
    return classe("erro simulado sk-FALSA1234567890", response=resposta, body=None)


class TestMensagemDeFalha(unittest.TestCase):
    def test_cada_tipo_tem_mensagem_propria(self):
        casos = {
            "chave": (_erro_http(AuthenticationError, 401), ".env"),
            "limite": (_erro_http(RateLimitError, 429), "limite de uso"),
            "tempo": (APITimeoutError(_REQUISICAO), "demorou demais"),
            "conexao": (APIConnectionError(request=_REQUISICAO), "conexão"),
            "modelo": (_erro_http(NotFoundError, 404), "modelo configurado"),
            "pedido": (_erro_http(BadRequestError, 400), "recusou"),
            "servidor": (_erro_http(InternalServerError, 500), "500"),
        }
        for nome, (erro, trecho) in casos.items():
            with self.subTest(nome):
                self.assertIn(trecho, mensagem_de_falha(erro, "a leitura"))

    def test_chave_ausente(self):
        erro = OpenAIError("The api_key client option must be set")
        self.assertIn(".env", mensagem_de_falha(erro, "a leitura"))

    def test_mensagem_nunca_expoe_chave(self):
        erros = [
            _erro_http(AuthenticationError, 401),
            _erro_http(BadRequestError, 400),
            OpenAIError("api_key sk-FALSA1234567890"),
            RuntimeError("sk-FALSA1234567890"),
        ]
        for erro in erros:
            texto = mensagem_de_falha(erro, "a leitura").casefold()
            self.assertNotIn("sk-", texto)
            self.assertNotIn("api_key", texto)

    def test_erro_desconhecido(self):
        self.assertTrue(mensagem_de_falha(RuntimeError("x"), "a leitura").startswith("Não foi possível"))


class TestFalhasNosModulos(unittest.TestCase):
    def test_transcricao_traduz_falha(self):
        cliente = MagicMock()
        cliente.audio.transcriptions.create.side_effect = _erro_http(AuthenticationError, 401)
        with TemporaryDirectory() as pasta, patch.object(audio, "OpenAI", return_value=cliente):
            wav = Path(pasta) / "a.wav"
            wav.write_bytes(b"RIFF")
            with self.assertRaises(ValueError) as contexto:
                audio.transcrever_audio(wav, destino_texto=Path(pasta) / "t.txt")
        self.assertIn("transcrição do áudio", str(contexto.exception))
        self.assertNotIn("sk-", str(contexto.exception))

    def test_transcricao_sem_chave(self):
        with TemporaryDirectory() as pasta, patch.object(
            audio, "OpenAI", side_effect=OpenAIError("api_key must be set")
        ):
            wav = Path(pasta) / "a.wav"
            wav.write_bytes(b"RIFF")
            with self.assertRaises(ValueError) as contexto:
                audio.transcrever_audio(wav, destino_texto=Path(pasta) / "t.txt")
        self.assertIn(".env", str(contexto.exception))

    def test_voz_traduz_falha(self):
        cliente = MagicMock()
        cliente.audio.speech.with_streaming_response.create.side_effect = APIConnectionError(
            request=_REQUISICAO
        )
        with TemporaryDirectory() as pasta, patch.object(audio, "OpenAI", return_value=cliente):
            with self.assertRaises(ValueError) as contexto:
                audio.sintetizar_minuta("Prezado Marcos, texto aprovado.", Path(pasta) / "a.mp3")
        self.assertIn("geração da voz", str(contexto.exception))

    def test_voz_sem_chave(self):
        with TemporaryDirectory() as pasta, patch.object(
            audio, "OpenAI", side_effect=OpenAIError("api_key must be set")
        ):
            with self.assertRaises(ValueError) as contexto:
                audio.sintetizar_minuta("Prezado Marcos, texto aprovado.", Path(pasta) / "a.mp3")
        self.assertIn(".env", str(contexto.exception))

    def test_visao_traduz_falha(self):
        cliente = MagicMock()
        cliente.chat.completions.create.side_effect = _erro_http(RateLimitError, 429)
        with TemporaryDirectory() as pasta, patch.object(vision, "OpenAI", return_value=cliente):
            imagem = Path(pasta) / "ficha.png"
            imagem.write_bytes(b"\x89PNG")
            with self.assertRaises(ValueError) as contexto:
                vision.ler_texto_visual(imagem)
        self.assertIn("leitura do documento", str(contexto.exception))
        self.assertIn("limite de uso", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()