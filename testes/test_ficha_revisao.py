"""Revisão na Ficha: corrigir campos, editar a minuta e salvar a aprovada (RF20 e RF24).

Rodam offline: a análise e o RAG são simulados, o log e a pasta das minutas aprovadas
são temporários (conftest).
"""

import json
import unittest
from datetime import date
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import testes.test_ficha_orientacoes as base
from src import audit, consulta_acervo, minuta_fundamentada
from src.consulta_acervo import (
    GUIA_FICHA_BLOQUEADA,
    GUIA_FICHA_EM_REVISAO,
    MENSAGEM_APROVAR_SEM_MINUTA,
    MENSAGEM_AVISO_DE_IA_REMOVIDO,
    guia_da_revisao,
    salvar_minuta_aprovada,
)
from src.nlp import Analise
from src.schemas import ErroValidacao, ResultadoValidacao, corrigir_solicitacao, validar_correcao
from testes.test_rf20_regras import _solicitacao

TEXTO = "Sou Camila, protocolo 2026-000188. Faço o Técnico em Agropecuária em Mimoso."
INCOERENCIA = ErroValidacao(
    "regra", "incoerencia_interna", "campos_ausentes", "campos_ausentes difere dos campos nulos."
)


def _analise(categoria="matricula", bloqueada=False):
    solicitacao = _solicitacao(categoria=categoria, solicitante="Camila", protocolo="2026-000188")
    erros = [INCOERENCIA] if bloqueada else []
    decisao = "revisar" if bloqueada else "aceita"
    validacao = ResultadoValidacao(decisao, solicitacao, [{"erros": []}], erros, {"arquivo": "ficha"})
    return Analise(validacao, "texto", "versao")


