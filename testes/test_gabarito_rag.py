"""Perguntas de avaliação do RAG e o seu gabarito (RF18, RF19 e RF23).

Testa a referência, não o RAG: as 8 perguntas têm a composição do enunciado, cada
frase de referência existe na página indicada do acervo e o esperado de cada
pergunta é coerente com o seu tipo. Frases são comparadas com espaços e quebras de
linha normalizados, porque a extração do PDF quebra linhas no meio das frases.
"""

import json
import re
import unittest
from pathlib import Path

import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_ACERVO = BASE_DIR / "dados" / "acervo"
PERGUNTAS = BASE_DIR / "dados" / "originais" / "perguntas_rag.json"
GABARITO = BASE_DIR / "dados" / "gabaritos" / "gabarito_rag.json"

# Composição exigida na seção 6 do enunciado
COMPOSICAO = {"respondivel": 5, "sem_resposta": 2, "contraditoria": 1}

# Status e decisão esperados para cada tipo de pergunta (RF19)
ESPERADO_POR_TIPO = {
    "respondivel": ("fundamentada", "aprovada"),
    "sem_resposta": ("sem_evidencia", "revisar"),
    "contraditoria": ("conflito", "revisar"),
}


def ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def alternativas(elemento) -> list[str]:
    """Um elemento esperado é um texto ou uma lista de textos equivalentes."""
    return elemento if isinstance(elemento, list) else [elemento]


