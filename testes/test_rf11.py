import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import audit, fluxo, llm_client
from src.extracao import resultado_de_dict
from testes.test_rf03 import cliente_simulado, resposta_valida

CHAVE_FALSA = "sk-proj-" + "x" * 30


class BaseRegistro(unittest.TestCase):
    """Cada teste grava num registro temporário, nunca no real."""

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.registro = self.base / "execucoes.jsonl"
        patcher = patch.object(audit, "ARQUIVO_REGISTRO", self.registro)
        patcher.start()
        self.addCleanup(patcher.stop)

    def linhas(self):
        return [json.loads(l) for l in self.registro.read_text(encoding="utf-8").splitlines()]


class TestRF11Registro(BaseRegistro):
    """O registro acumula eventos e não guarda credenciais."""

    def test_eventos_sao_acrescentados_sem_sobrescrever(self):
        primeira = audit.registrar_execucao({"resultado": "sucesso"})
        segunda = audit.registrar_execucao({"resultado": "erro"})

        linhas = self.linhas()
        self.assertEqual(len(linhas), 2)
        self.assertNotEqual(primeira, segunda)
        self.assertEqual([l["id_execucao"] for l in linhas], [primeira, segunda])
        for linha in linhas:
            self.assertEqual(linha["evento"], "execucao")
            self.assertIn("data_hora", linha)

    def test_credenciais_nao_sao_gravadas(self):
        audit.registrar_execucao({
            "api_key": CHAVE_FALSA,
            "OPENAI_API_KEY": CHAVE_FALSA,
            "erro": f"AuthenticationError: chave {CHAVE_FALSA} inválida",
            "parametros": {"authorization": f"Bearer {CHAVE_FALSA}"},
        })

        gravado = self.registro.read_text(encoding="utf-8")
        self.assertNotIn(CHAVE_FALSA, gravado)
        linha = self.linhas()[0]
        self.assertNotIn("api_key", linha)
        self.assertNotIn("OPENAI_API_KEY", linha)
        self.assertEqual(linha["parametros"], {})
        self.assertIn("[CREDENCIAL REMOVIDA]", linha["erro"])

    def test_contagem_de_tokens_e_preservada(self):
        audit.registrar_execucao({"tokens_entrada": 100, "tokens_saida": 50})

        linha = self.linhas()[0]
        self.assertEqual((linha["tokens_entrada"], linha["tokens_saida"]), (100, 50))


class TestRF11Decisao(BaseRegistro):
    """A decisão humana fica ligada à execução avaliada."""

    def test_aprovacao_dispensa_justificativa(self):
        id_execucao = audit.registrar_execucao({"resultado": "sucesso"})
        decisao = audit.registrar_decisao(id_execucao, "aprovado", revisor="Ana", conferencia_dados_criticos=True)

        self.assertEqual(decisao["evento"], "decisao")
        self.assertEqual(decisao["revisor"], "Ana")
        self.assertTrue(decisao["conferencia_dados_criticos"])

    def test_rejeicao_e_nova_geracao_exigem_justificativa(self):
        id_execucao = audit.registrar_execucao({"resultado": "sucesso"})
        for decisao in ("rejeitado", "nova_geracao"):
            with self.subTest(decisao=decisao), self.assertRaises(ValueError):
                audit.registrar_decisao(id_execucao, decisao, justificativa="   ")
        self.assertEqual(len(self.linhas()), 1)

    def test_decisao_desconhecida_ou_sem_execucao_e_recusada(self):
        with self.assertRaises(ValueError):
            audit.registrar_decisao("abc", "talvez")
        with self.assertRaises(ValueError):
            audit.registrar_decisao("", "aprovado")

    def test_aprovacao_exige_revisor_e_conferencia(self):
        id_execucao = audit.registrar_execucao({"resultado": "sucesso"})
        with self.assertRaises(ValueError):
            audit.registrar_decisao(id_execucao, "aprovado", revisor="  ", conferencia_dados_criticos=True)
        with self.assertRaises(ValueError):
            audit.registrar_decisao(id_execucao, "aprovado", revisor="Ana", conferencia_dados_criticos=False)
        self.assertEqual(len(self.linhas()), 1)

        decisao = audit.registrar_decisao(
            id_execucao, "aprovado_com_revisao", revisor="Ana", conferencia_dados_criticos=True,
        )
        self.assertEqual(decisao["decisao"], "aprovado_com_revisao")
        self.assertEqual(decisao["revisor"], "Ana")
        self.assertEqual(decisao["justificativa"], "")

    def test_campo_nao_localizado_vira_aprovado_com_revisao(self):
        from src.extracao import CAMPOS, VALOR_AUSENTE

        registro = {"campos": {nome: {"valor": "ok"} for nome in CAMPOS}}
        self.assertEqual(fluxo.decisao_de_aprovacao(registro), "aprovado")
        registro["campos"]["protocolo"] = {"valor": VALOR_AUSENTE}
        self.assertEqual(fluxo.decisao_de_aprovacao(registro), "aprovado_com_revisao")

    def test_historico_reune_execucao_e_decisoes(self):
        id_execucao = audit.registrar_execucao({"resultado": "sucesso"})
        audit.registrar_execucao({"resultado": "sucesso"})
        audit.registrar_decisao(
            id_execucao, "nova_geracao", justificativa="Data de início errada.", revisor="Ana",
        )
        audit.registrar_decisao(
            id_execucao, "aprovado", revisor="Ana", conferencia_dados_criticos=True,
        )

        historico = audit.historico(id_execucao)
        self.assertEqual(historico["execucao"]["id_execucao"], id_execucao)
        self.assertEqual([d["decisao"] for d in historico["decisoes"]], ["nova_geracao", "aprovado"])


