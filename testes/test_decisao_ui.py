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
        """Só as decisões; a revisão dos campos também entra no registro."""
        if not self.log.is_file():
            return []
        linhas = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines() if linha.strip()]
        return [linha for linha in linhas if linha.get("evento") == "decisao"]

    def _revisoes(self):
        if not self.log.is_file():
            return []
        linhas = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines() if linha.strip()]
        return [linha for linha in linhas if linha.get("evento") == "revisao_campos"]

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
        self.assertIn("Informe o cargo ou setor de quem assina.", _texto(tela))
        self.assertEqual(self._eventos(), [])

        tela.text_input(key="cargo_setor").set_value("Secretaria Escolar").run()
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

        aprovada = self.base / eventos[0]["arquivo_minuta"]
        self.assertEqual(aprovada.parent, self.base / "resultados" / "minutas" / "aprovadas")
        self.assertIn("Prezado(a) Ana", aprovada.read_text(encoding="utf-8"))
        self.assertIn(eventos[0]["arquivo_minuta"], "\n".join(item.value for item in tela.caption))
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')

    def test_aprovacao_recusada_nao_deixa_minuta_gravada(self):
        tela = self._ate_revisao()
        tela.button(key="prosseguir").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_input(key="cargo_setor").set_value("Secretaria Escolar").run()
        tela.checkbox(key="conferencia_critica").set_value(True).run()
        with patch("src.interface.registrar_decisao", side_effect=ValueError("Falhou.")):
            tela.button(key="aprovar").click().run()

        self.assertIn("Falhou.", _texto(tela))
        self.assertEqual(self._eventos(), [])
        aprovadas = self.base / "resultados" / "minutas" / "aprovadas"
        self.assertEqual(list(aprovadas.glob("*.md")) if aprovadas.exists() else [], [])

    def test_revisao_dos_campos_vai_para_o_registro_sem_os_valores(self):
        tela = self._ate_revisao()
        tela.text_input(key="edit_solicitante").set_value("Joana Lima").run()
        tela.button(key="prosseguir").click().run()
        tela.button(key="voltar").click().run()
        tela.button(key="prosseguir").click().run()

        revisoes = self._revisoes()
        self.assertEqual(len(revisoes), 1)
        self.assertEqual(revisoes[0]["campos_alterados"], ["solicitante"])
        self.assertNotIn("Joana Lima", self.log.read_text(encoding="utf-8"))
        arquivo = self.base / revisoes[0]["arquivo_revisao"]
        self.assertIn("Joana Lima", arquivo.read_text(encoding="utf-8"))
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')

    # ---- Bloco 2: assinatura, conferência por dado, alerta, avisos e origem

    def _ate_minuta(self):
        tela = self._ate_revisao()
        tela.button(key="prosseguir").click().run()
        self.assertFalse(tela.exception)
        return tela

    def _avisos(self, tela):
        return [item.value for item in tela.markdown if "aviso-toast" in item.value and "<style>" not in item.value]

    def _aprovar_texto(self, tela, servidor="Ana Beatriz", cargo="Secretaria Escolar"):
        tela.text_input(key="revisor").set_value(servidor).run()
        tela.text_input(key="cargo_setor").set_value(cargo).run()
        tela.checkbox(key="conferencia_critica").set_value(True).run()
        tela.button(key="aprovar").click().run()
        return tela

    def test_assinatura_aparece_na_minuta_e_vai_para_o_arquivo(self):
        tela = self._ate_minuta()
        self.assertIn("[NOME DO SERVIDOR RESPONSÁVEL]", _texto(tela))
        tela.text_input(key="revisor").set_value("Ana Beatriz").run()
        tela.text_input(key="cargo_setor").set_value("Secretaria Escolar").run()
        texto = _texto(tela)
        self.assertIn("Ana Beatriz", texto)
        self.assertNotIn("[NOME DO SERVIDOR RESPONSÁVEL]", texto)
        self.assertNotIn("[CARGO / SETOR]", texto)

        tela.checkbox(key="conferencia_critica").set_value(True).run()
        tela.button(key="aprovar").click().run()

        decisao = self._eventos()[0]
        self.assertEqual(decisao["revisor"], "Ana Beatriz")
        self.assertEqual(decisao["cargo_setor"], "Secretaria Escolar")
        aprovada = (self.base / decisao["arquivo_minuta"]).read_text(encoding="utf-8")
        self.assertIn("Ana Beatriz", aprovada)
        self.assertIn("Secretaria Escolar", aprovada)
        self.assertNotIn("[NOME DO SERVIDOR RESPONSÁVEL]", aprovada)
        self.assertIn("Ana Beatriz", _texto(tela))

    def test_outra_entrada_limpa_servidor_e_cargo(self):
        tela = self._aprovar_texto(self._ate_minuta())
        tela.button(key="encerrar_caso").click().run()
        tela.text_area(key="rascunho_texto").set_value("Outro pedido.").run()
        tela.button(key="prosseguir").click().run()
        tela.button(key="prosseguir").click().run()

        self.assertEqual(tela.text_input(key="revisor").value, "")
        self.assertEqual(tela.text_input(key="cargo_setor").value, "")

    def test_corrigir_campos_mantem_o_servidor(self):
        tela = self._ate_minuta()
        tela.button(key="rejeitar").click().run()
        tela.text_input(key="revisor").set_value("Ana Beatriz").run()
        tela.text_area(key="justificativa_rejeicao").set_value("Turno errado.").run()
        tela.button(key="confirmar_rejeicao").click().run()
        tela.button(key="corrigir_campos").click().run()
        tela.button(key="prosseguir").click().run()

        self.assertEqual(tela.text_input(key="revisor").value, "Ana Beatriz")

    def test_audio_exige_os_quatro_dados_conferidos(self):
        self.registro["modalidade"] = "audio"
        tela = self._ate_minuta()
        caixas = [caixa for caixa in tela.checkbox if caixa.key.startswith("conferido_")]
        self.assertEqual(len(caixas), 4)
        self.assertNotIn("conferencia_critica", [caixa.key for caixa in tela.checkbox])
        self.assertIn("Nome do solicitante: Ana", [caixa.label for caixa in caixas])
        self.assertIn("Ouvir o áudio original", [item.label for item in tela.expander])

        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_input(key="cargo_setor").set_value("Secretaria").run()
        caixas[0].check().run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Confira com o original: Protocolo, Data da solicitação, Data de início.", _texto(tela))
        self.assertEqual(self._eventos(), [])

        for caixa in [caixa for caixa in tela.checkbox if caixa.key.startswith("conferido_")]:
            caixa.check()
        tela.run()
        tela.button(key="aprovar").click().run()
        decisao = self._eventos()[0]
        self.assertEqual(decisao["dados_conferidos"], ["solicitante", "protocolo", "data_solicitacao", "data_inicio"])

    def test_alerta_mostra_cartao_e_exige_justificativa(self):
        self.registro["alertas_seguranca"] = ["Tentativa de ignorar instruções."]
        tela = self._ate_revisao()
        self.assertTrue(any("alerta-seguranca" in item.value for item in tela.markdown))
        tela.button(key="prosseguir").click().run()

        tela = self._aprovar_texto(tela)
        self.assertIn("Há alerta de segurança: justifique a aprovação.", _texto(tela))
        self.assertEqual(self._eventos(), [])

        tela.text_area(key="justificativa_aprovacao").set_value("Instruções ignoradas; minuta correta.").run()
        tela.button(key="aprovar").click().run()
        self.assertEqual(self._eventos()[0]["justificativa"], "Instruções ignoradas; minuta correta.")

    def test_avisos_de_sucesso_e_de_alerta(self):
        tela = self._ate_minuta()
        tela.button(key="aprovar").click().run()
        self.assertTrue(any("aviso-toast alerta" in aviso for aviso in self._avisos(tela)))

        tela = self._aprovar_texto(tela)
        avisos = self._avisos(tela)
        self.assertTrue(any("aviso-toast sucesso" in aviso and "Minuta aprovada" in aviso for aviso in avisos))

    def test_origem_e_campos_editados_na_revisao(self):
        tela = self._ate_revisao()
        self.assertIn("Origem: dados/originais/solicitacao_texto.txt", _texto(tela))
        tela.text_input(key="edit_turno").set_value("matutino").run()
        legendas = "\n".join(item.value for item in tela.caption)
        self.assertIn("Editados por você: Turno", legendas)

    def test_erro_aparece_em_cartao_e_some_ao_corrigir(self):
        tela = self._ate_minuta()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.button(key="aprovar").click().run()
        cartoes = [item.value for item in tela.markdown if "cartao-erro" in item.value and "<style>" not in item.value]
        self.assertEqual(len(cartoes), 1)
        self.assertIn("Informe o cargo ou setor de quem assina.", cartoes[0])

        tela.text_input(key="cargo_setor").set_value("Secretaria").run()
        self.assertFalse(any("cartao-erro" in item.value and "<style>" not in item.value for item in tela.markdown))

        tela.button(key="aprovar").click().run()
        self.assertIn("Confira nome, protocolo e datas antes de aprovar.", _texto(tela))
