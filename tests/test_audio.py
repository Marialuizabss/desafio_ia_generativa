
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src import audio


class TestRF06Transcricao(unittest.TestCase):

    def test_audio_inexistente(self):
        with TemporaryDirectory() as pasta:
            with patch.object(audio, "BASE_DIR", Path(pasta)):
                with self.assertRaises(FileNotFoundError):
                    audio.transcrever_audio()

    def test_transcricao_vazia(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "originais"
            entrada.mkdir(parents=True)
            (entrada / "entrada_audio.mp3").write_bytes(b"audio-ficticio")

            cliente = MagicMock()
            cliente.audio.transcriptions.create.return_value.text = "   "

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    with self.assertRaises(ValueError):
                        audio.transcrever_audio()

     
    def test_transcricao_sucesso(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "originais"
            entrada.mkdir(parents=True)
            (entrada / "entrada_audio.mp3").write_bytes(b"audio-ficticio")

            cliente = MagicMock()
            cliente.audio.transcriptions.create.return_value.text = (
                "Solicito informações sobre matrícula."
            )

            with patch.object(audio, "BASE_DIR", base):
                with patch.object(audio, "OpenAI", return_value=cliente):
                    audio.transcrever_audio()

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


if __name__ == "__main__":
    unittest.main()
