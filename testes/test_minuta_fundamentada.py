import unittest
from pathlib import Path
from unittest.mock import patch

from src import minuta_fundamentada as mf
from src.consulta_acervo import MENSAGEM_SEM_EVIDENCIA, minuta_do_atendimento

FONTE_A = {"doc_id": "DOC-A", "versao": "1.0", "pagina": 2, "chunk_id": "DOC-A-p2-c1"}
FONTE_B = {"doc_id": "DOC-B", "versao": "2.0", "pagina": 1, "chunk_id": "DOC-B-p1-c1"}
LINHAS = {"resumo": "Fulana, aprovada na 1ª chamada para o curso X.", "campos": [("Protocolo", "1")]}


def _resultado(status="fundamentada", resposta="resposta", fontes=None, decisao="responder"):
    return {
        "status": status,
        "resposta": resposta,
        "fontes": [FONTE_A] if fontes is None else fontes,
        "decisao": decisao,
        "justificativa": "",
        "id_consulta": "id-1",
    }


def _responder(por_assunto):
    perguntas = []

    def responder(pergunta, top_k=15, nome_configuracao="principal"):
        perguntas.append(pergunta)
        for palavra, resultado in por_assunto.items():
            if palavra in pergunta:
                if isinstance(resultado, Exception):
                    raise resultado
                return resultado
        raise AssertionError(pergunta)

    responder.perguntas = perguntas
    return responder


def _todas_fundamentadas():
    return _responder({
        "documentos": _resultado(resposta="Levar RG.", fontes=[FONTE_A]),
        "comparecer": _resultado(resposta="Ir à unidade.", fontes=[FONTE_A, FONTE_B]),
        "período": _resultado(resposta="Prazo X.", fontes=[FONTE_B]),
    })


class TestPerguntas(unittest.TestCase):
    def test_tres_assuntos_com_a_chamada_do_resumo(self):
        perguntas = [p for _, p in mf.perguntas_de_matricula(LINHAS)]
        self.assertEqual(len(perguntas), 3)
        self.assertTrue(all("1ª chamada" in p for p in perguntas))

    def test_sem_chamada_no_resumo_nao_inventa(self):
        perguntas = [p for _, p in mf.perguntas_de_matricula({"resumo": "Sem a informação."})]
        self.assertFalse(any("chamada" in p for p in perguntas))


class TestCombinar(unittest.TestCase):
    def test_todas_fundamentadas_junta_respostas_e_remove_fontes_repetidas(self):
        responder = _todas_fundamentadas()
        consulta, _ = mf.consultar_orientacoes(LINHAS, responder=responder)
        self.assertEqual(consulta["tipo"], "fundamentada")
        self.assertEqual(consulta["estado"], "pendente")
        for trecho in ("Levar RG.", "Ir à unidade.", "Prazo X."):
            self.assertIn(trecho, consulta["resposta"])
        self.assertEqual([f["chunk_id"] for f in consulta["fontes"]], ["DOC-A-p2-c1", "DOC-B-p1-c1"])
        self.assertEqual(len(responder.perguntas), 3)

    def test_uma_sem_evidencia_nao_vira_fundamentada(self):
        responder = _responder({
            "documentos": _resultado(resposta="Levar RG."),
            "comparecer": _resultado(status="sem_evidencia", resposta="", fontes=[], decisao="revisar"),
            "período": _resultado(resposta="Prazo X.", fontes=[FONTE_B]),
        })
        consulta, _ = mf.consultar_orientacoes(LINHAS, responder=responder)
        self.assertEqual(consulta["tipo"], "sem_evidencia")
        self.assertEqual(consulta["estado"], "revisar")
        self.assertIn(MENSAGEM_SEM_EVIDENCIA, consulta["texto"])
        self.assertIn("Levar RG.", consulta["texto"])
        self.assertIn("DOC-B", consulta["texto"])

    def test_falha_em_uma_consulta_vai_para_revisao(self):
        responder = _responder({
            "documentos": _resultado(),
            "comparecer": RuntimeError("serviço indisponível"),
            "período": _resultado(),
        })
        consulta, partes = mf.consultar_orientacoes(LINHAS, responder=responder)
        self.assertEqual(consulta["tipo"], "falha")
        self.assertEqual(consulta["estado"], "revisar")
        self.assertEqual(len(partes), 3)

    def test_minuta_traz_orientacoes_e_fontes(self):
        consulta, _ = mf.consultar_orientacoes(LINHAS, responder=_todas_fundamentadas())
        modelo = "Texto\n\n**Orientações**\nPENDENTE\n\n**Ciência das regras de matrícula**\nFim"
        with patch("src.llm_client.montar_minuta", return_value=modelo):
            minuta = minuta_do_atendimento({"linhas": LINHAS}, consulta)
        self.assertTrue(minuta["pronta"])
        self.assertIn("Levar RG.", minuta["texto"])
        self.assertIn("Fontes conferíveis", minuta["texto"])
        self.assertNotIn("PENDENTE", minuta["texto"])


class TestSemRegraDeCaso(unittest.TestCase):
    def test_modulo_nao_cita_documento_nem_data_do_acervo(self):
        texto = Path(mf.__file__).read_text(encoding="utf-8")
        for proibido in ("ACV-", "15 a 19", "06/2026", "Edital"):
            self.assertNotIn(proibido, texto)


if __name__ == "__main__":
    unittest.main()