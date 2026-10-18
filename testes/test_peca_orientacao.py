import base64
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from PIL import Image

from src import audit, peca_orientacao as peca

BRASAO = Path(__file__).resolve().parent.parent / "dados" / "originais" / "brasao.png"
CHECKLIST_OK = {chave: True for chave, _ in peca.CHECKLIST}


def png_base64(largura=1536, altura=1024):
    buffer = io.BytesIO()
    Image.new("RGB", (largura, altura), "#DDEBE1").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def cliente_de_imagem(conteudo):
    cliente = MagicMock()
    resposta = cliente.images.generate.return_value
    resposta.data = [MagicMock(b64_json=conteudo)] if conteudo is not None else []
    return cliente


class BasePeca(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "dados" / "originais").mkdir(parents=True)
        (self.base / "dados" / "originais" / "brasao.png").write_bytes(BRASAO.read_bytes())
        for alvo, nome, valor in (
            (peca, "BASE_DIR", self.base),
            (audit, "ARQUIVO_REGISTRO", self.base / "execucoes.jsonl"),
        ):
            patcher = patch.object(alvo, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

    def gerar(self, conteudo="png"):
        conteudo = png_base64() if conteudo == "png" else conteudo
        with patch.object(peca, "OpenAI", return_value=cliente_de_imagem(conteudo)) as openai:
            versao = peca.gerar_ilustracao()
        return versao, openai.return_value

    def eventos(self):
        arquivo = self.base / "execucoes.jsonl"
        if not arquivo.is_file():
            return []
        return [json.loads(linha) for linha in arquivo.read_text(encoding="utf-8").splitlines()]


class TestPrompt(unittest.TestCase):
    def test_prompt_tem_os_seis_elementos_do_rf10(self):
        for rotulo in ("Sujeito:", "Composição:", "Estilo:", "Iluminação:", "Proporção:", "Restrições:"):
            self.assertIn(rotulo, peca.PROMPT_ILUSTRACAO)

    def test_restricoes_de_texto_e_pessoas(self):
        restricoes = peca.PROMPT_ILUSTRACAO.split("Restrições:")[1]
        for termo in ("nenhuma letra", "letreiro", "nenhuma pessoa", "logotipo", "dados pessoais"):
            self.assertIn(termo, restricoes)
        self.assertIn("nenhum papel com título ou cabeçalho", peca.PROMPT_ILUSTRACAO)
        self.assertNotIn("formulário", peca.PROMPT_ILUSTRACAO)

    def test_composicao_pede_faixa_central_para_o_recorte(self):
        composicao = peca.PROMPT_ILUSTRACAO.split("Composição:")[1].split("Estilo:")[0]
        self.assertIn("faixa horizontal central", composicao)


class TestGeracao(BasePeca):
    def test_gera_versao_pendente_com_metadados(self):
        versao, cliente = self.gerar()

        argumentos = cliente.images.generate.call_args.kwargs
        self.assertEqual(argumentos["model"], "gpt-image-1")
        self.assertEqual(argumentos["size"], "1536x1024")
        self.assertEqual(argumentos["prompt"], peca.PROMPT_ILUSTRACAO)
        self.assertEqual(versao["versao"], 1)
        self.assertEqual(versao["revisao_humana"], "pendente")
        self.assertTrue((self.base / versao["arquivo"]).is_file())
        salvo = json.loads((self.base / "resultados/logs/metadados_peca_orientacao.json").read_text(encoding="utf-8"))
        self.assertEqual(salvo["versoes"][0]["prompt"], peca.PROMPT_ILUSTRACAO)
        self.assertIn("data_geracao", salvo["versoes"][0])
        self.assertEqual(self.eventos()[0]["acao"], "geracao")

    def test_nao_gera_outra_com_revisao_pendente(self):
        self.gerar()
        with self.assertRaises(ValueError):
            self.gerar()

    def test_resposta_vazia_nao_deixa_arquivo_e_registra_erro(self):
        with self.assertRaises(ValueError):
            self.gerar(conteudo=None)
        self.assertEqual(peca.carregar_versoes(), [])
        self.assertEqual(self.eventos()[0]["resultado"], "erro")


class TestRevisao(BasePeca):
    def test_aprovar_exige_checklist_completo_e_revisor(self):
        self.gerar()
        with self.assertRaises(ValueError):
            peca.revisar_ilustracao(1, "aprovada", "Ana", {"sem_texto": True})
        with self.assertRaises(ValueError):
            peca.revisar_ilustracao(1, "aprovada", " ", CHECKLIST_OK)

        aprovada = peca.revisar_ilustracao(1, "aprovada", "Ana", CHECKLIST_OK, "Coerente.")
        self.assertEqual(aprovada["revisao_humana"], "aprovada")
        self.assertEqual(peca.versao_vigente()["versao"], 1)

    def test_reprovar_exige_motivo_e_mantem_a_vigente(self):
        self.gerar()
        peca.revisar_ilustracao(1, "aprovada", "Ana", CHECKLIST_OK)
        self.gerar()
        with self.assertRaises(ValueError):
            peca.revisar_ilustracao(2, "reprovada", "Ana")
        peca.revisar_ilustracao(2, "reprovada", "Ana", nota="Apareceram letras.")

        self.assertEqual(peca.versao_vigente()["versao"], 1)
        self.assertEqual(len(peca.carregar_versoes()), 2)
        self.assertTrue((self.base / "resultados/imagens/orientacao/ilustracao_v02.png").is_file())

    def test_versao_ja_revisada_nao_muda(self):
        self.gerar()
        peca.revisar_ilustracao(1, "aprovada", "Ana", CHECKLIST_OK)
        with self.assertRaises(ValueError):
            peca.revisar_ilustracao(1, "reprovada", "Ana", nota="Mudei de ideia.")


class TestRevogacao(BasePeca):
    def test_revogar_tira_de_uso_sem_apagar(self):
        self.gerar()
        peca.revisar_ilustracao(1, "aprovada", "Ana", CHECKLIST_OK)
        with self.assertRaises(ValueError):
            peca.revogar_ilustracao(1, "Ana", " ")
        peca.revogar_ilustracao(1, "Ana", "Texto na ilustração notado depois.")

        self.assertIsNone(peca.versao_vigente())
        versao = peca.carregar_versoes()[0]
        self.assertEqual(versao["revisao_humana"], "revogada")
        self.assertTrue((self.base / versao["arquivo"]).is_file())
        self.assertEqual(self.eventos()[-1]["acao"], "revogacao")

    def test_so_revoga_aprovada(self):
        self.gerar()
        with self.assertRaises(ValueError):
            peca.revogar_ilustracao(1, "Ana", "Motivo.")


class TestPecaDoAtendimento(BasePeca):
    REGISTRO = {
        "id_execucao": "28b62555-aaaa",
        "arquivo_origem": "dados/originais/entrada_audio.mp3",
        "campos": {
            "curso": {"valor": "Técnico em Enfermagem"},
            "eixo": {"valor": "Saúde"},
            "solicitante": {"valor": "Marcos Vinícius"},
        },
    }

    def test_sem_vigente_nao_monta(self):
        self.assertIsNone(peca.peca_do_atendimento(self.REGISTRO))

    def test_monta_uma_vez_com_os_campos_aprovados_sem_dados_pessoais(self):
        self.gerar()
        peca.revisar_ilustracao(1, "aprovada", "Ana", CHECKLIST_OK)
        with patch.object(peca, "compor_peca", wraps=peca.compor_peca) as compor:
            primeira = peca.peca_do_atendimento(self.REGISTRO)
            segunda = peca.peca_do_atendimento(self.REGISTRO)

        self.assertEqual(compor.call_count, 1)
        dados = compor.call_args.args[2]
        self.assertEqual(dados["curso"], "Técnico em Enfermagem")
        self.assertEqual(dados["eixo"], "Saúde")
        self.assertNotIn("Marcos", json.dumps(dados, ensure_ascii=False))
        self.assertEqual(primeira["arquivo"], segunda["arquivo"])
        with Image.open(self.base / primeira["arquivo"]) as imagem:
            self.assertEqual(imagem.size, (1024, 1536))
        evento = [e for e in self.eventos() if e.get("acao") == "peca"][0]
        self.assertNotIn("Marcos", json.dumps(evento, ensure_ascii=False))

    def test_montagem_sem_fontes_do_sistema(self):
        ilustracao = self.base / "ilustracao.png"
        Image.new("RGB", (1536, 1024), "#DDEBE1").save(ilustracao)
        with patch.dict(peca._FONTES, {False: ("/nao/existe.ttf",), True: ("/nao/existe.ttf",)}):
            destino = peca.compor_peca(ilustracao, self.base / "peca.png", {"curso": "Curso", "eixo": "Eixo"})
        with Image.open(destino) as imagem:
            self.assertEqual(imagem.size, (1024, 1536))


class TestPassoAPasso(unittest.TestCase):
    """Os passos vêm dos campos aprovados; o que falta vira orientação, nunca invenção."""

    def test_campos_preenchidos_viram_passos(self):
        passos = dict(peca.passos_da_peca({
            "documentos": "documento de identidade com foto; CPF; uma foto 3x4",
            "prazo": "até 5 dias úteis após a resposta",
            "local": "Secretaria Escolar, das 8h às 17h",
            "ciencia": "O(a) solicitante declarou estar ciente de que a matrícula será cancelada se faltar.",
        }))
        self.assertEqual(passos["O QUE LEVAR"], ["• Documento de identidade com foto", "• CPF", "• Uma foto 3x4"])
        self.assertEqual(passos["ATÉ QUANDO"], ["Até 5 dias úteis após a resposta"])
        self.assertEqual(passos["ONDE IR"], ["Secretaria Escolar, das 8h às 17h"])
        self.assertEqual(passos["DEPOIS DA MATRÍCULA"], ["A matrícula será cancelada se faltar."])

    def test_campos_ausentes_viram_orientacao(self):
        passos = dict(peca.passos_da_peca({}))
        self.assertIn("A secretaria informará", passos["O QUE LEVAR"][0])
        self.assertIn("prazo informado pela secretaria", passos["ATÉ QUANDO"][0])
        self.assertIn("Procure a Secretaria Escolar", passos["ONDE IR"][0])
        self.assertNotIn("DEPOIS DA MATRÍCULA", passos)

    def test_nao_localizado_conta_como_ausente(self):
        registro = {"campos": {"documentos_necessarios": {"valor": "não localizado"}}}
        self.assertEqual(peca.dados_da_peca(registro)["documentos"], "")

    def test_dados_da_peca_nao_levam_nome_protocolo_nem_datas(self):
        registro = {"campos": {
            "solicitante": {"valor": "Marcos"}, "protocolo": {"valor": "2026-000142"},
            "data_solicitacao": {"valor": "14/10/2026"}, "curso": {"valor": "Técnico"},
        }}
        texto = json.dumps(peca.dados_da_peca(registro), ensure_ascii=False)
        for dado in ("Marcos", "2026-000142", "14/10/2026"):
            self.assertNotIn(dado, texto)

    def test_texto_longo_reduz_a_letra_e_cabe(self):
        ilustracao = Image.new("RGB", (1536, 1024), "#DDEBE1")
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "i.png"
            ilustracao.save(caminho)
            dados = {"documentos": "; ".join(f"documento número {n} com descrição longa" for n in range(30)),
                     "ciencia": "Regra " * 300}
            destino = peca.compor_peca(caminho, Path(pasta) / "p.png", dados)
            with Image.open(destino) as imagem:
                self.assertEqual(imagem.size, (1024, 1536))


if __name__ == "__main__":
    unittest.main()
