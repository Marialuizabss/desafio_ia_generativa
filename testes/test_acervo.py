"""Acervo do Desafio 2: catálogo, arquivos e regras de prevalência (RF17 e RF19).

Testa os dados do acervo, não o RAG: o catálogo dados/acervo/acervo.json precisa
descrever exatamente os arquivos da pasta, e as regras de prevalência precisam
decidir os casos conhecidos com o texto real dos PDFs.
"""

import hashlib
import json
import unittest
from pathlib import Path

import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_ACERVO = BASE_DIR / "dados" / "acervo"
CATALOGO = PASTA_ACERVO / "acervo.json"

# Arquivos da pasta que não são documentos do acervo
# Catálogo e registro de exclusões (RF24): ficam na pasta, mas não são documentos do acervo.
FORA_DO_ACERVO = {"acervo.json", "exclusoes.json", ".gitkeep"}

CAMPOS_DO_DOCUMENTO = (
    "doc_id", "titulo", "arquivo", "versao", "ordem", "origem", "data_documento", "tema",
    "formato", "paginas", "documento_base", "altera", "sha256",
)

# Linhas do cabeçalho dos documentos TXT e o campo do catálogo que cada uma repete
CABECALHO_TXT = {"ID": "doc_id", "Título": "titulo", "Versão": "versao"}

# A origem fica só no catálogo; no texto ela influenciaria o modelo. "oficial" não entra:
# aparece em conteúdo legítimo ("convocação oficial da Justiça Eleitoral")
MARCAS_DE_ORIGEM = ("fictício", "fictícia", "Origem:", "FIC_DEV", "Desafio", "criado pela equipe")


def carregar_catalogo() -> dict:
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def texto_do_pdf(arquivo: str) -> str:
    with pymupdf.open(PASTA_ACERVO / arquivo) as documento:
        return "\n".join(pagina.get_text() for pagina in documento)


class TestAcervoArquivos(unittest.TestCase):
    """RF17: cada documento catalogado existe, com o conteúdo e as páginas registrados."""

    @classmethod
    def setUpClass(cls):
        cls.documentos = carregar_catalogo()["documentos"]

    def test_arquivo_existe_e_hash_confere(self):
        for doc in self.documentos:
            with self.subTest(doc=doc["doc_id"]):
                caminho = PASTA_ACERVO / doc["arquivo"]
                self.assertTrue(caminho.is_file())
                self.assertEqual(hashlib.sha256(caminho.read_bytes()).hexdigest(), doc["sha256"])

    def test_pdf_tem_as_paginas_registradas_e_texto_em_todas(self):
        for doc in self.documentos:
            if doc["formato"] != "pdf":
                continue
            with self.subTest(doc=doc["doc_id"]), pymupdf.open(PASTA_ACERVO / doc["arquivo"]) as pdf:
                self.assertEqual(len(pdf), doc["paginas"])
                # PDF textual: sem texto extraível, a página não entra no índice
                for numero, pagina in enumerate(pdf, start=1):
                    self.assertTrue(pagina.get_text().strip(), f"página {numero} sem texto")

    def test_txt_tem_cabecalho_igual_ao_catalogo(self):
        for doc in self.documentos:
            if doc["formato"] != "txt":
                continue
            with self.subTest(doc=doc["doc_id"]):
                linhas = (PASTA_ACERVO / doc["arquivo"]).read_text(encoding="utf-8").splitlines()
                cabecalho = dict(linha.split(": ", 1) for linha in linhas[:5] if ": " in linha)
                for rotulo, campo in CABECALHO_TXT.items():
                    self.assertEqual(cabecalho.get(rotulo), doc[campo], rotulo)
                self.assertIsNone(doc["paginas"])

    def test_txt_nao_declara_origem(self):
        for doc in self.documentos:
            if doc["formato"] != "txt":
                continue
            texto = (PASTA_ACERVO / doc["arquivo"]).read_text(encoding="utf-8").casefold()
            for marca in MARCAS_DE_ORIGEM:
                with self.subTest(doc=doc["doc_id"], marca=marca):
                    self.assertNotIn(marca.casefold(), texto)

    def test_formato_confere_com_a_extensao(self):
        for doc in self.documentos:
            with self.subTest(doc=doc["doc_id"]):
                self.assertEqual(Path(doc["arquivo"]).suffix.lower(), "." + doc["formato"])

    def test_nenhum_arquivo_da_pasta_fica_fora_do_catalogo(self):
        na_pasta = {p.name for p in PASTA_ACERVO.iterdir() if p.is_file()} - FORA_DO_ACERVO
        self.assertEqual(na_pasta, {doc["arquivo"] for doc in self.documentos})


