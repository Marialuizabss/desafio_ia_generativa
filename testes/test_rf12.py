import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import audit, fluxo
from src.extracao import resultado_de_dict
from src.privacidade import MARCADORES, contar_remocoes, minimizar_texto

BASE_DIR = Path(__file__).resolve().parent.parent

CASOS_DE_TEXTO = {
    "caso1_solicitacao_completa.txt": "gabarito_caso01.json",
    "caso2_solicitacao_incompleta.txt": "gabarito_caso02.json",
    "caso3_solicitacao_prompt_injection.txt": "gabarito_caso03.json",
    "caso3b_solicitacao_injection_delimitador.txt": "gabarito_caso03b.json",
    "entrada_texto.txt": "gabarito_entrada_texto.json",
}

# Campos da minuta que aparecem literalmente nas entradas e não podem ser apagados
CAMPOS_PRESERVADOS = (
    "solicitante", "protocolo", "data_solicitacao", "curso", "eixo", "turno", "data_inicio",
)


class TestRF12Remocao(unittest.TestCase):
    """Cada dado pessoal é removido nas formas em que aparece nas entradas."""

    EXEMPLOS = {
        "cpf": [
            "CPF 123.456.789-00.",
            "meu cpf é 11122233344.",
            "Meu CPF é 1-2-3-4-5-6-7-8-9-00, meu",
            "CPF: 123.456.789-00",
        ],
        "rg": [
            "RG 1234567-8;",
            "RG nº 12.345.678-9.",
            "meu RG é 1-2-3-4-5-6-7-8, o",
        ],
        "email": [
            "e-mail marcos.almeida.teste@examplo.com.",
            "E-MAIL: MARCOS.ALMEIDA.TESTE @ EXAMPLO.COM",
            "o meu e-mail é marcos.almeida.teste.com. Declaro",
        ],
        "telefone": [
            "TEL. CELULAR: (65) 99876-5432",
            "meu telefone é 65 9 9876-5432.",
        ],
        "data_nascimento": [
            "nasci em 12/08/2008, e",
            "nasci em 12 de agosto de 2008, e",
            "DATA DE NASCIMENTO: 12/08/2008",
        ],
        "naturalidade": [
            "nasci em 12/08/2008, em Cuiabá, e",
            "NATURALIDADE: CUIABÁ UF:",
        ],
        "filiacao": [
            "nome da mãe, Lúcia Helena de Almeida Santos;",
            "o nome da minha mãe é Lúcia Helena de Almeida Santos, e",
            "NOME DA MÃE: LUCIA HELENA DE ALMEIDA SANTOS",
            "O nome do meu pai é João da Silva, e",
        ],
    }

    VALORES_PESSOAIS = [
        "123.456.789-00", "11122233344", "1-2-3-4-5-6-7-8-9-00", "1234567-8", "12.345.678-9",
        "1-2-3-4-5-6-7-8", "marcos.almeida", "MARCOS.ALMEIDA", "99876-5432", "9 9876-5432",
        "12/08/2008", "12 de agosto de 2008", "Cuiabá", "CUIABÁ", "Lúcia", "LUCIA", "João da Silva",
    ]

    def test_dados_pessoais_sao_substituidos_pelo_marcador(self):
        for categoria, exemplos in self.EXEMPLOS.items():
            for exemplo in exemplos:
                with self.subTest(categoria=categoria, exemplo=exemplo):
                    minimizado = minimizar_texto(exemplo)

                    self.assertIn(MARCADORES[categoria], minimizado)
                    for valor in self.VALORES_PESSOAIS:
                        self.assertNotIn(valor, minimizado)

    def test_entrada_do_professor_sem_nenhum_dado_pessoal(self):
        texto = (BASE_DIR / "dados" / "originais" / "entrada_texto.txt").read_text(encoding="utf-8")

        minimizado = minimizar_texto(texto)

        self.assertEqual(
            contar_remocoes(minimizado),
            {"cpf": 1, "rg": 1, "email": 1, "data_nascimento": 1,
             "naturalidade": 1, "filiacao": 1},
        )
        for valor in ("123.456.789-00", "1234567-8", "@", "12/08/2008", "Cuiabá", "Lúcia"):
            self.assertNotIn(valor, minimizado)

    def test_transcricao_do_audio_sem_nenhum_dado_pessoal(self):
        transcricao = (
            "Meu nome é Marcos Vinícius de Almeida Santos, nasci em 12 de agosto de 2008, "
            "em Cuiabá, e quero pedir a efetivação da minha matrícula. Meu CPF é "
            "1-2-3-4-5-6-7-8-9-00, meu RG é 1-2-3-4-5-6-7-8, o nome da minha mãe é "
            "Lúcia Helena de Almeida Santos, e o meu e-mail é marcos.almeida.teste.com."
        )

        minimizado = minimizar_texto(transcricao)

        self.assertEqual(len(contar_remocoes(minimizado)), 6)
        self.assertIn("Marcos Vinícius de Almeida Santos", minimizado)
        for valor in ("1-2-3", "12 de agosto", "Cuiabá", "Lúcia", "marcos.almeida"):
            self.assertNotIn(valor, minimizado)


