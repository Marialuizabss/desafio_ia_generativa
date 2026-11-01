"""T15: a regressão encaminha à revisão e não grava decisão humana."""

import json
import unittest
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src import audit, regressao_t15


def _analise_vazia(_texto, _origem, chamar=None):
    return SimpleNamespace(validacao=None, guardrail=None)


class TestRegressaoT15(unittest.TestCase):
    def test_caso_05_declara_o_turno_repetido(self):
        texto = (regressao_t15.BASE_DIR / regressao_t15.CASOS[1]["origem"]).read_text(encoding="utf-8")
        minuta = "Turno: noturno noturno\nInício do curso: não localizado\n"
        pendencias = regressao_t15.pendencias_do_caso("CASO-05", texto, minuta)
        self.assertEqual(len(pendencias), 1)
        self.assertIn("noturno noturno", pendencias[0])
        self.assertIn("não localizado", pendencias[0])
        self.assertIn("revisão humana ainda não foi feita", pendencias[0])
        self.assertEqual(regressao_t15.pendencias_do_caso("CASO-04", texto, minuta), [])

    def test_execucao_nao_registra_decisao_humana(self):
        with TemporaryDirectory() as pasta, patch.object(
            regressao_t15, "PASTA_SAIDA", regressao_t15.Path(pasta)
        ), patch.object(
            regressao_t15, "analisar_solicitacao", side_effect=_analise_vazia
        ), patch.object(
            regressao_t15, "registrar_execucao", return_value="id-teste"
        ), patch.object(audit, "registrar_decisao") as decisao:
            destino = regressao_t15.executar()
            decisao.assert_not_called()
            caso_04 = json.loads((destino / "CASO-04.json").read_text(encoding="utf-8"))
            caso_05 = json.loads((destino / "CASO-05.json").read_text(encoding="utf-8"))
            resumo = json.loads((destino / "resumo.json").read_text(encoding="utf-8"))

        self.assertIsNone(caso_04["decisao_humana"])
        self.assertEqual(caso_04["pendencias"], [])
        self.assertIsNone(caso_05["decisao_humana"])
        self.assertIn("noturno noturno", caso_05["pendencias"][0])
        self.assertIsNone(resumo["decisao_humana"])
        self.assertNotIn("revisor", json.dumps(resumo, ensure_ascii=False))
        self.assertNotIn("Felipe", json.dumps(caso_05, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
