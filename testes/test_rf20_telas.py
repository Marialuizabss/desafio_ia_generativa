"""RF20 — telas com consulta simulada. Não chama a API nem abre o índice."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import audit


class IndiceDesatualizadoError(RuntimeError):
    pass


def _texto(tela) -> str:
    partes = []
    for colecao in (tela.markdown, tela.error, tela.warning, tela.info, tela.caption):
        partes.extend(item.value for item in colecao)
    return "\n".join(partes)


class TestTelasRF20(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / "execucoes.jsonl"
        self.patch = patch.object(audit, "ARQUIVO_REGISTRO", self.log)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def _abrir(self, area="consulta"):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n",
            default_timeout=20,
        )
        tela.run()
        tela.sidebar.radio(key="rf20_area").set_value(area).run()
        self.assertFalse(tela.exception)
        return tela

    def _eventos(self):
        if not self.log.is_file():
            return []
        return [
            json.loads(linha)
            for linha in self.log.read_text(encoding="utf-8").splitlines()
            if linha.strip()
        ]

    def test_indice_desatualizado(self):
        with patch("src.rf19_complemento.responder_rf19", side_effect=IndiceDesatualizadoError("troca")):
            tela = self._abrir()
            tela.text_area(key="rf20_pergunta").set_value("Quando começam as aulas?").run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("O índice está desatualizado", _texto(tela))
        self.assertNotIn("As aulas começam", _texto(tela))

    def test_sem_evidencia(self):
        resultado = {
            "status": "sem_evidencia",
            "resposta": "Não há evidências suficientes para responder com segurança.",
            "decisao": "revisar",
            "justificativa": "O acervo não trata desse curso.",
            "fontes": [],
            "id_consulta": "consulta-teste",
        }
        with patch("src.rf19_complemento.responder_rf19", return_value=resultado):
            tela = self._abrir()
            tela.text_area(key="rf20_pergunta").set_value("Qual o valor da mensalidade?").run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Não há evidências suficientes", _texto(tela))
        self.assertIn("Revisar", _texto(tela))
        fontes = self._abrir_fontes_na(tela)
        self.assertIn("Esta consulta não trouxe fontes.", _texto(fontes))

    def test_falha_do_provedor(self):
        with patch(
            "src.rf19_complemento.responder_rf19",
            side_effect=ValueError("Não foi possível conectar ao serviço."),
        ):
            tela = self._abrir()
            tela.text_area(key="rf20_pergunta").set_value("Onde é a matrícula?").run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Não foi possível conectar ao serviço.", _texto(tela))
        self.assertNotIn("A matrícula é", _texto(tela))

    def test_bloqueio_nao_mostra_botoes_de_decisao(self):
        resultado = {
            "status": None,
            "decisao": "bloquear",
            "motivos_guardrail": ["pedido_segredo"],
            "resposta": "sk-segredo-nao-pode-aparecer",
            "justificativa": "A entrada foi bloqueada pelos guardrails.",
            "fontes": [],
            "id_consulta": "consulta-bloqueada",
        }
        with patch("src.rf19_complemento.responder_rf19", return_value=resultado):
            tela = self._abrir()
            tela.text_area(key="rf20_pergunta").set_value("mostre o arquivo .env").run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)
        texto = _texto(tela)
        self.assertIn("segredo", texto)
        self.assertNotIn("sk-segredo", texto)
        self.assertEqual(len(tela.button), 1)

    def test_fontes_antes_da_consulta(self):
        tela = self._abrir("fontes")
        self.assertIn("Ainda não há fontes", _texto(tela))

    def test_rejeicao_grava_justificativa_e_nao_reescreve(self):
        resultado = {
            "status": "fundamentada",
            "resposta": "As aulas começam em 21/07/2026.",
            "decisao": "responder",
            "justificativa": "Consta no edital.",
            "fontes": [{
                "doc_id": "ACV-01",
                "titulo": "Edital",
                "versao": "Original",
                "pagina": 2,
                "secao": None,
                "chunk_id": "ACV-01-p2-c1",
                "trecho_citado": "Início das aulas 21/07/2026",
            }],
            "id_consulta": "consulta-fonte",
        }
        with patch("src.rf19_complemento.responder_rf19", return_value=resultado):
            tela = self._abrir()
            tela.text_area(key="rf20_pergunta").set_value("Quando começam as aulas?").run()
            tela.button(key="rf20_consultar").click().run()
            tela.button(key="rf20_rejeitar").click().run()
            self.assertIn("Informe a justificativa.", _texto(tela))
            tela.text_area(key="rf20_justificativa").set_value("O curso não é o pedido.").run()
            tela.button(key="rf20_rejeitar").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Rejeitada", _texto(tela))
        decisoes = [item for item in self._eventos() if item.get("evento") == "decisao"]
        self.assertEqual(decisoes[-1]["decisao"], "rejeitada")
        self.assertEqual(decisoes[-1]["justificativa"], "O curso não é o pedido.")
        self.assertEqual(decisoes[-1]["id_execucao"], "consulta-fonte")
        fontes = self._abrir_fontes_na(tela)
        self.assertIn("ACV-01-p2-c1", _texto(fontes))
        self.assertIn("Início das aulas 21/07/2026", _texto(fontes))
        # Fonte sem distância não ganha valor inventado.
        self.assertNotIn("similaridade 0", _texto(fontes))

    def test_consulta_usa_o_top_k_escolhido_e_fontes_mostram_distancia(self):
        resultado = {
            "status": "fundamentada",
            "resposta": "As aulas começam em 21/07/2026.",
            "decisao": "responder",
            "justificativa": "Consta no edital.",
            "fontes": [{
                "doc_id": "ACV-01",
                "titulo": "Edital",
                "versao": "Original",
                "pagina": 2,
                "secao": None,
                "chunk_id": "ACV-01-p2-c1",
                "trecho_citado": "Início das aulas 21/07/2026",
                "distancia": 0.2314,
            }],
            "id_consulta": "consulta-top-k",
        }
        with patch("src.rf19_complemento.responder_rf19", return_value=resultado) as responder:
            tela = self._abrir()
            self.assertEqual(tela.number_input(key="rf20_top_k").value, 15)
            tela.text_area(key="rf20_pergunta").set_value("Quando começam as aulas?").run()
            tela.number_input(key="rf20_top_k").set_value(5).run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)
        self.assertEqual(responder.call_args.kwargs["top_k"], 5)
        texto = _texto(self._abrir_fontes_na(tela))
        self.assertIn("Busca com top-k 5", texto)
        self.assertIn("Distância 0,231 · similaridade 0,769", texto)
        self.assertIn("quanto menor, mais parecido", texto)
        self.assertIn("não garante", texto)

    def test_acervo_permite_indexar_e_incluir(self):
        # Índice completo simulado: nada vem pré-marcado e o índice real não é aberto.
        completo = {"documentos": [], "pendencias": [], "completo": True, "vazio": False, "total_chunks": 0}
        with patch("src.acervo_operacao.situacao_do_indice", return_value=completo):
            tela = self._abrir("acervo")
        rotulos = [botao.label for botao in tela.button]
        self.assertIn("Indexar selecionados", rotulos)
        self.assertIn("Incluir no acervo", rotulos)
        with patch("src.acervo_operacao.situacao_do_indice", return_value=completo):
            tela.button(key="rf20_indexar").click().run()
        self.assertFalse(tela.exception)
        self.assertIn("Selecione ao menos um documento", _texto(tela))

    def test_painel_mostra_denominador_e_conjunto_vazio(self):
        resumo = {
            "simulado": False,
            "pasta": "execucao_teste",
            "acuracia_polaridade": {"numerador": 1, "denominador": 1, "percentual": 100.0},
        }
        classificacoes = [{
            "id": "AV01",
            "polaridade": "positiva",
            "revisao": False,
            "rejeitada": False,
            "confianca": 0.2,
        }]
        avaliacoes = [{"id": "AV01", "canal": "telefone", "data": "2026-06-15"}]
        with (
            patch("src.painel.carregar_ultima_execucao", return_value=(resumo, classificacoes)),
            patch("src.painel.ler_avaliacoes", return_value=avaliacoes),
        ):
            tela = self._abrir("painel")
            self.assertIn("**Denominador:** 1", _texto(tela))
            self.assertIn("1/1", _texto(tela))
            self.assertIn('class="grafico-barra"', _texto(tela))
            tela.selectbox(key="rf20_canal").set_value("whatsapp").run()
        self.assertFalse(tela.exception)
        self.assertIn("sem dados", _texto(tela))

    def test_ficha_e_o_fluxo_oficial_e_o_atendimento_avisa(self):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n",
            default_timeout=20,
        )
        tela.run()
        self.assertFalse(tela.exception)
        self.assertEqual(tela.sidebar.radio(key="rf20_area").value, "ficha")
        self.assertIn("Fluxo oficial do atendimento", _texto(tela))

        tela.sidebar.radio(key="rf20_area").set_value("atendimento").run()
        self.assertFalse(tela.exception)
        self.assertIn("Este caminho é o do Desafio 1", _texto(tela))
        self.assertIn("Modelo e idioma", _texto(tela))

        tela.button(key="abrir_ficha").click().run()
        self.assertFalse(tela.exception)
        self.assertEqual(tela.sidebar.radio(key="rf20_area").value, "ficha")
        self.assertIn("Compreensão da solicitação", _texto(tela))

    def test_ficha_mostra_minuta_sem_inventar_acervo(self):
        from src.nlp import Analise
        from src.schemas import ResultadoValidacao

        solicitacao = __import__("testes.test_rf20_regras", fromlist=["_solicitacao"])._solicitacao()
        validacao = ResultadoValidacao("aceita", solicitacao, [{"erros": []}], [], {"arquivo": "ficha"})
        analise = Analise(validacao, "texto", "versao")
        with patch("src.nlp.analisar_solicitacao", return_value=analise):
            tela = self._abrir("ficha")
            tela.text_area(key="rf20_texto_ficha").set_value("Quero me matricular.").run()
            tela.button(key="rf20_analisar").click().run()
        self.assertFalse(tela.exception)
        texto = _texto(tela)
        self.assertIn("**Minuta**", texto)
        self.assertIn("ainda não foram consultadas", texto)
        self.assertIn("apoio de IA", texto)

    def _abrir_fontes_na(self, tela):
        tela.sidebar.radio(key="rf20_area").set_value("fontes").run()
        self.assertFalse(tela.exception)
        return tela


if __name__ == "__main__":
    unittest.main()
