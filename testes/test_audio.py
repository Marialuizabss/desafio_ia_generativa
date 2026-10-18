
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src import audio


class TestRF06Transcricao(unittest.TestCase):

    def test_audio_inexistente(self):
        with TemporaryDirectory() as pasta:
            ausente = Path(pasta) / "entrada_audio.mp3"
            with self.assertRaises(FileNotFoundError):
                audio.transcrever_audio(ausente)

    def test_transcricao_vazia(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "originais"
            entrada.mkdir(parents=True)
            arquivo = entrada / "entrada_audio.mp3"
            arquivo.write_bytes(b"audio-ficticio")

            cliente = MagicMock()
            cliente.audio.transcriptions.create.return_value.text = "   "

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    with self.assertRaises(ValueError):
                        audio.transcrever_audio(arquivo)


    def test_transcricao_sucesso(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "originais"
            entrada.mkdir(parents=True)
            arquivo = entrada / "entrada_audio.mp3"
            arquivo.write_bytes(b"audio-ficticio")

            cliente = MagicMock()
            cliente.audio.transcriptions.create.return_value.text = (
                "Solicito informações sobre matrícula."
            )

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    audio.transcrever_audio(arquivo)

            saida = base / "dados" / "processados"
            logs = base / "resultados" / "logs"
            texto = (saida / "transcricao_rf06.txt").read_text(
                encoding="utf-8"
            )
            metadados = (logs / "metadados_rf06.json").read_text(
                encoding="utf-8"
            )

            self.assertEqual(
                texto, "Solicito informações sobre matrícula."
            )
            self.assertIn('"status": "sucesso"', metadados)
            self.assertIn('"requisito": "RF06"', metadados)


class TestRF07Sintese(unittest.TestCase):

    def test_texto_inexistente(self):
        with TemporaryDirectory() as pasta:
            with patch.object(audio, "BASE_DIR", Path(pasta)):
                with self.assertRaises(FileNotFoundError):
                    audio.gerar_audio()

    def test_texto_vazio(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "resultados" / "minutas"
            entrada.mkdir(parents=True)
            (entrada / "texto_rf07.txt").write_text(
                "   ", encoding="utf-8"
            )

            with patch.object(audio, "BASE_DIR", base):
                with self.assertRaises(ValueError):
                    audio.gerar_audio()


    def test_geracao_audio_sucesso(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "resultados" / "minutas"
            entrada.mkdir(parents=True)

            (entrada / "texto_rf07.txt").write_text(
                "Sua solicitação foi recebida.",
                encoding="utf-8"
            )

            cliente = MagicMock()
            resposta = MagicMock()

            def salvar_audio(caminho):
                Path(caminho).write_bytes(b"mp3-simulado")

            resposta.stream_to_file.side_effect = salvar_audio

            streaming = (
                cliente.audio.speech
                .with_streaming_response.create
                .return_value
            )
            streaming.__enter__.return_value = resposta

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    audio.gerar_audio()

            arquivo_saida = (
                base / "resultados" / "audios" / "audio_rf07.mp3"
            )

            self.assertTrue(arquivo_saida.is_file())
            self.assertEqual(
                arquivo_saida.read_bytes(),
                b"mp3-simulado"
            )

            cliente.audio.speech.with_streaming_response.create.assert_called_once_with(
                model="tts-1-hd",
                voice="nova",
                input="Sua solicitação foi recebida.",
                response_format="mp3",
            )


    def test_avisa_campos_nao_localizados(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "resultados" / "minutas"
            entrada.mkdir(parents=True)

            (entrada / "texto_rf07.txt").write_text(
                "Curso: Técnico em Enfermagem. Prazo: não localizado.",
                encoding="utf-8",
            )

            cliente = MagicMock()
            resposta = MagicMock()

            streaming = (
                cliente.audio.speech
                .with_streaming_response.create
                .return_value
            )
            streaming.__enter__.return_value = resposta

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    audio.gerar_audio()

            argumentos = (
                cliente.audio.speech
                .with_streaming_response.create.call_args.kwargs
            )

            self.assertIn("Atenção", argumentos["input"])
            self.assertIn("não localizados", argumentos["input"])
            self.assertIn("Confira as informações", argumentos["input"])


if __name__ == "__main__":
    unittest.main()


class TestRF06Duracao(unittest.TestCase):
    """A duração vem do cabeçalho do arquivo, sem chamar a API."""

    def test_duracao_de_um_wav(self):
        import wave

        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "voz.wav"
            with wave.open(str(caminho), "wb") as arquivo:
                arquivo.setnchannels(1)
                arquivo.setsampwidth(2)
                arquivo.setframerate(8000)
                arquivo.writeframes(b"\x00\x00" * 16000)
            self.assertEqual(audio.duracao_do_audio(caminho), 2.0)

    def test_formato_desconhecido_devolve_none(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "voz.webm"
            caminho.write_bytes(b"nao e audio")
            self.assertIsNone(audio.duracao_do_audio(caminho))

    def test_audio_do_projeto(self):
        caminho = Path(__file__).resolve().parent.parent / "dados" / "originais" / "entrada_audio.mp3"
        self.assertAlmostEqual(audio.duracao_do_audio(caminho), 89.16, places=1)