class TestRF12Preservacao(unittest.TestCase):
    """Os dados que preenchem a minuta continuam no texto enviado ao modelo."""

    def test_campos_da_minuta_preservados_nos_casos_de_texto(self):
        for entrada, gabarito in CASOS_DE_TEXTO.items():
            texto = (BASE_DIR / "dados" / "originais" / entrada).read_text(encoding="utf-8")
            esperado = json.loads(
                (BASE_DIR / "dados" / "gabaritos" / gabarito).read_text(encoding="utf-8")
            )["extracao_esperada"]

            minimizado = minimizar_texto(texto).casefold()

            for campo in CAMPOS_PRESERVADOS:
                valor = esperado[campo]["valor"]
                if valor == "não localizado":
                    continue
                with self.subTest(entrada=entrada, campo=campo):
                    self.assertIn(valor.casefold(), minimizado)

            if esperado["regras_ciencia"]["valor"] != "não localizado":
                with self.subTest(entrada=entrada, campo="regras_ciencia"):
                    self.assertIn("ciente", minimizado)

    def test_ficha_preserva_campos_do_curso(self):
        ficha = (
            "CÓDIGO: 2026-000142\n"
            "NOME: MARCOS VINICIUS DE ALMEIDA SANTOS\n"
            "NOME DO PAI:\n"
            "CURSO: TECNICO EM ENFERMAGEM CH: 1200 HORAS\n"
            "MUNICÍPIO: TURNO: NOTURNO\n"
            "INÍCIO DO CURSO: 01/02/2027 TÉRMINO DO CURSO:\n"
            "DATA MATRICULA: 14/10/2026"
        )

        self.assertEqual(minimizar_texto(ficha), ficha)

    def test_texto_sem_dados_pessoais_fica_igual(self):
        textos = [
            "Os documentos necessários são RG, CPF e comprovante de residência.",
            "Canal: E-mail\nProtocolo: 2026-000142\nData: 14/10/2026",
            "Protocolo 2026-000157, de 15/10/2026, início em 01/02/2027, 1.200 horas.",
            "NOME DO PAI:  TURNO: NOTURNO",
            "",
        ]
        for texto in textos:
            with self.subTest(texto=texto):
                self.assertEqual(minimizar_texto(texto), texto)
                self.assertEqual(contar_remocoes(minimizar_texto(texto)), {})

    def test_marcador_nao_e_reprocessado(self):
        minimizado = minimizar_texto("nasci em 12/08/2008, em Cuiabá. NATURALIDADE: CUIABÁ")

        self.assertEqual(minimizado.count("[NATURALIDADE REMOVIDA]"), 2)
        self.assertNotIn("[NATURALIDADE [", minimizado)
        self.assertEqual(minimizar_texto(minimizado), minimizado)


class TestRF12Fluxo(unittest.TestCase):
    """O fluxo envia ao modelo o texto já minimizado e registra o que removeu."""

    TEXTO = (
        "Protocolo 2026-000142. Meu nome é Marcos Vinícius de Almeida Santos, "
        "CPF 123.456.789-00, RG 1234567-8, e-mail marcos.almeida.teste@examplo.com."
    )

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.processados = self.base / "dados" / "processados"
        (self.base / "dados" / "originais").mkdir(parents=True)
        (self.base / "dados" / "originais" / "pedido.txt").write_text(self.TEXTO, encoding="utf-8")
        self.entrada = {"modalidade": "texto", "caminho_copia": "dados/originais/pedido.txt"}

        for nome, valor in (("BASE_DIR", self.base), ("PASTA_PROCESSADOS", self.processados)):
            patcher = patch.object(fluxo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

        patcher = patch.object(audit, "ARQUIVO_REGISTRO", self.base / "execucoes.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)

        self.enviados = []

        def extrair_simulado(texto, arquivo, **_):
            self.enviados.append(texto)
            resultado = resultado_de_dict({"categoria": "matricula", "minuta": "Minuta"}, arquivo)
            return resultado, {"modelo": "gpt-6-luna", "temperatura": None, "idioma": None}

        patcher = patch.object(fluxo, "extrair_campos", side_effect=extrair_simulado)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_modelo_recebe_texto_minimizado(self):
        fluxo.processar_entrada(self.entrada)

        enviado = self.enviados[0]
        self.assertIn("[CPF REMOVIDO]", enviado)
        self.assertIn("Marcos Vinícius de Almeida Santos", enviado)
        for valor in ("123.456.789-00", "1234567-8", "@"):
            self.assertNotIn(valor, enviado)

    def test_registro_guarda_texto_minimizado_e_remocoes(self):
        registro = fluxo.processar_entrada(self.entrada)

        self.assertEqual(registro["dados_removidos"], {"cpf": 1, "rg": 1, "email": 1})
        self.assertNotIn("123.456.789-00", registro["texto_extraido"])

        gravado = (self.processados / "extracao_pedido.json").read_text(encoding="utf-8")
        self.assertNotIn("123.456.789-00", gravado)
        self.assertIn('"dados_removidos"', gravado)

    def test_extracao_antiga_sem_minimizacao_e_refeita(self):
        self.processados.mkdir(parents=True)
        antiga = {
            "arquivo_origem": "dados/originais/pedido.txt",
            "modelo": "gpt-6-luna",
            "texto_extraido": self.TEXTO,
            "chamada": {"temperatura": None, "idioma": None},
        }
        (self.processados / "extracao_pedido.json").write_text(json.dumps(antiga), encoding="utf-8")

        registro = fluxo.processar_entrada(self.entrada)

        self.assertEqual(len(self.enviados), 1)
        self.assertIn("dados_removidos", registro)

    def test_extracao_ja_minimizada_e_reaproveitada(self):
        fluxo.processar_entrada(self.entrada)
        fluxo.processar_entrada(self.entrada)

        self.assertEqual(len(self.enviados), 1)


if __name__ == "__main__":
    unittest.main()
