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
                    with self.assertRaisesRegex(ValueError, "resposta vazia"):
                        vision.extrair_ficha()

    def test_extracao_sucesso(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            entrada = base / "dados" / "processados"
            entrada.mkdir(parents=True)
            (entrada / "entrada_rf08_pagina1.png").write_bytes(
                b"imagem-simulada"
            )

            campos = (
                vision.CAMPOS_SOLICITACAO
                + vision.CAMPOS_INSTITUCIONAIS
            )
            dados_simulados = {
                campo: {
                    "valor": (
                        "não localizado"
                        if campo in vision.CAMPOS_INSTITUCIONAIS
                        else "valor de teste"
                    ),
                    "fonte": (
                        "nenhuma"
                        if campo in vision.CAMPOS_INSTITUCIONAIS
                        else "dados/originais/entrada_pdf-imagem.pdf"
                    ),
                }
                for campo in campos
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

            resultado = json.loads(
                arquivo_saida.read_text(encoding="utf-8")
            )

            self.assertEqual(resultado["caso_id"], "CASO-06")
            self.assertEqual(resultado["modalidade"], "imagem")

            extracao = resultado["extracao"]
            for campo, esperado in dados_simulados.items():
                self.assertEqual(extracao[campo], esperado)

            self.assertEqual(
                resultado["campos_ausentes"],
                list(vision.CAMPOS_INSTITUCIONAIS),
            )
            self.assertTrue(resultado["requer_revisao"])
            self.assertEqual(resultado["revisao_humana"], "pendente")

            cliente.chat.completions.create.assert_called_once()
            argumentos = cliente.chat.completions.create.call_args.kwargs
            self.assertEqual(argumentos["model"], "gpt-4o")
            self.assertEqual(
                argumentos["response_format"],
                {"type": "json_object"},
            )


if __name__ == "__main__":
    unittest.main()