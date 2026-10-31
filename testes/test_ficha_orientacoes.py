"""Orientações do acervo na Ficha (RF19, RF20 e RF24) e modelo carregado uma vez.

Rodam offline: a análise da solicitação e o RAG são simulados; nenhum modelo é
carregado e o índice real não é tocado.
"""

import json
import threading
import unittest
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import audit, minuta_fundamentada, vector_store
from src.consulta_acervo import (
    AVISO_PRIMEIRA_CONSULTA,
    MENSAGEM_ORIENTACOES_SO_MATRICULA,
    MOTIVO_SEM_ORIENTACOES,
    aviso_de_espera,
    exigir_revisao_sem_orientacoes,
    pode_buscar_orientacoes,
    resumo_das_orientacoes,
)
from src.nlp import Analise
from src.schemas import ResultadoValidacao
from testes.test_rf20_regras import _solicitacao

RESPOSTAS = {
    "documentos": "Apresentar cópia simples e original do comprovante de escolaridade.",
    "local": "Comparecer à Escola Técnica Estadual onde se inscreveu.",
    "período": "A matrícula da 1ª chamada vai de 15 a 19/06/2026.",
}
PAGINAS = {"documentos": 10, "local": 10, "período": 1}


def _assunto(pergunta):
    if "documentos" in pergunta:
        return "documentos"
    if "Onde" in pergunta:
        return "local"
    return "período"


class RagFalso:
    """Fundamenta cada assunto, menos os listados em `sem_evidencia`."""

    def __init__(self, sem_evidencia=()):
        self.sem_evidencia = set(sem_evidencia)
        self.perguntas = []

    def __call__(self, pergunta, top_k=15, nome_configuracao="principal"):
        self.perguntas.append(pergunta)
        assunto = _assunto(pergunta)
        if assunto in self.sem_evidencia:
            return {
                "status": "sem_evidencia", "decisao": "revisar", "resposta": None,
                "fontes": [], "justificativa": "O acervo não sustenta.",
                "id_consulta": f"rag-{assunto}",
            }
        doc_id = "ACV-04" if assunto == "período" else "ACV-01"
        return {
            "status": "fundamentada", "decisao": "responder", "resposta": RESPOSTAS[assunto],
            "fontes": [{
                "doc_id": doc_id, "titulo": doc_id, "versao": "1", "pagina": PAGINAS[assunto],
                "chunk_id": f"{doc_id}-{assunto}", "trecho_citado": RESPOSTAS[assunto],
            }],
            "justificativa": "Trecho do edital.", "id_consulta": f"rag-{assunto}",
        }


def _analise(categoria="matricula"):
    validacao = ResultadoValidacao(
        "aceita", _solicitacao(categoria=categoria), [{"erros": []}], [], {"arquivo": "ficha"}
    )
    return Analise(validacao, "texto", "versao")


def _texto(tela) -> str:
    partes = []
    for colecao in (tela.markdown, tela.error, tela.warning, tela.info, tela.caption):
        partes.extend(item.value for item in colecao)
    return "\n".join(partes)


