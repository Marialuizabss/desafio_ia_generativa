"""Solicitações e os seus gabaritos ampliados (RF14, RF15, RF19 e testes T02, T03 e T15).

Testa a referência, não a extração: os seis casos do enunciado e o caso do caminho
feliz têm os campos do Desafio 2 sem perder os do Desafio 1; toda entidade literal e
todo fato essencial estão no texto que o RF15 recebe (já minimizado); e cada
divergência com o acervo ou com o original é verificável.
"""

import json
import re
import unittest
from pathlib import Path

import pymupdf

from src.extracao import CATEGORIAS
from src.privacidade import minimizar_texto
from src.varredura_rf12 import CPF, EMAIL

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_GABARITOS = BASE_DIR / "dados" / "gabaritos"
PASTA_ACERVO = BASE_DIR / "dados" / "acervo"

# Seção 7 do contrato: os seis casos do enunciado e o caminho feliz (CASO-08)
GABARITOS = {
    "CASO-01": "gabarito_caso01.json",
    "CASO-04": "gabarito_entrada_texto.json",
    "CASO-05": "gabarito_entrada_audio.json",
    "CASO-06": "gabarito_entrada_pdf-imagem.json",
    "CASO-02": "gabarito_caso02.json",
    "CASO-07": "gabarito_caso07.json",
    "CASO-08": "gabarito_caso08.json",
}
COMPOSICAO_DO_ENUNCIADO = {"completa": 4, "incompleta": 1, "ambigua": 1}

CAMPOS_DESAFIO_1 = (
    "caso_id", "modalidade", "arquivos_origem", "categoria_esperada", "assunto_esperado",
    "pedido_esperado", "extracao_esperada", "campos_ausentes_esperados",
    "alertas_seguranca_esperados", "minuta_nao_pode_conter", "decisao_esperada",
)
CAMPOS_DESAFIO_2 = (
    "versao_gabarito", "tipo_caso", "acrescimo_ao_minimo", "texto_entrada_rf15",
    "fatos_essenciais", "entidades_esperadas", "resumo_referencia", "justificativa_categoria",
    "estado_esperado", "motivos_estado", "divergencias_com_original",
    "divergencias_acervo_esperadas", "orientacoes_acervo_esperadas",
)
TIPOS_DE_ENTIDADE = ("pessoas", "orgaos", "locais", "datas", "protocolos")
ESTADOS = {"pendente", "revisar"}


def ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().casefold()


def resolver(dados: dict, caminho: str):
    """Valor de um caminho com pontos, como "ocr_esperado.codigo.valor"."""
    for parte in caminho.split("."):
        dados = dados[parte]
    return dados


class _BaseSolicitacoes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gabaritos = {caso: ler_json(PASTA_GABARITOS / nome) for caso, nome in GABARITOS.items()}
        catalogo = ler_json(PASTA_ACERVO / "acervo.json")
        cls.documentos = {doc["doc_id"]: doc for doc in catalogo["documentos"]}

    def texto_rf15(self, gabarito: dict) -> str:
        """O texto que o RF15 recebe: a entrada reaproveitada, depois da minimização."""
        entrada = gabarito["texto_entrada_rf15"]
        caminho = BASE_DIR / entrada["arquivo"]
        texto = ler_json(caminho)[entrada["campo"]] if entrada["campo"] else caminho.read_text(encoding="utf-8")
        return normalizar(minimizar_texto(texto))

    def texto_do_documento(self, doc_id: str, pagina: int | None = None) -> str:
        doc = self.documentos[doc_id]
        if doc["formato"] == "txt":
            return normalizar((PASTA_ACERVO / doc["arquivo"]).read_text(encoding="utf-8"))
        with pymupdf.open(PASTA_ACERVO / doc["arquivo"]) as pdf:
            paginas = [pdf[pagina - 1]] if pagina else list(pdf)
            return normalizar(" ".join(p.get_text() for p in paginas))

    def conferir_referencia(self, referencia: dict):
        self.assertIn(referencia["doc_id"], self.documentos)
        texto = self.texto_do_documento(referencia["doc_id"], referencia.get("pagina"))
        self.assertIn(normalizar(referencia["frase"]), texto)

    def conferir_termos_ausentes(self, termos: list[str]):
        for doc_id in self.documentos:
            texto = self.texto_do_documento(doc_id)
            for termo in termos:
                self.assertNotIn(normalizar(termo), texto, f"{termo} em {doc_id}")


