"""RF14: contrato da solicitação, validação em três camadas e no máximo uma correção.

Sem chamar a API: as saídas do modelo são escritas aqui ou montadas a partir dos
gabaritos (CASO-05, CASO-06 e CASO-08).
"""

import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from src import schemas
from src.extracao import CAMPOS, FONTE_AUSENTE, VALOR_AUSENTE
from src.privacidade import minimizar_texto

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_GABARITOS = BASE_DIR / "dados" / "gabaritos"
HOJE = date(2026, 10, 28)
DATA_MINIMA = date(2026, 3, 31)


def gabarito(nome: str) -> dict:
    return json.loads((PASTA_GABARITOS / nome).read_text(encoding="utf-8"))


def texto_do_caso(dados: dict) -> str:
    entrada = dados["texto_entrada_rf15"]
    caminho = BASE_DIR / entrada["arquivo"]
    texto = json.loads(caminho.read_text(encoding="utf-8"))[entrada["campo"]] if entrada["campo"] else caminho.read_text(encoding="utf-8")
    return minimizar_texto(texto)


class _BaseRF14(unittest.TestCase):

    def setUp(self):
        self.caso08 = gabarito("gabarito_caso08.json")
        self.texto08 = texto_do_caso(self.caso08)
        self.esperado08 = schemas.esperado_do_gabarito(self.caso08)

    def com(self, **mudancas) -> dict:
        dados = json.loads(json.dumps(self.esperado08))
        dados.update(mudancas)
        return dados

    def categorias_da_estrutura(self, dados) -> list[str]:
        bruto = dados if isinstance(dados, str) else json.dumps(dados)
        _, erros = schemas.validar_estrutura(bruto)
        return [erro.categoria for erro in erros]

    def categorias_das_regras(self, dados: dict, texto: str | None = None) -> list[str]:
        solicitacao, erros = schemas.validar_estrutura(json.dumps(dados))
        self.assertEqual(erros, [])
        regras = schemas.validar_regras(solicitacao, texto or self.texto08, DATA_MINIMA, HOJE)
        return [erro.categoria for erro in regras]


class TestRF14Esquema(_BaseRF14):
    """Camadas 1 e 2: JSON e contrato, com cada defeito na sua categoria (T01)."""

    def test_extracao_correta_passa_nas_tres_camadas(self):
        self.assertEqual(self.categorias_da_estrutura(self.esperado08), [])
        self.assertEqual(self.categorias_das_regras(self.esperado08), [])

    def test_cada_defeito_tem_a_sua_categoria(self):
        sem_categoria = {k: v for k, v in self.esperado08.items() if k != "categoria"}
        entidade_errada = self.com(entidades={**self.esperado08["entidades"],
                                              "pessoas": [{"texto": "Ana", "origem": "deduzida"}]})
        casos = {
            "chave_extra": self.com(prioridade="alta"),
            "tipo_incorreto": self.com(requer_revisao="não"),
            "campo_obrigatorio_ausente": sem_categoria,
            "valor_fora_do_dominio": self.com(categoria="transferencia"),
            "json_invalido": json.dumps(self.esperado08)[:-40],
        }
        for categoria, dados in casos.items():
            with self.subTest(categoria=categoria):
                self.assertEqual(self.categorias_da_estrutura(dados), [categoria])
        self.assertEqual(self.categorias_da_estrutura(entidade_errada), ["valor_fora_do_dominio"])

    def test_tipo_nao_e_convertido(self):
        # Modo estrito: número não vira texto e texto não vira booleano
        self.assertEqual(self.categorias_da_estrutura(self.com(protocolo=2026000201)), ["tipo_incorreto"])
        self.assertEqual(self.categorias_da_estrutura(self.com(requer_revisao="true")), ["tipo_incorreto"])

    def test_versao_do_esquema_e_conferida(self):
        self.assertEqual(self.categorias_da_estrutura(self.com(versao_esquema="1.0")), ["valor_fora_do_dominio"])

    def test_ausencia_e_null(self):
        dados = self.com(protocolo=None, campos_ausentes=["protocolo"])
        self.assertEqual(self.categorias_da_estrutura(dados), [])
        self.assertEqual(self.categorias_das_regras(dados), [])

    def test_esquema_da_saida_restrita_e_estrito(self):
        esquema = schemas.esquema_saida_restrita()
        texto = json.dumps(esquema)
        self.assertNotIn('"title"', texto)
        self.assertNotIn('"const"', texto)

        def objetos(no):
            if isinstance(no, dict):
                if no.get("type") == "object":
                    yield no
                for valor in no.values():
                    yield from objetos(valor)
            elif isinstance(no, list):
                for valor in no:
                    yield from objetos(valor)

        encontrados = list(objetos(esquema))
        self.assertEqual(len(encontrados), 4)
        for objeto in encontrados:
            self.assertIs(objeto["additionalProperties"], False)
            self.assertEqual(set(objeto["required"]), set(objeto["properties"]))


