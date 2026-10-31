import json
import unittest
from unittest.mock import patch

from src import rf19_complemento as rf
from testes.dados_vigencia import TRECHOS

CHUNKS = ("ACV-01-p13-s1-c1", "ACV-04-p2-s1-c1", "ACV-06-p2-s1-c1")

LISTA_ACV01 = {
    "chunk_id": "ACV-01-p13-s1-c1",
    "trecho": "A lista das matrículas efetivadas na 4ª chamada de vagas remanescentes serão",
}
LINHA_ACV04 = {
    "chunk_id": "ACV-04-p2-s1-c1",
    "trecho": "Efetivação das matrículas da 4º chamada das vagas",
}
LINHA_ACV06 = {
    "chunk_id": "ACV-06-p2-s1-c1",
    "trecho": "Divulgação/organização das matrículas efetivadas da 4ª",
}


def _evidencias():
    return [
        {
            "chunk_id": c,
            "texto": TRECHOS[c]["texto"],
            "metadados": TRECHOS[c]["metadados"],
            "distancia": 0.3,
            "similaridade": 0.7,
        }
        for c in CHUNKS
    ]


def _conflito(*citacoes):
    return {
        "status": "conflito",
        "resposta": "",
        "citacoes": list(citacoes),
        "justificativa": "Os documentos divergem.",
    }


def _llm(respostas):
    chamadas = []

    def consultar(instrucoes, entrada, nome_configuracao="principal"):
        chamadas.append(json.loads(entrada))
        indice = min(len(chamadas), len(respostas)) - 1
        return json.dumps(respostas[indice], ensure_ascii=False), {}

    consultar.chamadas = chamadas
    return consultar


class TestConflitoDeclaradoPeloModelo(unittest.TestCase):
    def _rodar(self, respostas):
        llm = _llm(respostas)
        with patch.object(rf, "consultar_llm", llm):
            resultado = rf._gerar_resposta("Quando sai a lista da 4ª chamada?", _evidencias(), None)
        return resultado, llm.chamadas

    def test_conflito_com_linha_substituida_recebe_correcao_e_nao_vale(self):
        resultado, chamadas = self._rodar([_conflito(LISTA_ACV01, LINHA_ACV04)])
        self.assertEqual(len(chamadas), 2)
        self.assertNotIn("correcao_de_vigencia", chamadas[0])
        self.assertIn("correcao_de_vigencia", chamadas[1])
        self.assertEqual(resultado["status"], "conflito")
        self.assertIn("substituído", json.dumps(resultado, ensure_ascii=False))

    def test_conflito_entre_trechos_vigentes_continua_valendo(self):
        resultado, chamadas = self._rodar([_conflito(LISTA_ACV01, LINHA_ACV06)])
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(resultado["status"], "conflito")
        self.assertEqual({f["doc_id"] for f in resultado["fontes"]}, {"ACV-01", "ACV-06"})

    def test_segunda_tentativa_com_par_vigente_e_aceita(self):
        resultado, chamadas = self._rodar([
            _conflito(LISTA_ACV01, LINHA_ACV04),
            _conflito(LISTA_ACV01, LINHA_ACV06),
        ])
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(resultado["status"], "conflito")
        self.assertEqual({f["doc_id"] for f in resultado["fontes"]}, {"ACV-01", "ACV-06"})
        self.assertNotIn("substituído", json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()