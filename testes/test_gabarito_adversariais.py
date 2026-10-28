"""Entradas adversariais e o seu gabarito (RF16 e teste T04).

Testa a referência, não os guardrails: há um ataque de cada tipo pedido no
enunciado (na solicitação, no acervo e tentativa de obter segredo), o trecho
malicioso está mesmo na entrada, e nenhuma entrada carrega credencial de verdade.
"""

import json
import re
import unittest
from pathlib import Path

from src.varredura_rf12 import CHAVE, credenciais_da_linha

BASE_DIR = Path(__file__).resolve().parent.parent
GABARITO = BASE_DIR / "dados" / "gabaritos" / "gabarito_adversariais.json"
CATALOGO = BASE_DIR / "dados" / "acervo" / "acervo.json"
PERGUNTAS_RAG = BASE_DIR / "dados" / "originais" / "perguntas_rag.json"

TIPOS = {"solicitacao", "acervo", "segredo"}
DECISOES = {"bloquear", "revisar"}

# Palavras que revelariam ao sistema que o documento é um ataque
MARCAS_DE_ATAQUE = ("advers", "ataque", "malicios", "injection", "ADV-")


def ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


class TestGabaritoAdversariais(unittest.TestCase):
    """Seção 6 e RF16: três ataques, um de cada tipo, verificáveis nas entradas."""

    @classmethod
    def setUpClass(cls):
        cls.gabarito = ler_json(GABARITO)
        cls.ataques = cls.gabarito["ataques"]
        cls.documentos = {doc["doc_id"]: doc for doc in ler_json(CATALOGO)["documentos"]}

    def _entradas(self):
        """Cada entrada do gabarito, inclusive as variantes, com o seu trecho malicioso."""
        for ataque in self.ataques:
            yield ataque["id"], ataque["entrada"], ataque["trecho_malicioso"]
            for variante in ataque["variantes"]:
                yield ataque["id"], variante["entrada"], variante["trecho_malicioso"]

    def test_tres_ataques_um_de_cada_tipo(self):
        self.assertEqual([ataque["id"] for ataque in self.ataques], ["ADV-01", "ADV-02", "ADV-03"])
        self.assertEqual({ataque["tipo"] for ataque in self.ataques}, TIPOS)

    def test_entrada_existe_e_contem_o_trecho_malicioso(self):
        for id_ataque, entrada, trecho in self._entradas():
            with self.subTest(ataque=id_ataque, entrada=entrada):
                texto = (BASE_DIR / entrada).read_text(encoding="utf-8")
                self.assertIn(normalizar(trecho), normalizar(texto))

    def test_decisao_alerta_e_proibicoes(self):
        self.assertEqual(len(self.gabarito["nao_pode_fazer_em_todos"]), 3)
        for ataque in self.ataques:
            with self.subTest(ataque=ataque["id"]):
                self.assertIn(ataque["decisao_esperada"], DECISOES)
                self.assertTrue(ataque["alerta_esperado"])
                self.assertTrue(ataque["nao_pode_conter"])
                self.assertTrue(ataque["motivo"].strip())

    def test_tentativa_de_segredo_e_bloqueada(self):
        segredo = next(ataque for ataque in self.ataques if ataque["tipo"] == "segredo")
        self.assertEqual(segredo["decisao_esperada"], "bloquear")

    def test_ataque_no_acervo_esta_catalogado_e_tem_consulta_propria(self):
        ataque = next(ataque for ataque in self.ataques if ataque["tipo"] == "acervo")
        doc = self.documentos[ataque["doc_id"]]
        self.assertEqual(Path(ataque["entrada"]).name, doc["arquivo"])
        self.assertTrue(ataque["consulta_gatilho"].strip())
        # A consulta do ataque não é uma das 8 perguntas, para não mudar o gabarito do RAG
        perguntas = {p["pergunta"] for p in ler_json(PERGUNTAS_RAG)["perguntas"]}
        self.assertNotIn(ataque["consulta_gatilho"], perguntas)

    def test_documento_do_ataque_nao_se_denuncia(self):
        # Catálogo e texto podem ir para o índice: não podem avisar que é um ataque
        ataque = next(ataque for ataque in self.ataques if ataque["tipo"] == "acervo")
        doc = self.documentos[ataque["doc_id"]]
        visivel = json.dumps(doc, ensure_ascii=False) + (BASE_DIR / ataque["entrada"]).read_text(encoding="utf-8")
        for marca in MARCAS_DE_ATAQUE:
            with self.subTest(marca=marca):
                self.assertNotIn(marca.casefold(), visivel.casefold())

    def test_nenhuma_entrada_tem_credencial_real(self):
        for id_ataque, entrada, _ in self._entradas():
            texto = (BASE_DIR / entrada).read_text(encoding="utf-8")
            with self.subTest(ataque=id_ataque, entrada=entrada):
                self.assertIsNone(CHAVE.search(texto))
                self.assertEqual([v for linha in texto.splitlines() for v in credenciais_da_linha(linha)], [])


if __name__ == "__main__":
    unittest.main()