class _BaseGabaritoRag(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.perguntas = ler_json(PERGUNTAS)["perguntas"]
        cls.itens = ler_json(GABARITO)["itens"]
        catalogo = ler_json(PASTA_ACERVO / "acervo.json")
        cls.documentos = {doc["doc_id"]: doc for doc in catalogo["documentos"]}
        cls.regras = {regra["id"] for regra in catalogo["regras_prevalencia"]["regras"]}
        cls._paginas = {}

    def pagina(self, doc_id: str, numero: int) -> str:
        chave = (doc_id, numero)
        if chave not in self._paginas:
            with pymupdf.open(PASTA_ACERVO / self.documentos[doc_id]["arquivo"]) as pdf:
                self._paginas[chave] = normalizar(pdf[numero - 1].get_text())
        return self._paginas[chave]

    def texto_completo(self, doc_id: str) -> str:
        doc = self.documentos[doc_id]
        if doc["formato"] == "txt":
            return normalizar((PASTA_ACERVO / doc["arquivo"]).read_text(encoding="utf-8"))
        return " ".join(self.pagina(doc_id, numero) for numero in range(1, doc["paginas"] + 1))


class TestGabaritoRagComposicao(_BaseGabaritoRag):
    """Seção 6: oito perguntas, cinco respondíveis, duas sem resposta e uma contraditória."""

    def test_entrada_e_gabarito_tem_as_mesmas_oito_perguntas(self):
        ids_entrada = [pergunta["id"] for pergunta in self.perguntas]
        ids_gabarito = [item["id"] for item in self.itens]
        self.assertEqual(len(ids_entrada), 8)
        self.assertEqual(len(set(ids_entrada)), 8)
        self.assertEqual(ids_entrada, ids_gabarito)

    def test_composicao_cinco_duas_uma(self):
        tipos = [item["tipo"] for item in self.itens]
        self.assertEqual({tipo: tipos.count(tipo) for tipo in COMPOSICAO}, COMPOSICAO)
        self.assertEqual(len(tipos), sum(COMPOSICAO.values()))

    def test_entrada_nao_contem_a_resposta(self):
        textos = {pergunta["id"]: pergunta["pergunta"].casefold() for pergunta in self.perguntas}
        for item in self.itens:
            pergunta = textos[item["id"]]
            esperados = [ref["frase"] for ref in item["referencias"]]
            esperados += [alt for el in item["elementos_esperados"] for alt in alternativas(el)]
            for esperado in esperados:
                with self.subTest(pergunta=item["id"], esperado=esperado):
                    self.assertNotIn(esperado.casefold(), pergunta)
        for pergunta in self.perguntas:
            self.assertEqual(set(pergunta), {"id", "pergunta"})


class TestGabaritoRagCoerencia(_BaseGabaritoRag):
    """RF19: status, decisão, referências e regra de prevalência coerentes com o tipo."""

    def test_status_e_decisao_seguem_o_tipo(self):
        for item in self.itens:
            with self.subTest(pergunta=item["id"]):
                status, decisao = ESPERADO_POR_TIPO[item["tipo"]]
                self.assertEqual(item["status_esperado"], status)
                self.assertEqual(item["decisao_esperada"], decisao)

    def test_sem_resposta_nao_tem_referencia_nem_elemento_esperado(self):
        for item in self.itens:
            if item["tipo"] != "sem_resposta":
                continue
            with self.subTest(pergunta=item["id"]):
                self.assertEqual(item["referencias"], [])
                self.assertEqual(item["elementos_esperados"], [])

    def test_respondivel_tem_referencia_e_elemento_esperado(self):
        for item in self.itens:
            if item["tipo"] != "respondivel":
                continue
            with self.subTest(pergunta=item["id"]):
                self.assertTrue(item["referencias"])
                self.assertTrue(item["elementos_esperados"])

    def test_contraditoria_cita_dois_documentos_e_usa_r4(self):
        for item in self.itens:
            if item["tipo"] != "contraditoria":
                continue
            with self.subTest(pergunta=item["id"]):
                self.assertGreaterEqual(len({ref["doc_id"] for ref in item["referencias"]}), 2)
                self.assertEqual(item["regra_aplicada"], "R4")

    def test_regra_aplicada_existe_no_catalogo(self):
        for item in self.itens:
            if item["regra_aplicada"] is not None:
                with self.subTest(pergunta=item["id"]):
                    self.assertIn(item["regra_aplicada"], self.regras)

    def test_justificativa_quando_nao_e_resposta_direta(self):
        for item in self.itens:
            if item["tipo"] != "respondivel" or item["regra_aplicada"]:
                with self.subTest(pergunta=item["id"]):
                    self.assertTrue((item["justificativa"] or "").strip())


class TestGabaritoRagFontes(_BaseGabaritoRag):
    """RF18 e RF19: cada referência e distrator é verificável no texto do acervo."""

    def _conferir_trechos(self, campo: str):
        for item in self.itens:
            for trecho in item[campo]:
                with self.subTest(pergunta=item["id"], doc=trecho["doc_id"], pagina=trecho["pagina"]):
                    self.assertIn(trecho["doc_id"], self.documentos)
                    self.assertLessEqual(trecho["pagina"], self.documentos[trecho["doc_id"]]["paginas"])
                    self.assertIn(normalizar(trecho["frase"]), self.pagina(trecho["doc_id"], trecho["pagina"]))

    def test_frase_de_referencia_esta_na_pagina_indicada(self):
        self._conferir_trechos("referencias")

    def test_distrator_esta_na_pagina_indicada(self):
        self._conferir_trechos("distratores")

    def test_elementos_esperados_estao_nas_referencias(self):
        for item in self.itens:
            fontes = " ".join(
                self.pagina(ref["doc_id"], ref["pagina"]) for ref in item["referencias"]
            ).casefold()
            for elemento in item["elementos_esperados"]:
                with self.subTest(pergunta=item["id"], elemento=elemento):
                    self.assertTrue(any(alt.casefold() in fontes for alt in alternativas(elemento)))

    def test_sem_resposta_continua_sem_resposta_no_acervo(self):
        # Um documento novo que trate do assunto faria a pergunta deixar de ser "sem resposta"
        for item in self.itens:
            if item["tipo"] != "sem_resposta":
                continue
            self.assertTrue(item.get("termos_ausentes_no_acervo"), item["id"])
            for doc_id in self.documentos:
                texto = self.texto_completo(doc_id).casefold()
                for termo in item["termos_ausentes_no_acervo"]:
                    with self.subTest(pergunta=item["id"], doc=doc_id, termo=termo):
                        self.assertNotIn(termo.casefold(), texto)

    def test_valor_proibido_nao_e_um_elemento_esperado(self):
        for item in self.itens:
            esperados = {alt.casefold() for el in item["elementos_esperados"] for alt in alternativas(el)}
            for proibido in item["nao_pode_conter"]:
                with self.subTest(pergunta=item["id"], proibido=proibido):
                    self.assertNotIn(proibido.casefold(), esperados)


if __name__ == "__main__":
    unittest.main()