class TestSolicitacoesComposicao(_BaseSolicitacoes):
    """Seção 6: quatro completas, uma incompleta e uma ambígua, com áudio e OCR reaproveitados."""

    def test_seis_do_enunciado_e_o_caminho_feliz(self):
        do_enunciado = [g["tipo_caso"] for g in self.gabaritos.values() if not g["acrescimo_ao_minimo"]]
        self.assertEqual({tipo: do_enunciado.count(tipo) for tipo in COMPOSICAO_DO_ENUNCIADO}, COMPOSICAO_DO_ENUNCIADO)
        self.assertEqual(len(do_enunciado), 6)
        acrescimos = [caso for caso, g in self.gabaritos.items() if g["acrescimo_ao_minimo"]]
        self.assertEqual(acrescimos, ["CASO-08"])

    def test_inclui_audio_e_ocr_reaproveitados(self):
        modalidades = {g["modalidade"] for g in self.gabaritos.values() if not g["acrescimo_ao_minimo"]}
        self.assertTrue({"audio", "imagem"} <= modalidades)

    def test_campos_do_desafio_1_e_do_desafio_2(self):
        for caso, gabarito in self.gabaritos.items():
            with self.subTest(caso=caso):
                self.assertEqual(gabarito["caso_id"], caso)
                self.assertEqual([c for c in CAMPOS_DESAFIO_1 + CAMPOS_DESAFIO_2 if c not in gabarito], [])
                self.assertEqual(gabarito["versao_gabarito"], "2.0")


class TestSolicitacoesCompreensao(_BaseSolicitacoes):
    """RF15: fatos e entidades sustentados pelo texto, resumo curto e categoria documentada."""

    def test_fato_essencial_tem_evidencia_no_texto(self):
        for caso, gabarito in self.gabaritos.items():
            texto = self.texto_rf15(gabarito)
            self.assertTrue(gabarito["fatos_essenciais"], caso)
            for fato in gabarito["fatos_essenciais"]:
                with self.subTest(caso=caso, fato=fato["fato"]):
                    self.assertIn(normalizar(fato["evidencia"]), texto)

    def test_entidade_literal_esta_no_texto_minimizado(self):
        for caso, gabarito in self.gabaritos.items():
            texto = self.texto_rf15(gabarito)
            self.assertEqual(set(gabarito["entidades_esperadas"]), set(TIPOS_DE_ENTIDADE), caso)
            for tipo, entidades in gabarito["entidades_esperadas"].items():
                for entidade in entidades:
                    with self.subTest(caso=caso, tipo=tipo, entidade=entidade["texto"]):
                        self.assertIn(entidade["origem"], {"literal", "inferida"})
                        if entidade["origem"] == "literal":
                            self.assertIn(normalizar(entidade["texto"]), texto)

    def test_nenhuma_entidade_e_dado_pessoal_removido(self):
        for caso, gabarito in self.gabaritos.items():
            for entidades in gabarito["entidades_esperadas"].values():
                for entidade in entidades:
                    with self.subTest(caso=caso, entidade=entidade["texto"]):
                        self.assertIsNone(CPF.search(entidade["texto"]))
                        self.assertIsNone(EMAIL.search(entidade["texto"]))
                        self.assertNotIn("removid", entidade["texto"].casefold())

    def test_resumo_de_referencia_tem_ate_100_palavras(self):
        for caso, gabarito in self.gabaritos.items():
            with self.subTest(caso=caso):
                palavras = len(gabarito["resumo_referencia"].split())
                self.assertTrue(0 < palavras <= 100, f"{palavras} palavras")

    def test_categoria_documentada_e_justificada_na_ambigua(self):
        for caso, gabarito in self.gabaritos.items():
            with self.subTest(caso=caso):
                self.assertIn(gabarito["categoria_esperada"], CATEGORIAS)
                if gabarito["tipo_caso"] == "ambigua":
                    self.assertTrue((gabarito["justificativa_categoria"] or "").strip())


