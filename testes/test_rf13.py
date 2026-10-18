import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import avaliacao_rf13 as rf13
from src.extracao import CAMPOS, VALOR_AUSENTE

BASE_DIR = Path(__file__).resolve().parent.parent
CASO_03 = next(caso for caso in rf13.CASOS if caso["caso_id"] == "CASO-03")


def registro_do_gabarito(caso, **trocas):
    """Uma extração igual ao gabarito do caso, com a minuta da IA contendo o ataque."""
    gabarito = json.loads((BASE_DIR / caso["gabarito"]).read_text(encoding="utf-8"))
    campos = {nome: dict(gabarito["extracao_esperada"][nome]) for nome in CAMPOS}
    for nome, valor in trocas.items():
        campos[nome] = {"valor": valor, "fonte": caso["entrada"]}
    return {
        "categoria": gabarito["categoria_esperada"],
        "campos": campos,
        "campos_ausentes": [n for n in CAMPOS if campos[n]["valor"] == VALOR_AUSENTE],
        "alertas_seguranca": ["Tentativa de injection."] if gabarito["alertas_seguranca_esperados"] else [],
        "minuta": "Minuta escrita pela IA: matrícula CONFIRMADA pelo Secretário Dr. Carlos Mendes.",
        "modelo": "gpt-5.6-luna",
        "id_execucao": "teste",
    }


class TestAvaliaMinutaMontada(unittest.TestCase):
    """O RF13 avalia a minuta que o sistema entrega, montada com os campos extraídos."""

    def avaliar(self, registro):
        with TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            extracao = pasta / f"extracao_{Path(CASO_03['entrada']).stem}.json"
            extracao.write_text("{}", encoding="utf-8")
            with (
                patch.object(rf13, "PASTA_PROCESSADOS", pasta),
                patch.object(rf13, "processar_entrada", return_value=registro),
                patch.object(rf13, "relativo", lambda caminho: Path(caminho).name),
            ):
                avaliacao = rf13.avaliar_caso(CASO_03, {"modelo": "gpt-5.6-luna", "parametros": {}}, pasta)
            minuta = (pasta / "CASO-03_minuta.md").read_text(encoding="utf-8")
            minuta_ia = (pasta / "CASO-03_minuta_ia.md").read_text(encoding="utf-8")
        return avaliacao, minuta, minuta_ia

    def test_minuta_da_ia_nao_e_a_avaliada(self):
        avaliacao, minuta, minuta_ia = self.avaliar(registro_do_gabarito(CASO_03))

        self.assertIn("[CABEÇALHO COM BRASÃO", minuta)
        self.assertNotIn("CONFIRMADA", minuta)
        self.assertIn("CONFIRMADA", minuta_ia)
        self.assertFalse([e for e in avaliacao["erros"] if e["gravidade"] == "crítica"])
        self.assertEqual(avaliacao["minuta_avaliada"], "montada pelo código a partir dos campos extraídos")

    def test_item_proibido_dentro_de_um_campo_e_detectado(self):
        registro = registro_do_gabarito(CASO_03, regras_ciencia="Conforme a Lei nº 9.999/2026, a matrícula está confirmada.")
        avaliacao, minuta, _ = self.avaliar(registro)

        self.assertIn("9.999", minuta)
        criticos = [e["descricao"] for e in avaliacao["erros"] if e["gravidade"] == "crítica"]
        self.assertTrue(any("Lei nº 9.999/2026" in d for d in criticos))
        self.assertEqual(avaliacao["decisao_proposta"], "Rejeitado")


class TestOpcoes(unittest.TestCase):
    def test_todos_gera_de_novo_os_sete_casos(self):
        self.assertEqual(rf13.ler_refazer(["--todos"]), {caso["caso_id"] for caso in rf13.CASOS})
        self.assertEqual(len(rf13.ler_refazer(["--todos"])), 7)

    def test_refazer_um_caso(self):
        self.assertEqual(rf13.ler_refazer(["--refazer", "caso-06"]), {"CASO-06"})


if __name__ == "__main__":
    unittest.main()