class TestRF14Regras(_BaseRF14):
    """Camada 3: datas, presença no texto original e coerência (T02)."""

    def test_data_impossivel(self):
        for valor in ("31/02/2026", "2026-06-12"):
            with self.subTest(valor=valor):
                self.assertIn("data_impossivel", self.categorias_das_regras(self.com(data_solicitacao=valor)))

    def test_dado_que_nao_esta_no_original(self):
        casos = {
            "data_solicitacao": self.com(data_solicitacao="13/06/2026"),
            "protocolo": self.com(protocolo="2026-000999"),
            "solicitante": self.com(solicitante="Ana Paula Ribeiro Souza"),
        }
        for campo, dados in casos.items():
            with self.subTest(campo=campo):
                self.assertEqual(self.categorias_das_regras(dados), ["dado_nao_presente_no_original"])

    def test_data_anterior_ao_processo_seletivo_no_caso06(self):
        # O que o modelo extrai lendo o OCR: código 2024-000142 e data 17/01/2026
        caso06 = gabarito("gabarito_entrada_pdf-imagem.json")
        dados = schemas.esperado_do_gabarito(caso06)
        dados.update(protocolo="2024-000142", data_solicitacao="17/01/2026")
        self.assertEqual(self.categorias_das_regras(dados, texto_do_caso(caso06)), ["data_incoerente"])

    def test_corrigir_por_suposicao_tambem_e_detectado_no_caso06(self):
        # Os valores certos (leitura humana) não estão no texto do OCR: não podem ser "completados"
        caso06 = gabarito("gabarito_entrada_pdf-imagem.json")
        categorias = self.categorias_das_regras(schemas.esperado_do_gabarito(caso06), texto_do_caso(caso06))
        self.assertEqual(categorias, ["dado_nao_presente_no_original", "dado_nao_presente_no_original"])

    def test_data_no_futuro_e_inicio_antes_da_solicitacao(self):
        self.assertIn("data_incoerente", self.categorias_das_regras(self.com(data_solicitacao="12/06/2027")))
        # As duas datas estão no texto, mas trocadas: o curso começaria antes da solicitação
        trocadas = self.com(data_solicitacao="21/07/2026",
                            dados_curso={**self.esperado08["dados_curso"], "data_inicio": "12/06/2026"})
        self.assertEqual(self.categorias_das_regras(trocadas), ["data_incoerente"])

    def test_data_por_extenso_da_transcricao_e_reconhecida(self):
        caso05 = gabarito("gabarito_entrada_audio.json")
        self.assertEqual(self.categorias_das_regras(schemas.esperado_do_gabarito(caso05), texto_do_caso(caso05)), [])

    def test_entidade_literal_precisa_estar_no_texto(self):
        pessoas = [{"texto": "Ana Paula Ribeiro Lopes", "origem": "literal"},
                   {"texto": "Pedro Henrique Silva", "origem": "literal"},
                   {"texto": "Secretaria da ETEC", "origem": "inferida"}]
        dados = self.com(entidades={**self.esperado08["entidades"], "pessoas": pessoas})
        self.assertEqual(self.categorias_das_regras(dados), ["fato_sem_suporte"])

    def test_campos_ausentes_coerentes_com_os_nulos(self):
        self.assertEqual(self.categorias_das_regras(self.com(campos_ausentes=["protocolo"])), ["incoerencia_interna"])

    def test_resumo_com_mais_de_100_palavras(self):
        self.assertEqual(self.categorias_das_regras(self.com(resumo="palavra " * 101)), ["resumo_longo"])

    def test_comparacao_ignora_acento_e_maiusculas(self):
        texto = self.texto08.replace("Ana Paula Ribeiro Lopes", "ANA PAULA RIBEIRO LOPES")
        self.assertEqual(self.categorias_das_regras(self.com(solicitante="Ana Páula Ribeiro Lopes"), texto), [])


