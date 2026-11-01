"""Áudio, imagem ou TXT na Ficha. Sem API: a transcrição e a leitura são simuladas."""

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src import audio, audit, entrada_ficha, vision
from src.consulta_acervo import MOTIVO_CONFERIR_LEITURA, exigir_conferencia_da_leitura
from src.entrada_ficha import ArquivoBloqueado, destino_da_transcricao, ler_arquivo_da_ficha


class TestArquivoNaFicha(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.log = self.pasta / "execucoes.jsonl"
        self.guardados = []
        self.lidos = []
        for alvo, nome, valor in (
            (audit, "ARQUIVO_REGISTRO", self.log),
            (entrada_ficha, "_guardar_copia", self._guardar),
        ):
            patcher = patch.object(alvo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _guardar(self, nome, conteudo):
        caminho = self.pasta / nome
        caminho.write_bytes(conteudo)
        self.guardados.append(nome)
        return {"caminho": caminho, "relativo": f"dados/originais/{nome}"}

    def _ler(self, texto):
        def extrair(modalidade, caminho):
            self.lidos.append((modalidade, caminho.name))
            return texto

        return patch.object(entrada_ficha, "_texto_do_arquivo", extrair)

    def _eventos(self):
        if not self.log.is_file():
            return []
        return [
            json.loads(linha)
            for linha in self.log.read_text(encoding="utf-8").splitlines()
            if linha.strip()
        ]

    def test_audio_vira_texto_com_aviso_de_conferencia(self):
        with self._ler("Meu nome é Marcos e quero me matricular."):
            lido = ler_arquivo_da_ficha("entrada_audio.mp3", b"ID3-audio")
        self.assertEqual(lido["modalidade"], "audio")
        self.assertEqual(lido["texto"], "Meu nome é Marcos e quero me matricular.")
        self.assertEqual(lido["arquivo"], "dados/originais/entrada_audio.mp3")
        self.assertIn("confira nome, protocolo e datas com o áudio original", lido["aviso"])
        self.assertEqual(self.lidos, [("audio", "entrada_audio.mp3")])

    def test_imagem_e_pdf_vao_para_a_leitura(self):
        for nome in ("ficha.jpg", "ficha.png", "entrada_pdf-imagem.pdf"):
            with self.subTest(nome=nome), self._ler("FICHA DE MATRÍCULA"):
                lido = ler_arquivo_da_ficha(nome, b"conteudo")
                self.assertEqual(lido["modalidade"], "imagem")
                self.assertIn("ficha original", lido["aviso"])

    def test_txt_le_a_copia_sem_chamar_a_api(self):
        lido = ler_arquivo_da_ficha("pedido.txt", "Quero me matricular.".encode("utf-8"))
        self.assertEqual((lido["modalidade"], lido["texto"]), ("texto", "Quero me matricular."))

    def test_txt_fora_de_utf8_avisa(self):
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            ler_arquivo_da_ficha("pedido.txt", "matrícula".encode("latin-1"))

    def test_tipo_nao_aceito_bloqueia_e_registra_sem_o_nome(self):
        with self.assertRaisesRegex(ArquivoBloqueado, "O tipo do arquivo não é aceito."):
            ler_arquivo_da_ficha("planilha_marcos.xlsx", b"conteudo")
        evento = self._eventos()[-1]
        self.assertEqual(evento["evento"], "bloqueio_guardrail")
        self.assertEqual(evento["origem"], "analise")
        self.assertEqual(evento["motivos"], ["tipo_nao_aceito"])
        self.assertNotIn("planilha", self.log.read_text(encoding="utf-8"))
        self.assertEqual(self.guardados, [])

    def test_vazio_e_acima_do_limite_bloqueiam(self):
        with self.assertRaisesRegex(ArquivoBloqueado, "A entrada está vazia."):
            ler_arquivo_da_ficha("pedido.txt", b"")
        with self.assertRaisesRegex(ArquivoBloqueado, "passa do tamanho permitido"):
            ler_arquivo_da_ficha("pedido.txt", b"a" * (5 * 1024 * 1024 + 1))
        self.assertEqual(self.guardados, [])

    def test_leitura_vazia_nao_vira_ficha(self):
        with self._ler("   "), self.assertRaisesRegex(ValueError, "Não foi possível extrair texto"):
            ler_arquivo_da_ficha("entrada_audio.mp3", b"ID3-audio")

    def test_transcricao_nao_sobrescreve_a_evidencia_do_t15(self):
        destino = destino_da_transcricao(
            Path("dados/originais/entrada_audio.mp3"), datetime(2026, 11, 1, 10, 0, 0)
        )
        processados = entrada_ficha.BASE_DIR / "dados" / "processados"
        self.assertEqual(destino.name, "transcricao_entrada_audio_20261101_100000.txt")
        self.assertEqual(destino.parent, processados / "ficha")
        self.assertNotEqual(destino, processados / "transcricao_entrada_audio.txt")


class TestConferenciaDaLeitura(unittest.TestCase):
    FICHA = {"linhas": {"categoria": "Matrícula"}, "estado": "pendente", "motivos": []}

    def test_audio_e_imagem_vao_para_revisao(self):
        for modalidade in ("audio", "imagem"):
            with self.subTest(modalidade=modalidade):
                ficha = exigir_conferencia_da_leitura(dict(self.FICHA), modalidade)
                self.assertEqual(ficha["estado"], "revisar")
                self.assertEqual(ficha["motivos"], [MOTIVO_CONFERIR_LEITURA])
                # Aplicar de novo não repete o motivo.
                self.assertEqual(
                    exigir_conferencia_da_leitura(ficha, modalidade)["motivos"],
                    [MOTIVO_CONFERIR_LEITURA],
                )

    def test_texto_digitado_e_ficha_bloqueada_nao_mudam(self):
        for modalidade in (None, "texto"):
            with self.subTest(modalidade=modalidade):
                self.assertEqual(exigir_conferencia_da_leitura(dict(self.FICHA), modalidade), self.FICHA)
        bloqueada = {"tipo": "bloqueio", "estado": None, "motivos": []}
        self.assertEqual(exigir_conferencia_da_leitura(bloqueada, "audio"), bloqueada)


class TestUmaRepeticao(unittest.TestCase):
    """RF16: a transcrição e a leitura que alimentam a Ficha repetem no máximo uma vez."""

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.vistos = []

    def _cliente(self, resposta):
        vistos = self.vistos

        class _Cliente:
            def __init__(self, timeout, max_retries):
                vistos.append(max_retries)
                criar = SimpleNamespace(create=lambda **_: resposta)
                self.audio = SimpleNamespace(transcriptions=criar)
                self.chat = SimpleNamespace(completions=criar)

        return _Cliente

    def test_transcricao(self):
        arquivo = self.pasta / "pedido.mp3"
        arquivo.write_bytes(b"ID3")
        with patch.object(audio, "OpenAI", self._cliente(SimpleNamespace(text="Quero me matricular."))):
            texto = audio.transcrever_audio(arquivo, destino_texto=self.pasta / "transcricao.txt")
        self.assertEqual(texto, "Quero me matricular.")
        self.assertEqual(self.vistos, [1])

    def test_leitura_da_ficha(self):
        arquivo = self.pasta / "ficha.png"
        arquivo.write_bytes(b"\x89PNG")
        resposta = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="FICHA"))])
        with patch.object(vision, "OpenAI", self._cliente(resposta)):
            self.assertEqual(vision.ler_texto_visual(arquivo), "FICHA")
        self.assertEqual(self.vistos, [1])


if __name__ == "__main__":
    unittest.main()
