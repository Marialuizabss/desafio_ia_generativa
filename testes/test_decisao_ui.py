import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import audit, fluxo
from src.extracao import CAMPOS, VALOR_AUSENTE


def _texto(tela) -> str:
    return "\n".join(item.value for item in tela.markdown)


class TestDecisaoInterface(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.original = self.base / "dados" / "originais" / "solicitacao_texto.txt"
        self.extracao = self.base / "dados" / "processados" / "extracao_pedido.json"
        self.original.parent.mkdir(parents=True)
        self.extracao.parent.mkdir(parents=True)
        self.original.write_text("Pedido original", encoding="utf-8")
        self.extracao.write_text('{"evidencia": true}\n', encoding="utf-8")
        self.log = self.base / "execucoes.jsonl"
        self.registro = {
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
            "arquivo_origem": "dados/originais/solicitacao_texto.txt",
            "chamada": {},
        }
        self.registro["campos"]["solicitante"] = {
            "valor": "Ana",
            "fonte": "dados/originais/solicitacao_texto.txt",
        }
        self.chamadas = []

        def processar(entrada, forcar=False, configuracao=None, id_execucao_anterior=None):
            self.chamadas.append({"forcar": forcar, "anterior": id_execucao_anterior})
            if not forcar:
                return self.registro
            novo = json.loads(json.dumps(self.registro))
            novo["id_execucao"] = "teste-nova"
            novo["campos"]["solicitante"] = {
                "valor": "Nova Pessoa",
                "fonte": "edicao",
            }
            return novo

        def copia_falsa(nome, dados, pasta=None):
            return {
                "caminho": self.original,
                "relativo": "dados/originais/solicitacao_texto.txt",
                "preservou_existente": True,
            }

        self.patches = [
            patch("src.interface.processar_entrada", side_effect=processar),
            patch("src.interface.guardar_copia", side_effect=copia_falsa),
            patch.object(fluxo, "BASE_DIR", self.base),
            patch.object(audit, "ARQUIVO_REGISTRO", self.log),
            patch("src.audio.gerar_audio"),
        ]
        iniciados = []
        for item in self.patches:
            iniciados.append(item.start())
            self.addCleanup(item.stop)
        self.audio = iniciados[-1]

    def _ate_revisao(self):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n",
            default_timeout=15,
        )
        tela.run()
        tela.button(key="prosseguir").click().run()
        tela.text_area(key="rascunho_texto").set_value("Pedido de matrícula.").run()
        tela.button(key="prosseguir").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Avaliação humana", _texto(tela))
        return tela

    def _eventos(self):
        if not self.log.is_file():
            return []
        return [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines() if linha.strip()]

    def test_rejeicao_sem_justificativa_nao_grava(self):
        tela = self._ate_revisao()
        tela.button(key="rejeitar").click().run()
        tela.text_area(key="justificativa_rejeicao").set_value("   ").run()
        tela.button(key="confirmar_rejeicao").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("Informe a justificativa para rejeitar.", _texto(tela))
        self.assertEqual(self._eventos(), [])
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        self.assertEqual(self.original.read_text(encoding="utf-8"), "Pedido original")
        self.assertNotIn("MINUTA_DO_MODELO_OCULTA", _texto(tela))
        self.audio.assert_not_called()

    def test_rejeicao_na_etapa_3_grava_e_pode_gerar_de_novo(self):
        tela = self._ate_revisao()
        antes = list(self.chamadas)
        tela.button(key="rejeitar").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_rejeicao").set_value("Protocolo inventado.").run()
        tela.button(key="confirmar_rejeicao").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("Gerar de novo chama o modelo outra vez.", _texto(tela))
        self.assertNotIn("MINUTA_DO_MODELO_OCULTA", _texto(tela))
        self.assertEqual(self.chamadas, antes)
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        eventos = self._eventos()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["decisao"], "rejeitado")
        self.assertEqual(eventos[0]["id_execucao"], "teste-edicao")
        self.assertEqual(eventos[0]["justificativa"], "Protocolo inventado.")
        self.assertEqual(eventos[0]["revisor"], "Ana")
        self.audio.assert_not_called()

        tela.button(key="gerar_de_novo").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Avaliação humana", _texto(tela))
        self.assertEqual(tela.text_input(key="edit_solicitante").value, "Nova Pessoa")
        self.assertEqual(self.chamadas[-1]["forcar"], True)
        self.assertEqual(self.chamadas[-1]["anterior"], "teste-edicao")
        eventos = self._eventos()
        self.assertEqual([evento["decisao"] for evento in eventos], ["rejeitado", "nova_geracao"])
        self.assertTrue(all(evento["id_execucao"] == "teste-edicao" for evento in eventos))
        preservado = self.base / eventos[1]["arquivo_preservado"]
        self.assertEqual(preservado.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')

    def test_rejeicao_na_etapa_4_volta_para_corrigir_os_campos(self):
        tela = self._ate_revisao()
        tela.text_input(key="edit_solicitante").set_value("Joana Lima").run()
        tela.button(key="prosseguir").click().run()
        self.assertIn("Joana Lima", _texto(tela))
        gravado = self.extracao.read_text(encoding="utf-8")

        tela.button(key="rejeitar").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_rejeicao").set_value("Nome do solicitante errado.").run()
        tela.button(key="confirmar_rejeicao").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("corrija na etapa anterior", _texto(tela))
        self.assertIn("Joana Lima", _texto(tela))
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), gravado)
        self.assertEqual(self._eventos()[0]["decisao"], "rejeitado")
        self.audio.assert_not_called()

        tela.button(key="corrigir_campos").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Avaliação humana", _texto(tela))
        self.assertEqual(tela.text_input(key="edit_solicitante").value, "Joana Lima")
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), gravado)
        self.assertEqual(len(self._eventos()), 1)

    def test_aprovacao_na_etapa_4_grava_sem_gerar_audio(self):
        tela = self._ate_revisao()
        tela.button(key="prosseguir").click().run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Informe o nome do revisor.", _texto(tela))
        self.assertEqual(self._eventos(), [])

        tela.text_input(key="revisor").set_value("Ana").run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Confira nome, protocolo e datas antes de aprovar.", _texto(tela))
        self.assertEqual(self._eventos(), [])

        tela.checkbox(key="conferencia_critica").set_value(True).run()
        tela.button(key="aprovar").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("aprovado com revisão", _texto(tela))
        eventos = self._eventos()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["decisao"], "aprovado_com_revisao")
        self.assertEqual(eventos[0]["id_execucao"], "teste-edicao")
        self.assertEqual(eventos[0]["revisor"], "Ana")
        self.assertEqual(eventos[0]["justificativa"], "")
        self.assertTrue(eventos[0]["conferencia_dados_criticos"])
        self.audio.assert_not_called()