class TestOrientacoesNaFicha(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.log = Path(temp.name) / "execucoes.jsonl"
        for alvo in (
            patch.object(audit, "ARQUIVO_REGISTRO", self.log),
            # Índice simulado completo: a busca não depende do índice real.
            patch("src.acervo_operacao.mensagem_do_indice", return_value=""),
        ):
            alvo.start()
            self.addCleanup(alvo.stop)
        self.rag = RagFalso()
        self._usar_rag(self.rag)

    def _usar_rag(self, rag):
        # A função real da Maria (combina os três assuntos), só com o RAG simulado.
        real = minuta_fundamentada.consultar_orientacoes
        alvo = patch(
            "src.minuta_fundamentada.consultar_orientacoes", partial(real, responder=rag)
        )
        alvo.start()
        self.addCleanup(alvo.stop)

    def _abrir(self, area):
        tela = AppTest.from_string(
            "from src.interface import renderizar\nrenderizar()\n", default_timeout=20
        )
        tela.run()
        tela.sidebar.radio(key="rf20_area").set_value(area).run()
        self.assertFalse(tela.exception)
        return tela

    def _analisar(self, tela, categoria="matricula"):
        tela.sidebar.radio(key="rf20_area").set_value("ficha").run()
        with patch("src.nlp.analisar_solicitacao", return_value=_analise(categoria)):
            tela.text_area(key="rf20_texto_ficha").set_value("Quero me matricular.").run()
            tela.button(key="rf20_analisar").click().run()
        self.assertFalse(tela.exception)
        return tela

    def _consultar_mimoso(self, tela):
        resultado = {
            "status": "fundamentada", "decisao": "responder",
            "resposta": "As aulas de Agropecuária em Mimoso começam em 05/10/2026.",
            "fontes": [{"doc_id": "ACV-07", "pagina": 1, "chunk_id": "ACV-07-p1-s1-c2"}],
            "justificativa": "Retificação nº 06.", "id_consulta": "consulta-livre",
        }
        tela.sidebar.radio(key="rf20_area").set_value("consulta").run()
        with patch("src.rf19_complemento.responder_rf19", return_value=resultado):
            tela.text_area(key="rf20_pergunta").set_value("Quando começam as aulas em Mimoso?").run()
            tela.button(key="rf20_consultar").click().run()
        self.assertFalse(tela.exception)

    def _eventos(self, nome):
        if not self.log.is_file():
            return []
        eventos = map(json.loads, self.log.read_text(encoding="utf-8").splitlines())
        return [e for e in eventos if e["evento"] == nome]

    def test_consulta_livre_nao_entra_na_minuta(self):
        # O bug do passo 3: a minuta da Ana Paula trazia a resposta sobre Mimoso.
        tela = self._abrir("consulta")
        self._consultar_mimoso(tela)

        self._analisar(tela)
        texto = _texto(tela)

        self.assertIn("ainda não foram consultadas", texto)
        self.assertNotIn("Mimoso", texto)

    def test_buscar_orientacoes_monta_a_minuta_com_fontes_e_fica_pendente(self):
        tela = self._analisar(self._abrir("ficha"))

        tela.button(key="rf20_buscar_orientacoes").click().run()
        texto = _texto(tela)

        self.assertEqual(len(self.rag.perguntas), 3)
        self.assertIn('**Documentos:** "Quais documentos devo apresentar', texto)
        self.assertIn("→ fundamentada (ACV-01 p. 10)", texto)
        for resposta in RESPOSTAS.values():
            self.assertIn(resposta, texto)
        self.assertIn("Fontes conferíveis", texto)
        self.assertIn("**Estado:** Pendente", texto)
        evento = self._eventos("orientacoes_da_ficha")[0]
        self.assertEqual([c["id_consulta"] for c in evento["consultas"]],
                         ["rag-documentos", "rag-local", "rag-período"])

    def test_assunto_sem_evidencia_vai_para_revisao(self):
        self.rag.sem_evidencia = {"período"}
        tela = self._analisar(self._abrir("ficha"))

        tela.button(key="rf20_buscar_orientacoes").click().run()
        texto = _texto(tela)

        self.assertIn("**Período:** \"Qual o período de matrícula?\" → sem evidência", texto)
        self.assertIn("**Estado:** Revisar", texto)
        self.assertNotIn(RESPOSTAS["período"], texto)

    def test_indice_incompleto_bloqueia_sem_consultar(self):
        mensagem = "O índice está incompleto: ACV-04 não indexado. Para consultar, vá à tela Acervo."
        tela = self._analisar(self._abrir("ficha"))

        with patch("src.acervo_operacao.mensagem_do_indice", return_value=mensagem):
            tela.button(key="rf20_buscar_orientacoes").click().run()

        self.assertEqual(self.rag.perguntas, [])
        self.assertIn(mensagem, "\n".join(item.value for item in tela.error))
        self.assertIn("ainda não foram consultadas", _texto(tela))

    def test_outra_categoria_mostra_aviso_sem_botao(self):
        tela = self._analisar(self._abrir("ficha"), categoria="frequencia_cancelamento")

        self.assertNotIn("rf20_buscar_orientacoes", [botao.key for botao in tela.button])
        self.assertIn(MENSAGEM_ORIENTACOES_SO_MATRICULA, "\n".join(i.value for i in tela.info))

    def test_nova_solicitacao_descarta_as_orientacoes_anteriores(self):
        tela = self._analisar(self._abrir("ficha"))
        tela.button(key="rf20_buscar_orientacoes").click().run()

        self._analisar(tela)
        texto = _texto(tela)

        self.assertIn("ainda não foram consultadas", texto)
        self.assertNotIn(RESPOSTAS["documentos"], texto)

    def test_aprovacao_na_ficha_fica_no_identificador_da_ficha(self):
        tela = self._analisar(self._abrir("ficha"))
        tela.button(key="rf20_buscar_orientacoes").click().run()
        id_ficha = self._eventos("orientacoes_da_ficha")[0]["id_execucao"]
        self._consultar_mimoso(tela)

        tela.sidebar.radio(key="rf20_area").set_value("ficha").run()
        tela.text_input(key="rf20_revisor").input("Ana").run()
        tela.text_input(key="rf20_cargo").input("Secretaria").run()
        tela.button(key="rf20_aprovar").click().run()

        aprovadas = [e for e in self._eventos("decisao") if e["decisao"] == "aprovada"]
        self.assertEqual([e["id_execucao"] for e in aprovadas], [id_ficha])

    def test_outra_categoria_vai_para_revisao_com_o_motivo(self):
        # CASO-07: o aviso diz "vai para revisão", e o estado precisa cumprir.
        tela = self._analisar(self._abrir("ficha"), categoria="frequencia_cancelamento")

        self.assertIn("**Estado:** Revisar", _texto(tela))
        self.assertIn(MOTIVO_SEM_ORIENTACOES, _texto(tela))
        revisoes = [e for e in self._eventos("decisao") if e["decisao"] == "revisar"]
        self.assertIn(MOTIVO_SEM_ORIENTACOES, revisoes[-1]["justificativa"])

    def _ficha_com_orientacoes(self):
        tela = self._analisar(self._abrir("ficha"))
        tela.button(key="rf20_buscar_orientacoes").click().run()
        return tela

    def _assert_ficha_limpa(self, tela, aviso):
        self.assertFalse(tela.exception)
        self.assertEqual([item.value for item in tela.toast], [aviso])
        self.assertEqual(tela.text_area(key="rf20_texto_ficha").value, "")
        texto = _texto(tela)
        self.assertNotIn("**Minuta**", texto)
        self.assertNotIn("Decisão do servidor", texto)
        self.assertNotIn("rf20_buscar_orientacoes", [botao.key for botao in tela.button])

    def test_aprovar_avisa_e_limpa_a_ficha(self):
        tela = self._ficha_com_orientacoes()
        tela.text_input(key="rf20_revisor").input("Ana").run()
        tela.text_input(key="rf20_cargo").input("Secretaria").run()

        tela.button(key="rf20_aprovar").click().run()

        self._assert_ficha_limpa(tela, "Ficha aprovada e registrada.")
        self.assertEqual(tela.session_state["rf20_revisor"], "")
        self.assertEqual(tela.session_state["rf20_cargo"], "")
        self.assertEqual([e["decisao"] for e in self._eventos("decisao")][-1], "aprovada")

    def test_rejeitar_avisa_e_limpa_a_ficha(self):
        tela = self._ficha_com_orientacoes()
        tela.text_area(key="rf20_justificativa").input("Orientação incompleta.").run()

        tela.button(key="rf20_rejeitar").click().run()

        self._assert_ficha_limpa(tela, "Ficha rejeitada e registrada.")
        self.assertEqual([e["decisao"] for e in self._eventos("decisao")][-1], "rejeitada")

    def test_pedir_revisao_mantem_a_ficha_na_tela(self):
        tela = self._ficha_com_orientacoes()
        tela.text_area(key="rf20_justificativa").input("Conferir a lista de documentos.").run()

        tela.button(key="rf20_revisar").click().run()

        self.assertEqual(list(tela.toast), [])
        self.assertIn("**Minuta**", _texto(tela))
        self.assertIn("**Estado:** Revisar", _texto(tela))


class TestRegrasDasOrientacoes(unittest.TestCase):
    def test_aviso_de_espera_so_antes_de_o_modelo_carregar(self):
        texto = "Consultando o acervo..."

        self.assertEqual(aviso_de_espera(texto, False), f"{texto} {AVISO_PRIMEIRA_CONSULTA}")
        self.assertEqual(aviso_de_espera(texto, True), texto)

    def test_outra_categoria_exige_revisao_e_matricula_nao(self):
        outra = {"linhas": {"categoria": "frequencia_cancelamento"}, "estado": "pendente", "motivos": []}
        matricula = {"linhas": {"categoria": "matricula"}, "estado": "pendente", "motivos": []}

        self.assertEqual(exigir_revisao_sem_orientacoes(outra)["estado"], "revisar")
        self.assertEqual(exigir_revisao_sem_orientacoes(outra)["motivos"], [MOTIVO_SEM_ORIENTACOES])
        self.assertEqual(exigir_revisao_sem_orientacoes(matricula), matricula)

    def test_so_busca_para_matricula_com_minuta_liberada(self):
        linhas = {"categoria": "matrícula"}

        self.assertTrue(pode_buscar_orientacoes({"linhas": linhas}))
        self.assertFalse(pode_buscar_orientacoes({"linhas": linhas, "minuta_bloqueada": True}))
        self.assertFalse(pode_buscar_orientacoes({"linhas": {"categoria": "reclamação"}}))
        self.assertFalse(pode_buscar_orientacoes(None))

    def test_resumo_mostra_pergunta_status_e_fontes(self):
        partes = [{
            "assunto": "local", "pergunta": "Onde devo comparecer?",
            "consulta": {"tipo": "conflito", "fontes": [{"doc_id": "ACV-01", "pagina": 10}]},
        }]

        self.assertEqual(
            resumo_das_orientacoes(partes),
            ['**Local:** "Onde devo comparecer?" → conflito (ACV-01 p. 10)'],
        )


class TestModeloCarregadoUmaVez(unittest.TestCase):
    def setUp(self):
        self.criados = 0

        class ModeloFalso:
            max_seq_length = 128

            def encode(self, textos):
                return [[0.0] for _ in textos]

        def criar():
            self.criados += 1
            return ModeloFalso()

        for alvo in (
            patch.object(vector_store, "_MODELO", None),
            patch.object(vector_store, "_criar_modelo", criar),
        ):
            alvo.start()
            self.addCleanup(alvo.stop)

    def test_consultas_seguintes_reaproveitam_o_modelo(self):
        self.assertFalse(vector_store.modelo_carregado())

        primeiro = vector_store.carregar_modelo_embeddings()

        self.assertTrue(vector_store.modelo_carregado())
        segundo = vector_store.carregar_modelo_embeddings()

        self.assertIs(primeiro, segundo)
        self.assertEqual(self.criados, 1)
        self.assertEqual(primeiro.max_seq_length, 128)
        self.assertEqual(primeiro.encode(["a", "b"]), [[0.0], [0.0]])

    def test_duas_consultas_simultaneas_criam_um_modelo_so(self):
        largada = threading.Barrier(2)
        modelos = []

        def carregar():
            largada.wait()
            modelos.append(vector_store.carregar_modelo_embeddings())

        threads = [threading.Thread(target=carregar) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(self.criados, 1)
        self.assertIs(modelos[0], modelos[1])


if __name__ == "__main__":
    unittest.main()
