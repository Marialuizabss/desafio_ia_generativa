
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from src import vision


class TestRF08Visao(unittest.TestCase):

    def test_imagem_inexistente(self):
        with TemporaryDirectory() as pasta:
            with patch.object(vision, "BASE_DIR", Path(pasta)):
                with self.assertRaises(FileNotFoundError):
                    vision.extrair_ficha()

    def test_resposta_vazia(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "processados"
            entrada.mkdir(parents=True)

            (entrada / "entrada_rf08_pagina1.png").write_bytes(
                b"imagem-simulada"
            )

            cliente = MagicMock()
            cliente.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content=""))
            ]

            with patch.object(vision, "BASE_DIR", base):
                with patch.object(vision, "OpenAI", return_value=cliente):
                    with self.assertRaisesRegex(
                        ValueError, "resposta vazia"
                    ):
                        vision.extrair_ficha()

    def test_extracao_sucesso(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "processados"
            entrada.mkdir(parents=True)

            (entrada / "entrada_rf08_pagina1.png").write_bytes(
                b"imagem-simulada"
            )

            dados_simulados = {
                "codigo": "2026-000142",
                "nome": "MARCOS VINICIUS DE ALMEIDA SANTOS",
                "curso": "TÉCNICO EM ENFERMAGEM",
                "data_matricula": "14/10/2026",
            }

            cliente = MagicMock()
            cliente.chat.completions.create.return_value.choices = [
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            dados_simulados, ensure_ascii=False
                        )
                    )
                )
            ]

            with patch.object(vision, "BASE_DIR", base):
                with patch.object(vision, "OpenAI", return_value=cliente):
                    vision.extrair_ficha()

            arquivo_saida = (
                base / "dados" / "processados" / "extracao_rf08.json"
            )

            self.assertTrue(arquivo_saida.is_file())

            dados = json.loads(
                arquivo_saida.read_text(encoding="utf-8")
            )

            self.assertEqual(dados, dados_simulados)

            cliente.chat.completions.create.assert_called_once()

            argumentos = (
                cliente.chat.completions.create.call_args.kwargs
            )

            self.assertEqual(argumentos["model"], "gpt-4o")
            self.assertEqual(
                argumentos["response_format"],
                {"type": "json_object"}
            )


if __name__ == "__main__":
    unittest.main()