class TestRevisaoNaFicha(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.log = Path(temp.name) / "execucoes.jsonl"
        self.rag = base.RagFalso()
        for alvo in (
            patch.object(audit, "ARQUIVO_REGISTRO", self.log),
            patch("src.acervo_operacao.mensagem_do_indice", return_value=""),
            patch(
                "src.minuta_fundamentada.consultar_orientacoes",
                partial(minuta_fundamentada.consultar_orientacoes, responder=self.rag),
            ),
        ):
            alvo.start()
            self.addCleanup(alvo.stop)

    def _ficha(self, categoria="matricula", bloqueada=False):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n", default_timeout=20
        )
        tela.run()
        tela.sidebar.radio(key="rf20_area").set_value("ficha").run()
        with patch("src.nlp.analisar_solicitacao", return_value=_analise(categoria, bloqueada)):
            tela.text_area(key="rf20_texto_ficha").set_value(TEXTO).run()
            tela.button(key="rf20_analisar").click().run()
        self.assertFalse(tela.exception)
        return tela

    def _corrigir(self, tela, **valores):
        rodada = tela.session_state["rf20_rodada"] if "rf20_rodada" in tela.session_state else 0
        for nome, valor in valores.items():
            if nome == "categoria":
                tela.selectbox(key=f"rf20_corrigir_categoria_{rodada}").set_value(valor).run()
            else:
                tela.text_input(key=f"rf20_corrigir_{nome}_{rodada}").input(valor).run()
        tela.button(key="rf20_aplicar_correcoes").click().run()
        self.assertFalse(tela.exception)
        return tela

    def _editar_minuta(self, tela, trocar, por):
        tela.toggle(key="rf20_editar_minuta").set_value(True).run()
        caixa = next(item for item in tela.text_area if item.label == "Texto da minuta")
        caixa.set_value(caixa.value.replace(trocar, por)).run()
        return tela

    def _assinar(self, tela, botao="rf20_aprovar"):
        tela.text_input(key="rf20_revisor").input("Ana Beatriz").run()
        tela.text_input(key="rf20_cargo").input("Secretaria").run()
        tela.button(key=botao).click().run()
        self.assertFalse(tela.exception)
        return tela

    def _eventos(self, nome):
        if not self.log.is_file():
            return []
        return [e for e in map(json.loads, self.log.read_text(encoding="utf-8").splitlines())
                if e["evento"] == nome]

    def _salvas(self):
        pasta = Path(consulta_acervo.PASTA_MINUTAS_APROVADAS)
        return sorted(pasta.glob("ficha_*.md")) if pasta.is_dir() else []

    def _texto(self, tela):
        return base._texto(tela)

    # F1 e F3

    def test_ficha_bloqueada_mostra_o_guia_e_o_formulario(self):
        tela = self._ficha(bloqueada=True)

        self.assertIn(GUIA_FICHA_BLOQUEADA, "\n".join(item.value for item in tela.info))
        self.assertEqual(tela.text_input(key="rf20_corrigir_solicitante_0").value, "Camila")
        self.assertEqual(tela.text_input(key="rf20_corrigir_curso_0").value, "")

    def test_corrigir_resolve_o_bloqueio_e_monta_a_minuta(self):
        tela = self._corrigir(
            self._ficha(bloqueada=True), curso="Técnico em Agropecuária", turno="noturno"
        )
        texto = self._texto(tela)

        self.assertIn("Correções aplicadas: Curso, Turno. Informado pelo servidor: Turno.",
                      "\n".join(item.value for item in tela.success))
        self.assertIn("Curso: Técnico em Agropecuária", texto)
        self.assertNotIn(GUIA_FICHA_BLOQUEADA, texto)
        self.assertIn("**Estado:** Pendente", texto)
        evento = self._eventos("revisao_campos_ficha")[0]
        self.assertEqual(evento["campos_alterados"], ["curso", "turno"])
        self.assertEqual(evento["informados_pelo_servidor"], ["turno"])
        self.assertNotIn("noturno", json.dumps(evento, ensure_ascii=False))

    def test_data_impossivel_nao_aplica_a_correcao(self):
        tela = self._corrigir(self._ficha(bloqueada=True), data_solicitacao="31/02/2026")

        self.assertIn("Correção não aplicada", "\n".join(item.value for item in tela.error))
        self.assertIn(GUIA_FICHA_BLOQUEADA, "\n".join(item.value for item in tela.info))
        self.assertEqual(self._eventos("revisao_campos_ficha"), [])

    def test_campo_fora_do_texto_aparece_como_informado_pelo_servidor(self):
        tela = self._corrigir(self._ficha(), curso="Técnico em Agropecuária", turno="noturno")

        texto = self._texto(tela)
        self.assertIn("informado pelo servidor: Turno", texto)
        self.assertNotIn("informado pelo servidor: Curso", texto)

    def test_categoria_corrigida_para_matricula_libera_a_busca(self):
        tela = self._ficha(categoria="frequencia_cancelamento")
        self.assertNotIn("rf20_buscar_orientacoes", [botao.key for botao in tela.button])

        self._corrigir(tela, categoria="matricula")

        self.assertIn("rf20_buscar_orientacoes", [botao.key for botao in tela.button])

    def test_guia_na_revisao_e_nao_na_pendente(self):
        ficha = {"linhas": {"categoria": "matricula"}, "minuta_bloqueada": False}

        self.assertEqual(guia_da_revisao(ficha, "revisar"), GUIA_FICHA_EM_REVISAO)
        self.assertIsNone(guia_da_revisao(ficha, "pendente"))

    # F2

    def test_minuta_editada_e_aprovada_fica_salva_e_assinada(self):
        tela = self._ficha()
        tela.button(key="rf20_buscar_orientacoes").click().run()
        self._editar_minuta(tela, "Permanecemos à disposição",
                            "Leve também RG e CPF. Permanecemos à disposição")

        self._assinar(tela)

        salvas = self._salvas()
        self.assertEqual(len(salvas), 1)
        conteudo = salvas[0].read_text(encoding="utf-8")
        self.assertIn("Leve também RG e CPF.", conteudo)
        self.assertIn("Ana Beatriz", conteudo)
        self.assertIn("Secretaria", conteudo)
        self.assertNotIn("[NOME DO SERVIDOR RESPONSÁVEL]", conteudo)
        self.assertIn("Minuta elaborada com apoio de IA", conteudo)
        self.assertTrue(tela.toast[0].value.startswith("Ficha aprovada e registrada. Minuta salva em"))
        aprovacao = self._eventos("minuta_aprovada_ficha")[0]
        self.assertTrue(aprovacao["editada_pelo_servidor"])
        decisao = [e for e in self._eventos("decisao") if e["decisao"] == "aprovada"][0]
        self.assertEqual(decisao["id_execucao"], aprovacao["id_execucao"])

    def test_minuta_sem_edicao_e_salva_como_montada(self):
        tela = self._ficha()
        tela.button(key="rf20_buscar_orientacoes").click().run()

        self._assinar(tela)

        self.assertEqual(len(self._salvas()), 1)
        self.assertFalse(self._eventos("minuta_aprovada_ficha")[0]["editada_pelo_servidor"])

    def test_apagar_o_aviso_de_ia_recusa_a_aprovacao(self):
        tela = self._ficha()
        self._editar_minuta(tela, "Minuta elaborada com apoio de IA", "Minuta da secretaria")

        self._assinar(tela)

        self.assertIn(MENSAGEM_AVISO_DE_IA_REMOVIDO, "\n".join(item.value for item in tela.error))
        self.assertEqual(self._salvas(), [])
        self.assertNotIn("aprovada", [e["decisao"] for e in self._eventos("decisao")])

    def test_aprovar_sem_minuta_e_recusado(self):
        tela = self._assinar(self._ficha(bloqueada=True))

        self.assertIn(MENSAGEM_APROVAR_SEM_MINUTA, "\n".join(item.value for item in tela.error))
        self.assertEqual(self._salvas(), [])

    def test_rejeitar_nao_salva_minuta(self):
        tela = self._ficha()
        tela.text_area(key="rf20_justificativa").input("Falta conferir a chamada.").run()

        tela.button(key="rf20_rejeitar").click().run()

        self.assertTrue(tela.toast[0].value.startswith("Ficha rejeitada e registrada."))
        self.assertEqual(self._salvas(), [])


