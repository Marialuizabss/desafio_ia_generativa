import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import audit, fluxo, peca_orientacao
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
            patch.object(peca_orientacao, "BASE_DIR", self.base),
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
        tela.sidebar.radio(key="rf20_area").set_value("atendimento").run()
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

    def _nomes(self):
        return [evento["decisao"] for evento in self._eventos()]

    def _evento(self, decisao):
        return next(evento for evento in reversed(self._eventos()) if evento["decisao"] == decisao)

    def _revisoes(self):
        if not self.log.is_file():
            return []
        linhas = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines() if linha.strip()]
        return [linha for linha in linhas if linha.get("evento") == "revisao_campos"]

    def test_rejeicao_sem_justificativa_nao_grava(self):
        tela = self._ate_revisao()
        tela.button(key="pedir_revisao").click().run()
        tela.text_area(key="justificativa_revisao").set_value("   ").run()
        tela.button(key="confirmar_revisao").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("Informe a justificativa.", _texto(tela))
        self.assertEqual(self._eventos(), [])
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        self.assertEqual(self.original.read_text(encoding="utf-8"), "Pedido original")
        self.assertNotIn("MINUTA_DO_MODELO_OCULTA", _texto(tela))
        self.audio.assert_not_called()

    def test_rejeicao_na_etapa_3_grava_e_pode_gerar_de_novo(self):
        tela = self._ate_revisao()
        antes = list(self.chamadas)
        tela.button(key="pedir_revisao").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_revisao").set_value("Protocolo inventado.").run()
        tela.button(key="confirmar_revisao").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("Gerar de novo chama o modelo outra vez.", _texto(tela))
        self.assertNotIn("MINUTA_DO_MODELO_OCULTA", _texto(tela))
        self.assertEqual(self.chamadas, antes)
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        eventos = self._eventos()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["decisao"], "revisar")
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
        self.assertEqual(self._nomes(), ["revisar"])
        preservado = self.base / "dados" / "processados" / "extracao_pedido__teste-edicao.json"
        self.assertEqual(preservado.read_text(encoding="utf-8"), '{"evidencia": true}\n')
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), '{"evidencia": true}\n')

        tela.button(key="prosseguir").click().run()
        self.assertFalse(tela.exception)
        self.assertEqual(self._nomes(), ["revisar", "pendente"])
        self.assertEqual(self._eventos()[-1]["id_execucao"], "teste-nova")

    def test_rejeicao_na_etapa_4_encerra_sem_correcao(self):
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
        self.assertIn("nova execução", _texto(tela))
        self.assertIn("Joana Lima", _texto(tela))
        self.assertEqual(self.extracao.read_text(encoding="utf-8"), gravado)
        self.assertEqual(self._nomes(), ["pendente", "rejeitada"])
        self.assertEqual(self._evento("rejeitada")["justificativa"], "Nome do solicitante errado.")
        chaves = [botao.key for botao in tela.button]
        self.assertNotIn("corrigir_campos", chaves)
        self.assertNotIn("gerar_de_novo", chaves)
        self.assertNotIn("voltar", chaves)
        self.audio.assert_not_called()

        with self.assertRaises(ValueError):
            audit.registrar_decisao(
                "teste-edicao", "aprovada", revisor="Ana", cargo_setor="Secretaria",
            )
        self.assertEqual(len(self._eventos()), 2)

    def test_aprovacao_na_etapa_4_grava_sem_gerar_audio(self):
        tela = self._ate_revisao()
        tela.button(key="prosseguir").click().run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Informe o nome do revisor.", _texto(tela))
        self.assertEqual(self._nomes(), ["pendente"])

        tela.text_input(key="revisor").set_value("Ana").run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Informe o cargo ou setor de quem assina.", _texto(tela))
        self.assertEqual(self._nomes(), ["pendente"])

        tela.text_input(key="cargo_setor").set_value("Secretaria Escolar").run()
        tela.button(key="aprovar").click().run()
        self.assertIn("Confira nome, protocolo e datas antes de aprovar.", _texto(tela))
        self.assertEqual(self._nomes(), ["pendente"])

        tela.checkbox(key="conferencia_critica").set_value(True).run()
        tela.button(key="aprovar").click().run()

        self.assertFalse(tela.exception)
        self.assertIn("Aprovada", _texto(tela))
        self.assertIn("faltam dados da solicitação", _texto(tela))
        eventos = self._eventos()
        self.assertEqual(self._nomes(), ["pendente", "aprovada"])
        self.assertNotIn("motivos", eventos[0])
        self.assertEqual(eventos[1]["decisao"], "aprovada")
        self.assertEqual(eventos[1]["motivos"], ["faltam dados da solicitação"])
        self.assertEqual(eventos[1]["id_execucao"], "teste-edicao")
        self.assertEqual(eventos[1]["revisor"], "Ana")
        self.assertEqual(eventos[1]["justificativa"], "")
        self.assertTrue(eventos[1]["conferencia_dados_criticos"])
        self.audio.assert_not_called()

        aprovada = self.base / eventos[1]["arquivo_minuta"]
        self.assertEqual(aprovada.parent, self.base / "resultados" / "minutas" / "aprovadas")
        self.assertIn("Prezado(a) Ana", aprovada.read_text(encoding="utf-8"))
        self.assertIn(eventos[1]["arquivo_minuta"], "\n".join(item.value for item in tela.caption))
        with self.assertRaises(ValueError):
            audit.registrar_decisao(
                "teste-edicao", "rejeitada", justificativa="Mudei de ideia.",
            )
        self.assertEqual(self._nomes(), ["pendente", "aprovada"])
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
        self.assertEqual(self._nomes(), ["pendente"])
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

        decisao = self._evento("aprovada")
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
        self.assertEqual(tela.session_state["revisor"], "")
        self.assertEqual(tela.session_state["cargo_setor"], "")
        tela.text_area(key="rascunho_texto").set_value("Outro pedido.").run()
        tela.button(key="prosseguir").click().run()
        tela.button(key="prosseguir").click().run()

        self.assertFalse(tela.exception)
        self.assertNotIn("revisor", [campo.key for campo in tela.text_input])
        self.assertIn("Atendimento encerrado.", "\n".join(item.value for item in tela.caption))

    def test_corrigir_campos_mantem_o_servidor(self):
        tela = self._ate_minuta()
        tela.button(key="pedir_revisao").click().run()
        tela.text_input(key="revisor").set_value("Ana Beatriz").run()
        tela.text_area(key="justificativa_revisao").set_value("Turno errado.").run()
        tela.button(key="confirmar_revisao").click().run()
        tela.button(key="corrigir_campos").click().run()
        tela.button(key="prosseguir").click().run()

        self.assertEqual(tela.text_input(key="revisor").value, "Ana Beatriz")

    def _caixas_conferencia(self, tela):
        return [caixa for caixa in tela.checkbox if caixa.key.startswith("conferido_")]

    def test_audio_confere_os_dados_na_etapa_3_antes_da_minuta(self):
        self.registro["modalidade"] = "audio"
        tela = self._ate_revisao()
        caixas = self._caixas_conferencia(tela)
        self.assertEqual(len(caixas), 4)
        self.assertIn("Nome do solicitante: Ana", [caixa.label for caixa in caixas])
        self.assertIn("Ouvir o áudio original", [item.label for item in tela.expander])

        caixas[0].check().run()
        tela.button(key="prosseguir").click().run()
        self.assertIn("Avaliação humana", _texto(tela))
        self.assertIn("Confira com o original: Protocolo, Data da solicitação, Data de início.", _texto(tela))
        self.assertEqual(self._revisoes(), [])

        for caixa in self._caixas_conferencia(tela):
            caixa.check()
        tela.run()
        tela.button(key="prosseguir").click().run()
        self.assertIn("Rascunho montado com os campos revisados.", _texto(tela))
        self.assertEqual(self._caixas_conferencia(tela), [])
        self.assertIn("conferidos com o original antes de montar a minuta", "\n".join(c.value for c in tela.caption))
        revisao = self._revisoes()[0]
        self.assertEqual(revisao["dados_conferidos"], ["solicitante", "protocolo", "data_solicitacao", "data_inicio"])

        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_input(key="cargo_setor").set_value("Secretaria").run()
        tela.button(key="aprovar").click().run()
        decisao = self._evento("aprovada")
        self.assertEqual(decisao["dados_conferidos"], ["solicitante", "protocolo", "data_solicitacao", "data_inicio"])

    def test_corrigir_campo_desmarca_so_a_conferencia_dele(self):
        self.registro["modalidade"] = "imagem"
        tela = self._ate_revisao()
        self.assertIn("Ver a ficha original", [item.label for item in tela.expander])
        for caixa in self._caixas_conferencia(tela):
            caixa.check()
        tela.run()
        tela.text_input(key="edit_protocolo").set_value("2026-000143").run()

        marcadas = {caixa.label: caixa.value for caixa in self._caixas_conferencia(tela)}
        self.assertFalse(marcadas["Protocolo: 2026-000143"])
        self.assertTrue(marcadas["Nome do solicitante: Ana"])

    def test_texto_nao_tem_conferencia_na_etapa_3(self):
        tela = self._ate_revisao()
        self.assertEqual(self._caixas_conferencia(tela), [])
        tela.button(key="prosseguir").click().run()
        self.assertIn("conferencia_critica", [caixa.key for caixa in tela.checkbox])
        self.assertNotIn("dados_conferidos", self._revisoes()[0])

    def test_alerta_mostra_cartao_e_exige_justificativa(self):
        self.registro["alertas_seguranca"] = ["Tentativa de ignorar instruções."]
        tela = self._ate_revisao()
        self.assertTrue(any("alerta-seguranca" in item.value for item in tela.markdown))
        tela.button(key="prosseguir").click().run()

        tela = self._aprovar_texto(tela)
        self.assertIn("Há alerta de segurança: justifique a aprovação.", _texto(tela))
        self.assertEqual(self._nomes(), ["pendente"])

        tela.text_area(key="justificativa_aprovacao").set_value("Instruções ignoradas; minuta correta.").run()
        tela.button(key="aprovar").click().run()
        self.assertEqual(self._evento("aprovada")["justificativa"], "Instruções ignoradas; minuta correta.")

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

    def test_pdf_so_depois_de_aprovar_assinado_e_salvo(self):
        import pymupdf

        tela = self._ate_minuta()
        self.assertEqual(tela.get("download_button"), [])
        tela = self._aprovar_texto(tela, servidor="Ana Beatriz", cargo="SECITECI")

        self.assertEqual(len(tela.get("download_button")), 1)
        decisao = self._evento("aprovada")
        pdf = self.base / decisao["arquivo_pdf"]
        self.assertEqual(pdf.with_suffix(".md"), self.base / decisao["arquivo_minuta"])
        with pymupdf.open(pdf) as documento:
            texto = "\n".join(pagina.get_text() for pagina in documento)
        self.assertIn("Ana Beatriz", texto)
        self.assertIn("GOVERNO DE MATO GROSSO", texto)
        self.assertIn("Origem: solicitacao_texto.txt", texto)
        self.assertIn("Aprovada por Ana Beatriz (SECITECI)", texto)
        self.assertNotIn("[NOME DO SERVIDOR RESPONSÁVEL]", texto)

    def test_rejeicao_nao_mostra_pdf(self):
        tela = self._ate_minuta()
        tela.button(key="rejeitar").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_rejeicao").set_value("Dados errados.").run()
        tela.button(key="confirmar_rejeicao").click().run()
        self.assertEqual(tela.get("download_button"), [])
        self.assertFalse((self.base / "resultados" / "minutas" / "aprovadas").exists())

    def test_falha_no_pdf_nao_registra_e_nao_deixa_arquivos(self):
        tela = self._ate_minuta()
        with patch("src.interface.gerar_pdf_minuta", side_effect=RuntimeError("PDF falhou.")):
            tela = self._aprovar_texto(tela)
        self.assertEqual(self._nomes(), ["pendente"])
        aprovadas = self.base / "resultados" / "minutas" / "aprovadas"
        self.assertEqual(list(aprovadas.iterdir()) if aprovadas.exists() else [], [])
        self.assertIn("PDF falhou.", _texto(tela))

    def test_origem_mostra_a_duracao_do_audio(self):
        self.registro["modalidade"] = "audio"
        self.registro["duracao_audio_segundos"] = 89.16
        tela = self._ate_revisao()
        self.assertIn("lido por gpt-4o-transcribe · duração 1min29s", _texto(tela))

    # ---- B3: áudio da minuta aprovada

    def _sintese_falsa(self):
        chamadas = []

        def sintetizar(minuta, destino):
            chamadas.append(minuta)
            destino = Path(destino)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(b"mp3")
            falado = destino.with_name(f"{destino.stem}_texto_falado.txt")
            falado.write_text("texto falado", encoding="utf-8")
            return {
                "arquivo_audio": destino, "arquivo_texto_falado": falado, "modelo": "gpt-4o-mini-tts",
                "voz": "nova", "instrucoes": "x", "instrucoes_aplicadas": True,
                "duracao_audio_segundos": None, "tempo_geracao_segundos": 0.1, "custo_estimado_usd": None,
            }

        return chamadas, sintetizar

    def test_audio_so_depois_de_aprovar_e_gerado_uma_vez(self):
        tela = self._ate_minuta()
        self.assertNotIn("gerar_audio", [botao.key for botao in tela.button])

        tela = self._aprovar_texto(tela, servidor="Ana Beatriz", cargo="SECITECI")
        chamadas, sintetizar = self._sintese_falsa()
        with patch("src.fluxo.sintetizar_minuta", side_effect=sintetizar):
            tela.button(key="gerar_audio").click().run()
            self.assertFalse(tela.exception)
            self.assertEqual(len(tela.get("audio")), 1)
            self.assertNotIn("gerar_audio", [botao.key for botao in tela.button])
            tela.run()

        self.assertEqual(len(chamadas), 1)
        self.assertIn("Ana Beatriz", chamadas[0])
        self.assertNotIn("[NOME DO SERVIDOR RESPONSÁVEL]", chamadas[0])
        linhas = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines()]
        evento = [linha for linha in linhas if linha.get("evento") == "audio_minuta"][0]
        self.assertEqual(evento["resultado"], "sucesso")
        self.assertEqual(evento["id_execucao"], "teste-edicao")
        self.assertTrue(evento["arquivo_audio"].startswith("resultados/audios/audio_minuta_"))
        self.assertTrue((self.base / evento["arquivo_audio"]).is_file())

    def test_falha_no_audio_registra_erro_e_nao_deixa_arquivo(self):
        tela = self._aprovar_texto(self._ate_minuta())
        with patch("src.fluxo.sintetizar_minuta", side_effect=RuntimeError("voz indisponível")):
            tela.button(key="gerar_audio").click().run()

        self.assertFalse(tela.exception)
        self.assertTrue(any("aviso-toast erro" in item.value for item in tela.markdown if "<style>" not in item.value))
        linhas = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines()]
        evento = [linha for linha in linhas if linha.get("evento") == "audio_minuta"][0]
        self.assertEqual(evento["resultado"], "erro")
        audios = self.base / "resultados" / "audios"
        self.assertEqual(list(audios.iterdir()) if audios.exists() else [], [])

    def test_rejeicao_nao_oferece_audio(self):
        tela = self._ate_minuta()
        tela.button(key="rejeitar").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_rejeicao").set_value("Dados errados.").run()
        tela.button(key="confirmar_rejeicao").click().run()
        self.assertNotIn("gerar_audio", [botao.key for botao in tela.button])

    # ---- atendimento aprovado fica encerrado

    def test_depois_de_aprovar_nao_ha_voltar_e_o_quadro_fica(self):
        tela = self._aprovar_texto(self._ate_minuta())
        chaves = [botao.key for botao in tela.button]
        self.assertNotIn("voltar", chaves)
        self.assertIn("encerrar_caso", chaves)
        self.assertIn("Atendimento encerrado.", "\n".join(item.value for item in tela.caption))

        tela.session_state["etapa"] = 3
        tela.run()
        self.assertIn("Rascunho montado com os campos revisados.", _texto(tela))
        self.assertNotIn("aprovar", [botao.key for botao in tela.button])
        self.assertEqual(self._nomes(), ["pendente", "aprovada"])

    def test_revisao_na_minuta_permite_corrigir(self):
        tela = self._ate_minuta()
        tela.button(key="pedir_revisao").click().run()
        tela.text_input(key="revisor").set_value("Ana").run()
        tela.text_area(key="justificativa_revisao").set_value("Turno errado.").run()
        tela.button(key="confirmar_revisao").click().run()
        self.assertIn("corrigir_campos", [botao.key for botao in tela.button])
        self.assertEqual(self._nomes(), ["pendente", "revisar"])

    # ---- B4: peça de orientação (RF10)

    def _gerar_ilustracao_falsa(self, tela):
        from testes.test_peca_orientacao import cliente_de_imagem, png_base64

        (self.base / "dados" / "originais" / "brasao.png").write_bytes(
            (Path(__file__).resolve().parent.parent / "dados" / "originais" / "brasao.png").read_bytes()
        )
        with patch.object(peca_orientacao, "OpenAI", return_value=cliente_de_imagem(png_base64())):
            tela.button(key="gerar_ilustracao").click().run()
        return tela

    def test_peca_gerada_revisada_na_tela_e_mostrada(self):
        tela = self._aprovar_texto(self._ate_minuta())
        self.assertIn("Ainda não há ilustração aprovada", "\n".join(c.value for c in tela.caption))
        tela = self._gerar_ilustracao_falsa(tela)

        caixas = [caixa for caixa in tela.checkbox if caixa.key.startswith("ilustracao_")]
        self.assertEqual(len(caixas), 4)
        self.assertIn("Prévia da peça com esta ilustração", _texto(tela))
        self.assertIn("Ver a ilustração gerada inteira", [item.label for item in tela.expander])
        tela.button(key="aprovar_ilustracao").click().run()
        self.assertIn("Para aprovar, confira", _texto(tela))

        for caixa in [caixa for caixa in tela.checkbox if caixa.key.startswith("ilustracao_")]:
            caixa.check()
        tela.run()
        tela.button(key="aprovar_ilustracao").click().run()
        self.assertFalse(tela.exception)
        self.assertEqual(peca_orientacao.versao_vigente()["revisor"], "Ana Beatriz")
        self.assertIn("baixar_peca", [botao.key for botao in tela.get("download_button")])
        self.assertIn("Ilustração v01 gerada por IA", "\n".join(c.value for c in tela.caption))

    def test_reprovar_ilustracao_exige_observacao(self):
        tela = self._gerar_ilustracao_falsa(self._aprovar_texto(self._ate_minuta()))
        tela.button(key="reprovar_ilustracao").click().run()
        self.assertIn("Informe o motivo da reprovação.", _texto(tela))
        tela.text_area(key="ilustracao_nota_1").set_value("Apareceram letras.").run()
        tela.button(key="reprovar_ilustracao").click().run()
        self.assertIsNone(peca_orientacao.versao_vigente())
        self.assertEqual(peca_orientacao.carregar_versoes()[0]["revisao_humana"], "reprovada")
