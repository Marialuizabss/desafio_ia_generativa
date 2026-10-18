import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src import audio, audit, configuracao, fluxo, llm_client, peca_orientacao, versoes, vision

BASE_DIR = Path(__file__).resolve().parent.parent


class TestConfigJson(unittest.TestCase):
    """RF01: caminhos, modelos e parâmetros num arquivo de configuração sem segredos."""

    def setUp(self):
        self.bruto = (BASE_DIR / "config.json").read_text(encoding="utf-8")
        self.config = json.loads(self.bruto)

    def test_tem_as_quatro_secoes(self):
        for secao in ("caminhos", "modelos", "parametros", "custos_estimados_usd"):
            self.assertIsInstance(self.config[secao], dict)

    def test_nao_tem_nada_parecido_com_chave(self):
        self.assertIsNone(re.search(r"sk-[A-Za-z0-9_-]{8,}", self.bruto))
        self.assertNotRegex(self.bruto.casefold(), r"api_?key|secret|senha|password|token")

    def test_caminhos_de_entrada_existem(self):
        for nome in ("originais", "gabaritos", "modelo_minuta", "brasao", "modelos_analise"):
            with self.subTest(caminho=nome):
                self.assertTrue((BASE_DIR / self.config["caminhos"][nome]).exists())

    def test_modulos_usam_os_valores_do_arquivo(self):
        modelos, parametros = self.config["modelos"], self.config["parametros"]
        self.assertEqual(audio.MODELO, modelos["transcricao"])
        self.assertEqual(audio.MODELO_VOZ, modelos["voz"])
        self.assertEqual(audio.VOZ, parametros["voz"])
        self.assertEqual(vision.MODELO_VISUAL, modelos["leitura_visual"])
        self.assertEqual(peca_orientacao.MODELO_IMAGEM, modelos["imagem"])
        self.assertEqual(llm_client.TIMEOUT_SEGUNDOS, float(parametros["timeout_segundos"]))
        self.assertEqual(fluxo.MODELOS_LEITURA["imagem"], modelos["leitura_visual"])
        self.assertEqual(audit.ARQUIVO_REGISTRO, BASE_DIR / self.config["caminhos"]["registro"])

    def test_modelo_de_analise_vem_do_arquivo_da_interface(self):
        modelos = json.loads((BASE_DIR / "config" / "modelos.json").read_text(encoding="utf-8"))
        self.assertEqual(llm_client.MODELO, modelos["modelo_padrao"])


class TestCarregarConfig(unittest.TestCase):
    def test_item_ausente_usa_o_padrao(self):
        with TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "config.json"
            arquivo.write_text('{"parametros": {"voz": "coral"}}', encoding="utf-8")
            config = configuracao.carregar_config(arquivo)
        self.assertEqual(config["parametros"]["voz"], "coral")
        self.assertEqual(config["parametros"]["idioma"], "pt")
        self.assertEqual(config["modelos"]["transcricao"], "gpt-4o-transcribe")

    def test_json_invalido_tem_mensagem_clara(self):
        with TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "config.json"
            arquivo.write_text('{"parametros": ', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "não é um JSON válido"):
                configuracao.carregar_config(arquivo)

    def test_sem_arquivo_usa_os_padroes(self):
        config = configuracao.carregar_config(Path("/nao/existe/config.json"))
        self.assertEqual(config, configuracao.PADROES)


class TestVersoes(unittest.TestCase):
    def test_le_o_requirements_e_detecta_diferencas(self):
        with TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "requirements.txt"
            arquivo.write_text("openai==0.0.1  # antiga\npacote-que-nao-existe==1.0\n\n", encoding="utf-8")
            resultado = {item["pacote"]: item for item in versoes.conferir(arquivo)}
        self.assertFalse(resultado["openai"]["ok"])
        self.assertIsNotNone(resultado["openai"]["instalada"])
        self.assertIsNone(resultado["pacote-que-nao-existe"]["instalada"])

    def test_requirements_do_projeto_esta_fixado(self):
        pacotes = dict(versoes.exigidas())
        for nome in ("openai", "streamlit", "python-dotenv", "PyMuPDF", "Pillow", "mutagen"):
            self.assertIn(nome, pacotes)

    def test_versao_do_python_registrada(self):
        self.assertEqual((BASE_DIR / ".python-version").read_text(encoding="utf-8").strip(), "3.13")


if __name__ == "__main__":
    unittest.main()