class TestCorrecaoNoContrato(unittest.TestCase):
    def setUp(self):
        self.original = _solicitacao(
            categoria="matricula", solicitante="Camila", protocolo="2026-000188",
            requer_revisao=True, motivos_revisao=["pedido ambíguo"],
            alertas_seguranca=["instrução no texto"],
        ).model_dump()

    def test_recalcula_ausentes_tira_motivos_do_modelo_e_mantem_alertas(self):
        corrigida = corrigir_solicitacao(self.original, {"curso": "Agropecuária", "turno": " "})

        self.assertNotIn("curso", corrigida.campos_ausentes)
        self.assertIn("turno", corrigida.campos_ausentes)
        self.assertFalse(corrigida.requer_revisao)
        self.assertEqual(corrigida.motivos_revisao, [])
        self.assertEqual(corrigida.alertas_seguranca, ["instrução no texto"])

    def test_inicio_antes_da_solicitacao_bloqueia(self):
        texto = TEXTO + " Enviado em 12/06/2026."
        corrigida = corrigir_solicitacao(
            self.original, {"data_solicitacao": "12/06/2026", "data_inicio": "01/06/2026"}
        )

        bloqueios, alterados, informados = validar_correcao(
            self.original, corrigida, texto, hoje=date(2026, 10, 31)
        )

        self.assertEqual([erro.categoria for erro in bloqueios], ["data_incoerente"])
        self.assertEqual(alterados, ["data_solicitacao", "data_inicio"])
        self.assertEqual(informados, ["data_inicio"])

    def test_campo_fora_do_contrato_e_recusado(self):
        with self.assertRaises(ValueError):
            corrigir_solicitacao(self.original, {"resumo": "outro resumo"})


class TestMinutaAprovadaSalva(unittest.TestCase):
    def test_nao_sobrescreve(self):
        with TemporaryDirectory() as pasta:
            salvar_minuta_aprovada("id-1", "primeira", pasta=Path(pasta))
            salvar_minuta_aprovada("id-2", "segunda", pasta=Path(pasta))

            with self.assertRaises(FileExistsError):
                salvar_minuta_aprovada("id-1", "outra", pasta=Path(pasta))

            self.assertEqual((Path(pasta) / "ficha_id-1.md").read_text(encoding="utf-8"), "primeira\n")
            self.assertEqual(len(list(Path(pasta).glob("ficha_*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
