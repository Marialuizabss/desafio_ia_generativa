
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


MINUTA_APROVADA = (
    "[CABEÇALHO COM BRASÃO — dados/originais/brasao.png]\n\n"
    "Prezado(a) Marcos Vinícius de Almeida Santos,\n\n"
    "Recebemos sua solicitação de matrícula, registrada sob o protocolo 2026-000142.\n\n"
    "**Dados informados na solicitação**\n"
    "- Curso: Técnico em Enfermagem\n"
    "- Início do curso: 01/02/2027\n\n"
    "**Orientações**\n"
    "- Prazo para apresentação: não localizado\n\n"
    "Atenciosamente,\nAna Beatriz\nSecretaria Escolar\n\n"
    "*Minuta elaborada com apoio de IA.*"
)


def _palavras(texto):
    import re

    return {palavra.casefold() for palavra in re.findall(r"[A-Za-zÀ-ÿ]+", texto)}


def _cliente_de_voz(erro_no_primeiro=None):
    cliente = MagicMock()
    chamadas = []

    def criar(**argumentos):
        chamadas.append(argumentos)
        if erro_no_primeiro is not None and len(chamadas) == 1:
            raise erro_no_primeiro
        contexto = MagicMock()
        resposta = MagicMock()
        resposta.stream_to_file.side_effect = lambda caminho: Path(caminho).write_bytes(b"mp3-simulado")
        contexto.__enter__.return_value = resposta
        return contexto

    cliente.audio.speech.with_streaming_response.create.side_effect = criar
    return cliente, chamadas


class TestRF07MinutaAprovada(unittest.TestCase):
    """O áudio sai do texto aprovado, só com ajustes de forma para a voz."""

    def test_texto_para_fala_sem_formatacao(self):
        falado = audio.preparar_texto_para_fala(MINUTA_APROVADA)

        self.assertNotIn("CABEÇALHO", falado)
        self.assertNotIn("**", falado)
        self.assertNotIn("- Curso", falado)
        self.assertIn("protocolo 2026, traço, 0 0 0 1 4 2.", falado)
        self.assertIn("Início do curso: 1º de fevereiro de 2027.", falado)
        self.assertIn("Prezado ou prezada Marcos", falado)
        self.assertTrue(falado.startswith(audio.AVISO_NAO_LOCALIZADO))

    def test_nenhuma_palavra_do_texto_aprovado_se_perde(self):
        aprovado = MINUTA_APROVADA.replace("[CABEÇALHO COM BRASÃO — dados/originais/brasao.png]", "")
        aprovado = aprovado.replace("(a)", "")
        faltando = _palavras(aprovado) - _palavras(audio.preparar_texto_para_fala(MINUTA_APROVADA))
        self.assertEqual(faltando, set())

    def test_sem_campo_ausente_nao_ha_aviso(self):
        falado = audio.preparar_texto_para_fala("Prezado(a) Ana,\n\nTexto completo.")
        self.assertNotIn("Atenção", falado)

    def test_sintese_usa_instrucoes_e_guarda_o_texto_falado(self):
        cliente, chamadas = _cliente_de_voz()
        with TemporaryDirectory() as pasta, patch.object(audio, "OpenAI", return_value=cliente):
            destino = Path(pasta) / "audio_minuta_caso_12345678.mp3"
            dados = audio.sintetizar_minuta(MINUTA_APROVADA, destino)

            self.assertEqual(destino.read_bytes(), b"mp3-simulado")
            falado = (Path(pasta) / "audio_minuta_caso_12345678_texto_falado.txt").read_text(encoding="utf-8")
        self.assertEqual(chamadas[0]["model"], "gpt-4o-mini-tts")
        self.assertEqual(chamadas[0]["voice"], "nova")
        self.assertEqual(chamadas[0]["instructions"], audio.INSTRUCOES_VOZ)
        self.assertEqual(chamadas[0]["input"] + "\n", falado)
        self.assertTrue(dados["instrucoes_aplicadas"])

    def test_sem_acesso_ao_modelo_usa_o_alternativo_e_registra(self):
        from openai import NotFoundError

        resposta = MagicMock(status_code=404, headers={})
        erro = NotFoundError("modelo indisponível", response=resposta, body=None)
        cliente, chamadas = _cliente_de_voz(erro_no_primeiro=erro)
        with TemporaryDirectory() as pasta, patch.object(audio, "OpenAI", return_value=cliente):
            dados = audio.sintetizar_minuta(MINUTA_APROVADA, Path(pasta) / "a.mp3")

        self.assertEqual(chamadas[1]["model"], "tts-1-hd")
        self.assertNotIn("instructions", chamadas[1])
        self.assertFalse(dados["instrucoes_aplicadas"])
        self.assertIsNone(dados["instrucoes"])

    def test_minuta_vazia(self):
        with self.assertRaises(ValueError):
            audio.sintetizar_minuta("   ", Path("nao_usado.mp3"))


if __name__ == "__main__":
    unittest.main()
