import unittest

from src.rf19_complemento import _mesmo_assunto, _ordinais


def _fontes(*trechos):
    return [{"trecho_citado": t} for t in trechos]


class TestMesmoFato(unittest.TestCase):
    def test_ordinais_do_trecho(self):
        self.assertEqual(_ordinais("14. Período de Matrícula - 1ª Chamada 15 a 19/06/2026"), {"1"})
        self.assertEqual(_ordinais("4ª e 5ª chamadas"), {"4", "5"})
        self.assertEqual(_ordinais("Edital Nº 03, item 11.3.1"), set())

    def test_linhas_de_chamadas_diferentes_nao_sao_o_mesmo_fato(self):
        fontes = _fontes(
            "14. Período de Matrícula - 1ª Chamada 15 a 19/06/2026",
            "20 Efetivação das matrículas da 4ª chamada das vagas remanescentes 03/07/2026 a 08/07/2026",
        )
        self.assertFalse(_mesmo_assunto(fontes))

    def test_mesma_chamada_com_valores_diferentes_continua_sendo_o_mesmo_fato(self):
        fontes = _fontes(
            "Período de Matrícula - 1ª Chamada 15 a 19/06/2026",
            "Período de Matrícula - 1ª Chamada 22 a 26/06/2026",
        )
        self.assertTrue(_mesmo_assunto(fontes))

    def test_sem_ordinal_vale_so_a_sobreposicao_de_palavras(self):
        iguais = _fontes(
            "O prazo para entregar a documentação da matrícula é de cinco dias",
            "O prazo para entregar a documentação da matrícula é de dez dias",
        )
        diferentes = _fontes(
            "O prazo para entregar a documentação da matrícula é de cinco dias",
            "Uniforme obrigatório nas aulas práticas dos laboratórios",
        )
        self.assertTrue(_mesmo_assunto(iguais))
        self.assertFalse(_mesmo_assunto(diferentes))

    def test_ordinal_so_de_um_lado_nao_bloqueia(self):
        fontes = _fontes(
            "Período de Matrícula - 1ª Chamada 15 a 19/06/2026",
            "Período de Matrícula conforme o cronograma 22 a 26/06/2026",
        )
        self.assertTrue(_mesmo_assunto(fontes))


if __name__ == "__main__":
    unittest.main()