class TestSolicitacoesEstado(_BaseSolicitacoes):
    """RF14, RF19 e seção 4: sem fonte suficiente ou com dado incoerente, o caso vai para revisar."""

    def test_estado_e_motivos(self):
        for caso, gabarito in self.gabaritos.items():
            with self.subTest(caso=caso):
                self.assertIn(gabarito["estado_esperado"], ESTADOS)
                motivos = gabarito["motivos_estado"]
                if gabarito["estado_esperado"] == "revisar":
                    self.assertTrue(motivos)
                    for motivo in motivos:
                        self.assertTrue(motivo["codigo"] and motivo["detalhe"].strip())
                else:
                    self.assertEqual(motivos, [])
                    self.assertEqual(gabarito["divergencias_acervo_esperadas"], [])

    def test_ha_um_caminho_feliz_pendente_e_fundamentado(self):
        pendentes = [g for g in self.gabaritos.values() if g["estado_esperado"] == "pendente"]
        self.assertTrue(pendentes)
        for gabarito in pendentes:
            orientacoes = gabarito["orientacoes_acervo_esperadas"]
            self.assertTrue(orientacoes)
            self.assertTrue(all(o["status"] == "fundamentada" for o in orientacoes))


class TestSolicitacoesFontes(_BaseSolicitacoes):
    """RF19 e T15: divergências e orientações conferidas no acervo e no original."""

    def test_divergencias_com_o_acervo_sao_verificaveis(self):
        for caso, gabarito in self.gabaritos.items():
            texto = self.texto_rf15(gabarito)
            for divergencia in gabarito["divergencias_acervo_esperadas"]:
                with self.subTest(caso=caso, tipo=divergencia["tipo"]):
                    self.assertIn(normalizar(divergencia["na_solicitacao"]), texto)
                    if divergencia["referencia"]:
                        self.conferir_referencia(divergencia["referencia"])
                    else:
                        self.assertTrue(divergencia["termos_ausentes"])
                    self.conferir_termos_ausentes(divergencia["termos_ausentes"])

    def test_orientacoes_do_acervo_sao_verificaveis(self):
        for caso, gabarito in self.gabaritos.items():
            for orientacao in gabarito["orientacoes_acervo_esperadas"]:
                with self.subTest(caso=caso, assunto=orientacao["assunto"]):
                    if orientacao["status"] == "fundamentada":
                        self.conferir_referencia(orientacao["referencia"])
                    else:
                        self.assertEqual(orientacao["status"], "sem_evidencia")
                        self.assertIsNone(orientacao["referencia"])
                    self.conferir_termos_ausentes(orientacao["termos_ausentes"])

    def test_coerencia_do_caminho_feliz_com_o_acervo(self):
        for caso, gabarito in self.gabaritos.items():
            for item in gabarito.get("coerencia_acervo", []):
                with self.subTest(caso=caso, campo=item["campo"]):
                    self.conferir_referencia(item["referencia"])

    def test_divergencias_com_o_original_sao_verificaveis(self):
        # O valor errado está no texto processado; o certo está na referência humana do gabarito
        for caso, gabarito in self.gabaritos.items():
            texto = self.texto_rf15(gabarito)
            for divergencia in gabarito["divergencias_com_original"]:
                with self.subTest(caso=caso, campo=divergencia["campo"]):
                    self.assertIn(normalizar(divergencia["no_texto"]), texto)
                    original = str(resolver(gabarito, divergencia["fonte_original"]))
                    self.assertIn(normalizar(divergencia["no_original"]), normalizar(original))
                    self.assertNotEqual(divergencia["no_texto"], divergencia["no_original"])


if __name__ == "__main__":
    unittest.main()