class TestRF11Chamada(unittest.TestCase):
    """A chamada ao modelo informa provedor, parâmetros e versão do prompt."""

    @staticmethod
    def chamar():
        cliente = cliente_simulado(json.dumps(resposta_valida()))
        with patch.object(llm_client, "OpenAI", return_value=cliente):
            _, chamada = llm_client.extrair_campos("Pedido de matrícula.", "pedido.txt")
        return chamada

    def test_chamada_traz_provedor_parametros_e_versao_do_prompt(self):
        chamada = self.chamar()

        self.assertEqual(chamada["provedor"], "OpenAI")
        self.assertRegex(chamada["versao_prompt"], r"^[0-9a-f]{12}$")
        self.assertIs(chamada["parametros"]["store"], False)

    def test_versao_muda_quando_o_prompt_muda(self):
        atual = self.chamar()["versao_prompt"]
        with patch.object(llm_client, "PROMPT_SISTEMA", llm_client.PROMPT_SISTEMA + "\nRegra nova."):
            alterada = self.chamar()["versao_prompt"]

        self.assertEqual(atual, self.chamar()["versao_prompt"])
        self.assertNotEqual(atual, alterada)


class TestRF11Fluxo(BaseRegistro):
    """Toda passagem pelo fluxo deixa um evento no registro."""

    def setUp(self):
        super().setUp()
        self.processados = self.base / "dados" / "processados"
        (self.base / "dados" / "originais").mkdir(parents=True)
        (self.base / "dados" / "originais" / "pedido.txt").write_text(
            "Protocolo 2026-000142. CPF 123.456.789-00.", encoding="utf-8"
        )
        self.entrada = {"modalidade": "texto", "caminho_copia": "dados/originais/pedido.txt"}
        for nome, valor in (("BASE_DIR", self.base), ("PASTA_PROCESSADOS", self.processados)):
            patcher = patch.object(fluxo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

    def simular(self, **efeito):
        patcher = patch.object(fluxo, "extrair_campos", **efeito)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def extrair_simulado(texto, arquivo, **_):
        resultado = resultado_de_dict({"categoria": "matricula", "minuta": "Minuta"}, arquivo)
        return resultado, {
            "modelo": "gpt-6-luna", "provedor": "OpenAI",
            "versao_prompt": llm_client.versao_do_prompt(None),
            "parametros": {"reasoning": {"effort": "low"}, "store": False},
            "tokens_entrada": 100, "tokens_saida": 50, "custo_estimado_usd": 0.0001,
            "tempo_resposta_segundos": 1.5,
        }

    def test_sucesso_e_registrado_e_ligado_a_extracao(self):
        self.simular(side_effect=self.extrair_simulado)
        registro = fluxo.processar_entrada(self.entrada)

        evento = self.linhas()[0]
        self.assertEqual(evento["id_execucao"], registro["id_execucao"])
        self.assertEqual(evento["resultado"], "sucesso")
        self.assertEqual(evento["versao_prompt"], llm_client.versao_do_prompt(None))
        self.assertEqual(evento["provedor"], "OpenAI")
        self.assertEqual(evento["categoria"], "matricula")
        self.assertEqual(evento["dados_removidos"], {"cpf": 1})
        self.assertIsNone(evento["modelo_leitura"])

        gravado = json.loads((self.processados / "extracao_pedido.json").read_text(encoding="utf-8"))
        self.assertEqual(gravado["id_execucao"], registro["id_execucao"])

    def test_registro_nao_guarda_texto_da_solicitacao(self):
        self.simular(side_effect=self.extrair_simulado)
        fluxo.processar_entrada(self.entrada)

        gravado = self.registro.read_text(encoding="utf-8")
        self.assertNotIn("texto_extraido", gravado)
        self.assertNotIn("2026-000142", gravado)
        self.assertNotIn("123.456.789-00", gravado)

    def test_erro_e_registrado_e_repassado(self):
        self.simular(side_effect=ValueError("A API retornou uma resposta vazia."))
        with self.assertRaises(ValueError):
            fluxo.processar_entrada(self.entrada)

        evento = self.linhas()[0]
        self.assertEqual(evento["resultado"], "erro")
        self.assertEqual(evento["erro"], "ValueError: A API retornou uma resposta vazia.")
        self.assertFalse((self.processados / "extracao_pedido.json").exists())

    def test_reaproveitamento_usa_o_mesmo_identificador(self):
        self.simular(side_effect=self.extrair_simulado)
        primeira = fluxo.processar_entrada(self.entrada)
        segunda = fluxo.processar_entrada(self.entrada)

        self.assertEqual(primeira["id_execucao"], segunda["id_execucao"])
        self.assertEqual(len(self.linhas()), 1)

    def test_extracao_antiga_reaproveitada_ganha_identificador(self):
        self.simular(side_effect=self.extrair_simulado)
        fluxo.processar_entrada(self.entrada)
        saida = self.processados / "extracao_pedido.json"
        antiga = json.loads(saida.read_text(encoding="utf-8"))
        del antiga["id_execucao"]
        saida.write_text(json.dumps(antiga, ensure_ascii=False), encoding="utf-8")

        registro = fluxo.processar_entrada(self.entrada)

        evento = self.linhas()[-1]
        self.assertEqual(evento["resultado"], "reaproveitada")
        self.assertEqual(registro["id_execucao"], evento["id_execucao"])
        self.assertNotIn("id_execucao", json.loads(saida.read_text(encoding="utf-8")))

    def test_rejeitada_nao_e_reaproveitada_e_o_json_fica_arquivado(self):
        self.simular(side_effect=self.extrair_simulado)
        primeira = fluxo.processar_entrada(self.entrada)
        audit.registrar_decisao(
            primeira["id_execucao"], "rejeitado", justificativa="Pessoa errada.", revisor="Ana",
        )
        saida = self.processados / "extracao_pedido.json"
        saida.write_text(saida.read_text(encoding="utf-8").replace("Minuta", "MINUTA_REJEITADA"), encoding="utf-8")

        segunda = fluxo.processar_entrada(self.entrada)

        self.assertNotEqual(primeira["id_execucao"], segunda["id_execucao"])
        self.assertEqual(segunda["id_execucao_anterior"], primeira["id_execucao"])
        arquivo = self.base / segunda["arquivo_extracao_anterior"]
        self.assertIn("MINUTA_REJEITADA", arquivo.read_text(encoding="utf-8"))
        self.assertIn("Minuta", saida.read_text(encoding="utf-8"))
        self.assertNotIn("MINUTA_REJEITADA", saida.read_text(encoding="utf-8"))
        evento = next(linha for linha in self.linhas() if linha["id_execucao"] == segunda["id_execucao"])
        self.assertEqual(evento["id_execucao_anterior"], primeira["id_execucao"])
        self.assertEqual(evento["arquivo_extracao_anterior"], segunda["arquivo_extracao_anterior"])

    def test_versao_diferente_do_prompt_nao_reaproveita(self):
        self.simular(side_effect=self.extrair_simulado)
        fluxo.processar_entrada(self.entrada)
        saida = self.processados / "extracao_pedido.json"
        antigo = json.loads(saida.read_text(encoding="utf-8"))
        antigo["chamada"]["versao_prompt"] = "0" * 12
        antigo["minuta"] = "MINUTA_ANTIGA"
        saida.write_text(json.dumps(antigo), encoding="utf-8")

        novo = fluxo.processar_entrada(self.entrada)

        self.assertEqual(novo["id_execucao_anterior"], antigo["id_execucao"])
        preservado = (self.base / novo["arquivo_extracao_anterior"]).read_text(encoding="utf-8")
        self.assertIn("MINUTA_ANTIGA", preservado)
        self.assertNotIn("MINUTA_ANTIGA", saida.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