class TestAcervoCatalogo(unittest.TestCase):
    """RF17 e RF19: campos completos, identificadores únicos e referências válidas."""

    @classmethod
    def setUpClass(cls):
        cls.catalogo = carregar_catalogo()
        cls.documentos = cls.catalogo["documentos"]
        cls.ids = {doc["doc_id"] for doc in cls.documentos}

    def test_cada_documento_tem_todos_os_campos(self):
        for doc in self.documentos:
            with self.subTest(doc=doc.get("doc_id")):
                self.assertEqual([c for c in CAMPOS_DO_DOCUMENTO if c not in doc], [])

    def test_ids_e_ordens_nao_se_repetem(self):
        ids = [doc["doc_id"] for doc in self.documentos]
        # Documento independente do edital não tem ordem de precedência
        ordens = [doc["ordem"] for doc in self.documentos if doc["ordem"] is not None]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ordens), len(set(ordens)))

    def test_origem_e_uma_das_declaradas_no_catalogo(self):
        for doc in self.documentos:
            with self.subTest(doc=doc["doc_id"]):
                self.assertIn(doc["origem"], self.catalogo["origens"])

    def test_alteracoes_apontam_para_documentos_do_catalogo_e_tem_escopo(self):
        for doc in self.documentos:
            if doc["documento_base"] is not None:
                self.assertIn(doc["documento_base"], self.ids)
            for alteracao in doc["altera"]:
                with self.subTest(doc=doc["doc_id"], itens=alteracao.get("itens")):
                    self.assertIn(alteracao["doc_id"], self.ids)
                    self.assertTrue(alteracao["itens"])
                    self.assertTrue(alteracao["escopo"].strip())

    def test_regras_de_prevalencia_r1_a_r4(self):
        regras = self.catalogo["regras_prevalencia"]["regras"]
        self.assertEqual([regra["id"] for regra in regras], ["R1", "R2", "R3", "R4"])
        for regra in regras:
            self.assertTrue(regra["regra"].strip())


class TestAcervoPrevalencia(unittest.TestCase):
    """Seção 6 e T10: as regras do catálogo decidem os casos conhecidos.

    Aplica R1 a R3 aqui só para conferir os dados com o texto dos PDFs; a
    aplicação das regras nas respostas é do RAG (RF19).
    """

    @classmethod
    def setUpClass(cls):
        cls.documentos = {doc["doc_id"]: doc for doc in carregar_catalogo()["documentos"]}

    def _alteram(self, item: str) -> list[str]:
        return [
            doc_id for doc_id, doc in self.documentos.items()
            if any(item in alteracao["itens"] for alteracao in doc["altera"])
        ]

    def _vigente(self, candidatos: list[str]) -> str:
        """R2: entre os documentos que cobrem o mesmo ponto, vale o de maior ordem."""
        return max(candidatos, key=lambda doc_id: self.documentos[doc_id]["ordem"])

    def _texto(self, doc_id: str) -> str:
        return texto_do_pdf(self.documentos[doc_id]["arquivo"])

    def test_quadro_de_vagas_vale_o_retificador_02(self):
        candidatos = self._alteram("3.11")
        self.assertEqual(sorted(candidatos), ["ACV-02", "ACV-03"])
        self.assertEqual(self._vigente(candidatos), "ACV-03")

    def test_inicio_das_aulas_de_curso_listado_no_retificador_06(self):
        # Agropecuária em Mimoso (ETEC Cuiabá) está no item 1.1 do ACV-07 (R1)
        texto = self._texto("ACV-07")
        self.assertRegex(texto, r"Cuiabá\s*\n\s*Agropecuária\s*\n\s*Mimoso")
        self.assertEqual(self._vigente(self._alteram("5")), "ACV-07")
        self.assertIn("05 de outubro de 2026", texto)

    def test_inicio_das_aulas_de_curso_fora_do_retificador_06(self):
        # Enfermagem em Cuiabá não está no item 1.1 do ACV-07: fora do escopo,
        # vale o cronograma anterior de maior ordem (R3)
        self.assertNotRegex(self._texto("ACV-07"), r"Cuiabá\s*\n\s*Enfermagem")
        self.assertIn("somente dos cursos listados", self.documentos["ACV-07"]["altera"][0]["escopo"])
        candidatos = [doc_id for doc_id in self._alteram("5") if doc_id != "ACV-07"]
        self.assertEqual(self._vigente(candidatos), "ACV-06")
        self.assertRegex(self._texto("ACV-06"), r"Início das aulas\s*\n\s*21/07/2026")


if __name__ == "__main__":
    unittest.main()
