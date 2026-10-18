import unittest

from src.interface import MARCADOR_BRASAO, preparar_minuta

MINUTA = (
    f"{MARCADOR_BRASAO}\n\n"
    "Prezado(a) Marcos Vinícius de Almeida Santos,\n\n"
    "**Ciência das regras de matrícula**\n"
    "O(a) solicitante declarou estar ciente de que a matrícula será cancelada."
)


class TestExibicaoDaMinuta(unittest.TestCase):

    def test_marcador_do_brasao_e_separado_do_texto(self):
        com_brasao, texto = preparar_minuta(MINUTA)

        self.assertTrue(com_brasao)
        self.assertNotIn("CABEÇALHO COM BRASÃO", texto)
        self.assertTrue(texto.startswith("Prezado(a)"))

    def test_minuta_sem_marcador_nao_mostra_brasao(self):
        com_brasao, texto = preparar_minuta("Prezado(a) Fulano,\n\nTexto.")

        self.assertFalse(com_brasao)
        self.assertTrue(texto.startswith("Prezado(a) Fulano,"))

    def test_titulo_e_texto_ficam_em_linhas_separadas(self):
        _, texto = preparar_minuta(MINUTA)

        self.assertIn("**Ciência das regras de matrícula**  \nO(a) solicitante", texto)

    def test_conteudo_da_minuta_nao_e_alterado(self):
        _, texto = preparar_minuta(MINUTA)

        self.assertEqual(texto.replace("  \n", "\n"), MINUTA.removeprefix(MARCADOR_BRASAO).lstrip())


if __name__ == "__main__":
    unittest.main()