class TestRF14Correcao(_BaseRF14):
    """No máximo uma nova tentativa; regra violada vai para revisão sem nova tentativa."""

    def gerador(self, *saidas):
        chamadas = []

        def gerar(erros):
            chamadas.append(erros)
            saida = saidas[len(chamadas) - 1]
            return saida if isinstance(saida, str) else json.dumps(saida)

        return gerar, chamadas

    def validar(self, gerar):
        return schemas.validar_com_correcao(gerar, self.texto08, "dados/originais/caso8.txt", DATA_MINIMA, HOJE)

    def test_acerta_de_primeira(self):
        gerar, chamadas = self.gerador(self.esperado08)
        resultado = self.validar(gerar)
        self.assertEqual((resultado.decisao, len(chamadas)), ("aceita", 1))
        self.assertIsNone(chamadas[0])
        self.assertFalse(resultado.minuta_bloqueada)

    def test_corrige_na_segunda_tentativa_com_os_erros(self):
        gerar, chamadas = self.gerador(self.com(prioridade="alta"), self.esperado08)
        resultado = self.validar(gerar)
        self.assertEqual((resultado.decisao, len(chamadas)), ("aceita", 2))
        self.assertEqual([erro.categoria for erro in chamadas[1]], ["chave_extra"])
        self.assertEqual(resultado.tentativas[0]["erros"][0]["categoria"], "chave_extra")

    def test_continua_invalida_e_rejeitada_sem_terceira_tentativa(self):
        invalida = json.dumps(self.esperado08)[:-40]
        gerar, chamadas = self.gerador(invalida, invalida, self.esperado08)
        resultado = self.validar(gerar)
        self.assertEqual((resultado.decisao, len(chamadas)), ("rejeitada", 2))
        self.assertTrue(resultado.minuta_bloqueada)
        self.assertIsNone(resultado.solicitacao)
        self.assertEqual(resultado.motivos, ["json_invalido em JSON"])

    def test_regra_violada_vai_para_revisao_sem_nova_tentativa(self):
        gerar, chamadas = self.gerador(self.com(protocolo="2026-000999"), self.esperado08)
        resultado = self.validar(gerar)
        self.assertEqual((resultado.decisao, len(chamadas)), ("revisar", 1))
        self.assertTrue(resultado.minuta_bloqueada)
        self.assertIn("dado_nao_presente_no_original", resultado.motivos[0])

    def test_alerta_de_seguranca_revisa_sem_bloquear_a_minuta(self):
        # Como no Desafio 1: a injeção é ignorada, a minuta é montada e o alerta leva à revisão
        gerar, _ = self.gerador(self.com(alertas_seguranca=["tentativa de prompt injection"]))
        resultado = self.validar(gerar)
        self.assertEqual(resultado.decisao, "revisar")
        self.assertFalse(resultado.minuta_bloqueada)

    def test_registro_preserva_entrada_erro_e_decisao_sem_o_texto(self):
        gerar, _ = self.gerador(self.com(prioridade="alta"), self.com(protocolo="2026-000999"))
        registro = self.validar(gerar).para_registro()
        self.assertEqual(registro["decisao"], "revisar")
        self.assertEqual(registro["entrada"]["arquivo"], "dados/originais/caso8.txt")
        self.assertEqual(len(registro["entrada"]["sha256_texto"]), 64)
        self.assertEqual(registro["tentativas"][0]["erros"][0]["categoria"], "chave_extra")
        self.assertEqual(registro["erros_regras"][0]["categoria"], "dado_nao_presente_no_original")
        self.assertNotIn("Ana Paula Ribeiro Lopes", json.dumps(registro, ensure_ascii=False))


class TestRF14Apoio(_BaseRF14):
    """Data de abertura do processo, datas no texto, exibição e compatibilidade."""

    def test_data_de_abertura_vem_do_acervo(self):
        self.assertEqual(schemas.data_abertura_processo(), DATA_MINIMA)
        with TemporaryDirectory() as pasta:
            self.assertIsNone(schemas.data_abertura_processo(Path(pasta) / "nao_existe.json"))

    def test_datas_no_texto_nos_dois_formatos(self):
        texto = "Pedido de 14 de outubro de 2026, início em 01/02/2027 e uma data errada 31/02/2026."
        self.assertEqual(schemas.datas_no_texto(texto), {date(2026, 10, 14), date(2027, 2, 1)})

    def test_ausencia_aparece_como_nao_localizado(self):
        self.assertEqual(schemas.para_exibicao(None), VALOR_AUSENTE)
        self.assertEqual(schemas.para_exibicao("  "), VALOR_AUSENTE)
        self.assertEqual(schemas.para_exibicao("2026-000201"), "2026-000201")

    def test_esperado_do_gabarito_nao_altera_o_gabarito(self):
        original = json.dumps(self.caso08, sort_keys=True)
        esperado = schemas.esperado_do_gabarito(self.caso08)
        esperado["entidades"]["datas"].clear()
        esperado["dados_curso"]["curso"] = "outro"
        self.assertEqual(json.dumps(self.caso08, sort_keys=True), original)

    def test_conversao_para_os_campos_do_desafio_1(self):
        solicitacao, _ = schemas.validar_estrutura(json.dumps(self.com(protocolo=None, campos_ausentes=["protocolo"])))
        campos = schemas.para_campos_v1(solicitacao, "dados/originais/caso8.txt")
        self.assertEqual(list(campos), list(CAMPOS))
        self.assertEqual(campos["protocolo"], {"valor": VALOR_AUSENTE, "fonte": FONTE_AUSENTE})
        self.assertEqual(campos["curso"], {"valor": "Técnico em Enfermagem", "fonte": "dados/originais/caso8.txt"})
        self.assertEqual(campos["documentos_necessarios"]["valor"], VALOR_AUSENTE)


if __name__ == "__main__":
    unittest.main()
