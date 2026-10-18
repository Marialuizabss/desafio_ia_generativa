import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import fluxo, llm_client
from src.experimento_rf03 import procurar_texto_fixo_alterado
from src.extracao import CAMPOS, VALOR_AUSENTE


def valores_completos():
    return {nome: f"valor-{nome}" for nome in CAMPOS}


class TestMontarMinuta(unittest.TestCase):
    def test_preenche_os_campos_e_preserva_o_texto_fixo(self):
        minuta = llm_client.montar_minuta(valores_completos())

        self.assertIn("valor-solicitante", minuta)
        self.assertIn("valor-protocolo", minuta)
        self.assertIn("valor-regras_ciencia", minuta)
        self.assertNotIn("[NOME DO SOLICITANTE]", minuta)
        self.assertNotIn("[REGRAS DE CANCELAMENTO", minuta)
        self.assertIn("[NOME DO SERVIDOR RESPONSÁVEL]", minuta)
        self.assertIn("[CARGO / SETOR]", minuta)
        self.assertIn("brasao.png", minuta)
        self.assertEqual(procurar_texto_fixo_alterado(minuta), [])

    def test_campo_vazio_vira_nao_localizado(self):
        minuta = llm_client.montar_minuta({"solicitante": "  "})

        self.assertIn(f"Prezado(a) {VALOR_AUSENTE},", minuta)

    def test_valor_editado_nao_e_interpretado_como_marcador(self):
        minuta = llm_client.montar_minuta({
            "regras_ciencia": "Texto com [PROTOCOLO] literal",
            "protocolo": "2026-000142",
        })

        self.assertIn("Texto com [PROTOCOLO] literal", minuta)
        self.assertIn("protocolo 2026-000142", minuta)


class TestAplicarEdicao(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.relativo = "dados/processados/extracao_pedido.json"
        self.arquivo = self.base / self.relativo
        self.arquivo.parent.mkdir(parents=True)
        self.arquivo.write_text("{}", encoding="utf-8")
        self.registro = {
            "categoria": "matricula",
            "assunto": "Assunto antigo",
            "pedido": "Pedido antigo",
            "campos": {
                nome: {"valor": VALOR_AUSENTE, "fonte": "nenhuma"}
                for nome in CAMPOS
            },
            "campos_ausentes": list(CAMPOS),
            "minuta": "Minuta do modelo",
            "arquivo_extracao": self.relativo,
            "arquivo_origem": "dados/originais/pedido.txt",
            "requer_revisao": True,
        }
        self.registro["campos"]["solicitante"] = {
            "valor": "Ana",
            "fonte": "dados/originais/pedido.txt",
        }

    def test_grava_campos_editados_e_a_minuta(self):
        edicao = {nome: "" for nome in CAMPOS}
        edicao.update({
            "categoria": "documentacao",
            "assunto": "Novo assunto",
            "pedido": "  ",
            "solicitante": "Ana",
            "protocolo": "2026-1",
        })

        with patch.object(fluxo, "BASE_DIR", self.base):
            atualizado = fluxo.aplicar_edicao(self.registro, edicao)

        self.assertEqual(atualizado["categoria"], "documentacao")
        self.assertEqual(atualizado["assunto"], "Novo assunto")
        self.assertEqual(atualizado["pedido"], VALOR_AUSENTE)
        self.assertEqual(atualizado["campos"]["solicitante"]["fonte"], "dados/originais/pedido.txt")
        self.assertEqual(atualizado["campos"]["protocolo"], {"valor": "2026-1", "fonte": "edicao"})
        self.assertIn("curso", atualizado["campos_ausentes"])
        self.assertNotIn("protocolo", atualizado["campos_ausentes"])
        self.assertNotIn("solicitante", atualizado["campos_ausentes"])
        self.assertIn("Ana", atualizado["minuta"])
        self.assertIn("2026-1", atualizado["minuta"])
        self.assertNotIn("Minuta do modelo", atualizado["minuta"])
        self.assertTrue(atualizado["minuta_gerada_de_campos"])
        self.assertTrue(atualizado["requer_revisao"])
        self.assertEqual(self.registro["minuta"], "Minuta do modelo")

        gravado = json.loads(self.arquivo.read_text(encoding="utf-8"))
        self.assertEqual(gravado["minuta"], atualizado["minuta"])
        self.assertEqual(gravado["campos"]["protocolo"]["valor"], "2026-1")

    def test_categoria_desconhecida_mantem_a_anterior(self):
        with patch.object(fluxo, "BASE_DIR", self.base):
            atualizado = fluxo.aplicar_edicao(self.registro, {"categoria": "inventada"})

        self.assertEqual(atualizado["categoria"], "matricula")


class TestInterfaceEdicao(unittest.TestCase):
    def test_minuta_so_aparece_depois_do_botao(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            arquivo = base / "solicitacao_texto.txt"
            arquivo.write_text("Pedido", encoding="utf-8")
            (base / "dados" / "processados").mkdir(parents=True)
            registro = {
                "id_execucao": "teste-edicao",
                "categoria": "matricula",
                "assunto": "Matrícula",
                "pedido": "Efetivar",
                "campos": {
                    nome: {"valor": VALOR_AUSENTE, "fonte": "nenhuma"}
                    for nome in CAMPOS
                },
                "campos_ausentes": list(CAMPOS),
                "alertas_seguranca": [],
                "requer_revisao": True,
                "minuta": "MINUTA_DO_MODELO_OCULTA",
                "arquivo_extracao": "dados/processados/extracao_pedido.json",
                "chamada": {},
            }
            registro["campos"]["solicitante"] = {
                "valor": "Ana",
                "fonte": "dados/originais/pedido.txt",
            }

            def copia_falsa(nome, dados, pasta=None):
                return {
                    "caminho": arquivo,
                    "relativo": "dados/originais/solicitacao_texto.txt",
                    "preservou_existente": False,
                }

            with (
                patch("src.interface.processar_entrada", return_value=registro),
                patch("src.interface.guardar_copia", side_effect=copia_falsa),
                patch.object(fluxo, "BASE_DIR", base),
            ):
                tela = AppTest.from_string(
                    "from src.interface import renderizar\nrenderizar()\n",
                    default_timeout=15,
                )
                tela.run()
                self.assertFalse(tela.exception)
                tela.text_area(key="rascunho_texto").set_value("Pedido de matrícula.").run()
                tela.button(key="confirmar").click().run()
                self.assertFalse(tela.exception)

                texto = "\n".join(item.value for item in tela.markdown)
                self.assertNotIn("MINUTA_DO_MODELO_OCULTA", texto)
                self.assertEqual(tela.button(key="gerar_minuta").label, "Gerar minuta")
                self.assertEqual(tela.text_input(key="edit_solicitante").value, "Ana")

                tela.text_input(key="edit_solicitante").set_value("Joana Lima").run()
                tela.button(key="gerar_minuta").click().run()
                self.assertFalse(tela.exception)

                texto = "\n".join(item.value for item in tela.markdown)
                self.assertIn("Joana Lima", texto)
                self.assertNotIn("MINUTA_DO_MODELO_OCULTA", texto)
                self.assertEqual(tela.button(key="gerar_minuta").label, "Regerar minuta")
                self.assertIn("[NOME DO SERVIDOR RESPONSÁVEL]", texto)
