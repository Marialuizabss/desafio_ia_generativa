import unittest
from pathlib import Path

import pymupdf

from src.extracao import CAMPOS
from src.llm_client import montar_minuta
from src.minuta_pdf import CABECALHO, MARCADOR_BRASAO, gerar_pdf_minuta

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

    def test_cabecalho_institucional_abaixo_do_brasao(self):
        dados = gerar_pdf_minuta(montar_minuta(_valores()), BRASAO)
        with pymupdf.open(stream=dados, filetype="pdf") as documento:
            pagina = documento[0]
            texto = pagina.get_text()
            for linha in CABECALHO:
                self.assertIn(linha, texto)
            topo_cabecalho = pagina.search_for("GOVERNO DE MATO GROSSO")[0].y0
            topo_corpo = pagina.search_for("Prezado(a)")[0].y0
            self.assertLess(topo_cabecalho, topo_corpo)

    def test_rodape_em_todas_as_paginas_com_numero(self):
        longa = montar_minuta(_valores()) + "\n\n" + "\n\n".join(f"Parágrafo {n} " + "texto " * 60 for n in range(25))
        rodape = ["Origem: entrada_audio.mp3 · Protocolo 2026-000142 · Execução 28b62555",
                  "Aprovada por Ana Beatriz (SECITECI) em 18/10/2026 às 16:40"]
        dados = gerar_pdf_minuta(longa, BRASAO, rodape=rodape)
        with pymupdf.open(stream=dados, filetype="pdf") as documento:
            total = documento.page_count
            self.assertGreater(total, 1)
            for numero, pagina in enumerate(documento, start=1):
                texto = pagina.get_text()
                self.assertIn("Origem: entrada_audio.mp3", texto)
                self.assertIn(f"Página {numero} de {total}", texto)
            self.assertNotIn("dados/originais", "\n".join(p.get_text() for p in documento))
            self.assertNotIn("GOVERNO DE MATO GROSSO", documento[1].get_text())

    def test_sem_rodape_continua_funcionando(self):
        texto = _texto(gerar_pdf_minuta(montar_minuta(_valores()), BRASAO))
        self.assertNotIn("Página 1", texto)
