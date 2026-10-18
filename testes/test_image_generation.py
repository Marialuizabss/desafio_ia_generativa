
import base64
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src import image_generation as imagens


class TestRF10Imagens(unittest.TestCase):

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.saida = self.base / "resultados" / "imagens"
        self.saida.mkdir(parents=True)
        self.logs = self.base / "resultados" / "logs"

        self.patcher = patch.object(imagens, "BASE_DIR", self.base)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_geracao_sucesso(self):
        cliente = MagicMock()
        cliente.images.generate.return_value.data[0].b64_json = (
            base64.b64encode(b"imagem-simulada").decode("ascii")
        )

        with patch.object(imagens, "OpenAI", return_value=cliente):
            imagens.gerar_imagem()

        arquivo = self.saida / "imagem_rf10_original.png"
        metadados = self.logs / "metadados_rf10.json"

        self.assertEqual(arquivo.read_bytes(), b"imagem-simulada")
        self.assertTrue(metadados.is_file())

        registro = json.loads(metadados.read_text(encoding="utf-8"))
        self.assertEqual(registro["requisito"], "RF10")
        self.assertEqual(registro["etapa"], "geracao")
        self.assertEqual(registro["modelo"], "gpt-image-1")
        self.assertIn("prompt", registro)
        self.assertIn("data_execucao_utc", registro)

        cliente.images.generate.assert_called_once()

    def test_geracao_nao_sobrescreve(self):
        arquivo = self.saida / "imagem_rf10_original.png"
        arquivo.write_bytes(b"imagem-original")

        with patch.object(imagens, "OpenAI") as cliente:
            with self.assertRaises(FileExistsError):
                imagens.gerar_imagem()
            cliente.assert_not_called()

        self.assertEqual(arquivo.read_bytes(), b"imagem-original")

    def test_geracao_resposta_vazia(self):
        cliente = MagicMock()
        cliente.images.generate.return_value.data[0].b64_json = None

        with patch.object(imagens, "OpenAI", return_value=cliente):
            with self.assertRaises(ValueError):
                imagens.gerar_imagem()

        self.assertFalse(
            (self.saida / "imagem_rf10_original.png").exists()
        )

    def test_edicao_entrada_inexistente(self):
        with patch.object(imagens, "OpenAI") as cliente:
            with self.assertRaises(FileNotFoundError):
                imagens.editar_imagem()
            cliente.assert_not_called()

    def test_edicao_nao_sobrescreve(self):
        entrada = self.saida / "imagem_rf10_layout_formal.png"
        entrada.write_bytes(b"imagem-entrada")

        arquivo = self.saida / "imagem_rf10_editada.png"
        arquivo.write_bytes(b"imagem-existente")

        with patch.object(imagens, "OpenAI") as cliente:
            with self.assertRaises(FileExistsError):
                imagens.editar_imagem()
            cliente.assert_not_called()

        self.assertEqual(arquivo.read_bytes(), b"imagem-existente")

    def test_edicao_resposta_vazia(self):
        entrada = self.saida / "imagem_rf10_layout_formal.png"
        entrada.write_bytes(b"imagem-entrada")

        cliente = MagicMock()
        cliente.images.edit.return_value.data[0].b64_json = None

        with patch.object(imagens, "OpenAI", return_value=cliente):
            with self.assertRaises(ValueError):
                imagens.editar_imagem()

        self.assertFalse(
            (self.saida / "imagem_rf10_editada.png").exists()
        )

    def test_edicao_sucesso(self):
        entrada = self.saida / "imagem_rf10_layout_formal.png"
        entrada.write_bytes(b"imagem-entrada")

        cliente = MagicMock()
        cliente.images.edit.return_value.data[0].b64_json = (
            base64.b64encode(b"imagem-editada").decode("ascii")
        )

        with patch.object(imagens, "OpenAI", return_value=cliente):
            imagens.editar_imagem()

        arquivo = self.saida / "imagem_rf10_editada.png"
        metadados = self.logs / "metadados_edicao_rf10.json"

        self.assertEqual(arquivo.read_bytes(), b"imagem-editada")

        registro = json.loads(metadados.read_text(encoding="utf-8"))
        self.assertEqual(registro["etapa"], "edicao")
        self.assertEqual(registro["modelo"], "gpt-image-1")
        self.assertIn("prompt", registro)
        self.assertIn("data_execucao_utc", registro)

        cliente.images.edit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
