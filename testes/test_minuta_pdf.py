import unittest
from pathlib import Path

import pymupdf

from src.extracao import CAMPOS
from src.llm_client import montar_minuta
from src.minuta_pdf import MARCADOR_BRASAO, gerar_pdf_minuta

BRASAO = Path(__file__).resolve().parent.parent / "dados" / "originais" / "brasao.png"


def _valores():
    return {nome: f"valor-{nome}" for nome in CAMPOS}


def _texto(dados: bytes) -> str:
    with pymupdf.open(stream=dados, filetype="pdf") as documento:
        return "\n".join(pagina.get_text() for pagina in documento)


def _imagens(dados: bytes) -> int:
    with pymupdf.open(stream=dados, filetype="pdf") as documento:
        return sum(len(pagina.get_images()) for pagina in documento)


class TestPdfDaMinuta(unittest.TestCase):
    def test_pdf_traz_brasao_e_os_campos_preenchidos(self):
        minuta = montar_minuta(_valores())
        dados = gerar_pdf_minuta(minuta, BRASAO)

        self.assertTrue(dados.startswith(b"%PDF"))
        self.assertGreater(_imagens(dados), 0)
        texto = _texto(dados)
        self.assertIn("valor-solicitante", texto)
        self.assertIn("valor-protocolo", texto)
        self.assertIn("valor-curso", texto)
        self.assertIn("valor-regras_ciencia", texto)
        self.assertIn("Recebemos sua solicitação", texto)
        self.assertIn("Dados informados na solicitação", texto)
        self.assertIn("[NOME DO SERVIDOR RESPONSÁVEL]", texto)
        self.assertIn("[CARGO / SETOR]", texto)
        self.assertNotIn("CABEÇALHO COM BRASÃO", texto)
        self.assertNotIn(MARCADOR_BRASAO, texto)

    def test_sem_arquivo_de_brasao_ainda_traz_o_texto(self):
        dados = gerar_pdf_minuta(
            f"{MARCADOR_BRASAO}\n\nPrezado(a) Ana,\n\nTexto da minuta.",
            Path("/tmp/brasao-inexistente.png"),
        )

        self.assertEqual(_imagens(dados), 0)
        self.assertIn("Prezado(a) Ana,", _texto(dados))
        self.assertIn("Texto da minuta.", _texto(dados))

    def test_texto_longo_continua_na_pagina_seguinte(self):
        regras = "\n\n".join(
            f"Parágrafo {indice}: ciência da regra de permanência no curso."
            for indice in range(1, 25)
        )
        minuta = (
            f"{MARCADOR_BRASAO}\n\n"
            "Prezado(a) Ana,\n\n"
            "**Ciência das regras de matrícula**\n"
            f"{regras}\n"
        )
        dados = gerar_pdf_minuta(minuta, BRASAO)

        with pymupdf.open(stream=dados, filetype="pdf") as documento:
            self.assertGreater(documento.page_count, 1)
            self.assertGreater(len(documento[0].get_images()), 0)
            self.assertEqual(len(documento[1].get_images()), 0)
        self.assertIn("ciência da regra de permanência", _texto(dados))
