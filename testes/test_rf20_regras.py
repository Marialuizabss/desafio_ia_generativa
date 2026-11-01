"""RF20 — mensagens, estados e registro da decisão. Sem API e sem índice."""

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import audit
from src.acervo_operacao import incluir_documento
from src.consulta_acervo import (
    MENSAGEM_CONFLITO,
    MENSAGEM_INDICE,
    MENSAGEM_MINUTA_BLOQUEADA,
    MENSAGEM_SEM_EVIDENCIA,
    classificar_consulta,
    classificar_ficha,
    combinar_estado,
    linhas_da_ficha,
    minuta_do_atendimento,
    preparar_acervo,
    transicionar,
)
from types import SimpleNamespace
from src.schemas import Solicitacao, para_exibicao


class IndiceDesatualizadoError(RuntimeError):
    """Mesmo nome da exceção do índice, sem importar o banco vetorial."""


def _solicitacao(**extras):
    dados = {
        "versao_esquema": "2.0",
        "protocolo": None,
        "data_solicitacao": None,
        "solicitante": "Ana",
        "assunto": "Matrícula",
        "pedido": "Efetivar",
        "categoria": "matricula",
        "resumo": "Pedido de matrícula.",
        "entidades": {"pessoas": [], "orgaos": [], "locais": [], "datas": [], "protocolos": []},
        "dados_curso": {
            "curso": None, "eixo": None, "carga_horaria": None,
            "turno": None, "data_inicio": None, "regras_ciencia": None,
        },
        "campos_ausentes": [
            "protocolo", "data_solicitacao", "curso", "eixo",
            "carga_horaria", "turno", "data_inicio", "regras_ciencia",
        ],
        "alertas_seguranca": [],
        "requer_revisao": False,
        "motivos_revisao": [],
    }
    dados.update(extras)
    return Solicitacao.model_validate(dados)


class TestAcervo(unittest.TestCase):
    def test_aviso_de_arquivo_ausente_e_hash(self):
        catalogo = {"documentos": [
            {"doc_id": "ACV-01", "titulo": "Edital", "versao": "Original", "formato": "pdf", "sha256": "abc"},
            {"doc_id": "ACV-02", "titulo": "Retificação", "versao": "01", "formato": "pdf", "sha256": "def"},
        ]}
        validacoes = [
            {"doc_id": "ACV-01", "status": "arquivo_ausente"},
            {"doc_id": "ACV-02", "status": "hash_divergente"},
        ]
        linhas = preparar_acervo(catalogo, validacoes)
        self.assertEqual(linhas[0]["aviso"], "Arquivo ausente no acervo.")
        self.assertEqual(linhas[1]["aviso"], "O hash do arquivo não confere com o catálogo.")
        self.assertEqual(linhas[0]["sha256"], "abc")


class TestConsulta(unittest.TestCase):
    def test_indice_desatualizado_nao_traz_resposta(self):
        saida = classificar_consulta(erro=IndiceDesatualizadoError("modelo trocado"))
        self.assertEqual(saida["tipo"], "indice_desatualizado")
        self.assertEqual(saida["texto"], MENSAGEM_INDICE)
        self.assertIsNone(saida["resposta"])
        self.assertIsNone(saida["estado"])

    def test_sem_evidencia_vai_para_revisao(self):
        saida = classificar_consulta(resultado={
            "status": "sem_evidencia",
            "resposta": MENSAGEM_SEM_EVIDENCIA,
            "decisao": "revisar",
            "justificativa": "Nada no edital.",
            "fontes": [],
        })
        self.assertEqual(saida["tipo"], "sem_evidencia")
        self.assertEqual(saida["texto"], MENSAGEM_SEM_EVIDENCIA)
        self.assertEqual(saida["estado"], "revisar")
        self.assertIsNone(saida["resposta"])

    def test_conflito_mostra_as_passagens(self):
        fontes = [{"doc_id": "ACV-01", "trecho_citado": "15 a 19/06/2026"}, {"doc_id": "ACV-04", "trecho_citado": "22/06/2026"}]
        saida = classificar_consulta(resultado={
            "status": "conflito",
            "resposta": MENSAGEM_CONFLITO,
            "decisao": "revisar",
            "justificativa": "Datas divergentes.",
            "fontes": fontes,
        })
        self.assertEqual(saida["estado"], "revisar")
        self.assertEqual(saida["fontes"], fontes)
        self.assertIsNone(saida["resposta"])

    def test_falha_nao_inventa_resposta(self):
        saida = classificar_consulta(erro=ValueError("Não foi possível conectar ao serviço."))
        self.assertEqual(saida["tipo"], "falha")
        self.assertIn("Não foi possível conectar ao serviço.", saida["texto"])
        self.assertIsNone(saida["resposta"])
        self.assertEqual(saida["estado"], "revisar")

    def test_bloqueio_nao_abre_aprovacao(self):
        saida = classificar_consulta(resultado={
            "status": None,
            "decisao": "bloquear",
            "motivos_guardrail": ["pedido_segredo"],
            "resposta": "",
            "justificativa": "A entrada foi bloqueada pelos guardrails.",
            "fontes": [{"doc_id": "ACV-01"}],
        })
        self.assertEqual(saida["tipo"], "bloqueio")
        self.assertIsNone(saida["estado"])
        self.assertIsNone(saida["resposta"])
        self.assertEqual(saida["fontes"], [])
        self.assertIn("segredo", saida["texto"])

    def test_fundamentada_fica_pendente(self):
        saida = classificar_consulta(resultado={
            "status": "fundamentada",
            "resposta": "As aulas começam em 21/07/2026.",
            "decisao": "responder",
            "justificativa": "Consta no edital.",
            "fontes": [{"doc_id": "ACV-01"}],
        })
        self.assertEqual(saida["estado"], "pendente")
        self.assertEqual(saida["resposta"], "As aulas começam em 21/07/2026.")

    def test_proximidade_mostra_distancia_e_similaridade(self):
        from src.consulta_acervo import EXPLICACAO_DISTANCIA, proximidade_da_fonte

        self.assertEqual(
            proximidade_da_fonte({"distancia": 0.2314}),
            "Distância 0,231 · similaridade 0,769",
        )
        self.assertEqual(proximidade_da_fonte({"distancia": 0}), "Distância 0,000 · similaridade 1,000")
        # Sem distância, ou com valor que não é número, a tela não inventa um.
        for fonte in ({}, {"distancia": None}, {"distancia": "0.2"}, {"distancia": True}):
            with self.subTest(fonte=fonte):
                self.assertEqual(proximidade_da_fonte(fonte), "")
        self.assertIn("quanto menor, mais parecido", EXPLICACAO_DISTANCIA)
        self.assertIn("não garante", EXPLICACAO_DISTANCIA)


class TestFicha(unittest.TestCase):
    def test_ausencia_vira_nao_localizado(self):
        linhas = linhas_da_ficha(_solicitacao())
        self.assertEqual(dict(linhas["campos"])["Protocolo"], para_exibicao(None))
        self.assertEqual(linhas["categoria"], "matricula")

    def test_minuta_bloqueada_vai_para_revisao(self):
        class Validacao:
            minuta_bloqueada = True
            decisao = "revisar"
            motivos = ["data_incoerente: anterior à abertura"]
            solicitacao = _solicitacao()

        saida = classificar_ficha(Validacao())
        self.assertEqual(saida["estado"], "revisar")
        self.assertEqual(saida["texto"], MENSAGEM_MINUTA_BLOQUEADA)
        self.assertTrue(saida["minuta_bloqueada"])

    def test_guardrail_bloquear_nao_vira_revisao(self):
        class Validacao:
            minuta_bloqueada = True
            decisao = "rejeitada"
            motivos = ["guardrail em JSON"]
            solicitacao = None

        class Guardrail:
            decisao = "bloquear"
            motivos = ("texto_longo",)

        saida = classificar_ficha(Validacao(), Guardrail())
        self.assertEqual(saida["tipo"], "bloqueio")
        self.assertIsNone(saida["estado"])
        self.assertIsNone(saida["linhas"])
        self.assertIn("limite de caracteres", saida["texto"])

    def test_instrucao_na_entrada_continua_em_revisao(self):
        class Validacao:
            minuta_bloqueada = False
            decisao = "revisar"
            motivos = []
            solicitacao = _solicitacao()

        saida = classificar_ficha(Validacao(), {"decisao": "revisar", "motivos": ["instrucao_na_entrada"]})
        self.assertEqual(saida["estado"], "revisar")
        # O alerta da regra vai para a caixa de alertas de segurança, não para os motivos.
        self.assertIn("instrução ao sistema", saida["alertas"][0])
        self.assertEqual(saida["motivos"], [])


class TestDecisao(unittest.TestCase):
    def test_aprovacao_exige_nome_e_cargo(self):
        with self.assertRaises(ValueError):
            transicionar("pendente", "aprovar", revisor="Ana")
        self.assertEqual(
            transicionar("pendente", "aprovar", revisor="Ana", cargo="Secretaria"),
            "aprovada",
        )

    def test_rejeicao_e_revisao_exigem_justificativa(self):
        with self.assertRaises(ValueError):
            transicionar("pendente", "rejeitar", justificativa="  ")
        self.assertEqual(transicionar("pendente", "rejeitar", justificativa="Dados errados."), "rejeitada")
        self.assertEqual(transicionar("pendente", "revisar", justificativa="Conferir data."), "revisar")

    def test_estado_final_nao_muda(self):
        with self.assertRaises(ValueError):
            transicionar("aprovada", "rejeitar", justificativa="Mudei de ideia.")

    def test_revisao_prevalece_e_decisao_do_operador_fica(self):
        self.assertEqual(combinar_estado("pendente", "revisar"), "revisar")
        self.assertEqual(combinar_estado("revisar", "pendente"), "revisar")
        self.assertEqual(combinar_estado("aprovada", "revisar", travado=True), "aprovada")

    def test_retomar_so_sai_de_revisao(self):
        self.assertEqual(transicionar("revisar", "retomar"), "pendente")
        with self.assertRaises(ValueError):
            transicionar("pendente", "retomar")


class TestArquivo(unittest.TestCase):
    def test_extensao_e_tamanho_passam_pelo_guardrail(self):
        from src.interface import conferir_arquivo

        self.assertIsNone(conferir_arquivo("texto", "pedido.txt", b"Pedido de matricula."))
        self.assertEqual(conferir_arquivo("texto", "pedido.exe", b"abc"), "Essa extensão não é aceita.")
        self.assertEqual(conferir_arquivo("texto", "pedido.txt", b""), "O arquivo está vazio.")


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / "execucoes.jsonl"
        self.patch = patch.object(audit, "ARQUIVO_REGISTRO", self.log)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_nomes_novos_e_traducao_so_na_leitura(self):
        id_execucao = audit.registrar_execucao({"origem": "rf20"})
        audit.registrar_decisao(id_execucao, "pendente")
        audit.registrar_decisao(
            id_execucao, "aprovada", revisor="Ana", cargo_setor="Secretaria Escolar",
        )
        gravado = [json.loads(linha) for linha in self.log.read_text(encoding="utf-8").splitlines()]
        decisoes = [item["decisao"] for item in gravado if item["evento"] == "decisao"]
        self.assertEqual(decisoes, ["pendente", "aprovada"])
        self.assertEqual(audit.traduzir_decisao("aprovado_com_revisao"), "aprovada")
        self.assertEqual(audit.traduzir_decisao("nova_geracao"), "revisar")

    def test_decisao_final_nao_e_reescrita(self):
        id_execucao = audit.registrar_execucao({"origem": "rf20"})
        audit.registrar_decisao(id_execucao, "rejeitada", justificativa="Fora do escopo.")
        with self.assertRaises(ValueError):
            audit.registrar_decisao(id_execucao, "aprovada", revisor="Ana", cargo_setor="Secretaria")

    def test_fluxo_antigo_continua_valendo(self):
        id_execucao = audit.registrar_execucao({"origem": "desafio1"})
        audit.registrar_decisao(
            id_execucao, "aprovado", revisor="Ana", conferencia_dados_criticos=True,
        )
        with self.assertRaises(ValueError):
            audit.registrar_decisao(id_execucao, "rejeitado", justificativa=" ", revisor="Ana")


class TestMinuta(unittest.TestCase):
    def _ficha(self, **validacao):
        base = {
            "decisao": "aceita",
            "minuta_bloqueada": False,
            "motivos": [],
            "solicitacao": _solicitacao(),
        }
        base.update(validacao)
        return classificar_ficha(SimpleNamespace(**base))

    def test_sem_consulta_nao_inventa_orientacao_institucional(self):
        minuta = minuta_do_atendimento(self._ficha(), None)
        self.assertTrue(minuta["pronta"])
        self.assertIn("Ana", minuta["texto"])
        self.assertIn("ainda não foram consultadas", minuta["texto"])
        self.assertIn("apoio de IA", minuta["texto"])
        self.assertNotIn("Documentos necessários:", minuta["texto"])

    def test_resposta_fundamentada_entra_com_a_fonte(self):
        consulta = classificar_consulta(resultado={
            "status": "fundamentada",
            "decisao": "responder",
            "resposta": "As aulas começam em 21/07/2026.",
            "justificativa": "Consta no edital.",
            "fontes": [{
                "doc_id": "ACV-01",
                "versao": "Edital original",
                "pagina": 4,
                "chunk_id": "ACV-01-p4-s1-c1",
            }],
        })
        minuta = minuta_do_atendimento(self._ficha(), consulta)
        self.assertIn("21/07/2026", minuta["texto"])
        self.assertIn("ACV-01-p4-s1-c1", minuta["texto"])
        self.assertIn("apoio de IA", minuta["texto"])

    def test_sem_evidencia_nao_cria_prazo(self):
        consulta = classificar_consulta(resultado={
            "status": "sem_evidencia",
            "decisao": "revisar",
            "resposta": "Não há evidências suficientes para responder com segurança.",
            "fontes": [],
        })
        minuta = minuta_do_atendimento(self._ficha(), consulta)
        self.assertIn("Não há evidências suficientes", minuta["texto"])
        self.assertNotIn("prazo inventado", minuta["texto"].casefold())

    def test_ficha_bloqueada_nao_monta_minuta(self):
        ficha = self._ficha(decisao="rejeitada", minuta_bloqueada=True, motivos=["tipo"])
        minuta = minuta_do_atendimento(ficha, None)
        self.assertFalse(minuta["pronta"])
        self.assertEqual(minuta["texto"], MENSAGEM_MINUTA_BLOQUEADA)


class TestInclusaoDeDocumento(unittest.TestCase):
    def test_txt_entra_no_catalogo_e_duplicata_e_tipo_errado_nao(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            catalogo = {"versao_catalogo": "1.2", "documentos": [], "historico": []}
            documento = incluir_documento(
                "Texto fictício da equipe.".encode("utf-8"),
                "aviso.txt",
                "Aviso de teste",
                "Versão 1",
                catalogo,
                base,
            )
            self.assertEqual(documento["doc_id"], "ACV-01")
            self.assertEqual(documento["origem"], "equipe")
            self.assertTrue((base / documento["arquivo"]).is_file())
            self.assertEqual(catalogo["versao_catalogo"], "1.3")
            with self.assertRaises(ValueError):
                incluir_documento(
                    "Texto fictício da equipe.".encode("utf-8"),
                    "outro.txt",
                    "Outro",
                    "Versão 2",
                    catalogo,
                    base,
                )
            with self.assertRaises(ValueError):
                incluir_documento(b"nao", "nota.docx", "Nota", "1", catalogo, base)

    def test_arquivo_acima_do_limite_bloqueia_e_registra_o_motivo(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            log = base / "execucoes.jsonl"
            catalogo = {"versao_catalogo": "1.2", "documentos": [], "historico": []}
            grande = b"a" * (5 * 1024 * 1024 + 1)
            with patch.object(audit, "ARQUIVO_REGISTRO", log):
                with self.assertRaises(ValueError) as erro:
                    incluir_documento(grande, "aviso_grande.txt", "Aviso", "1", catalogo, base)

            self.assertIn("tamanho permitido", str(erro.exception))
            self.assertEqual(catalogo["documentos"], [])
            self.assertEqual(catalogo["versao_catalogo"], "1.2")
            self.assertFalse(any(base.glob("*.txt")))
            eventos = [json.loads(linha) for linha in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(eventos), 1)
            self.assertEqual(eventos[0]["evento"], "bloqueio_guardrail")
            self.assertEqual(eventos[0]["origem"], "acervo")
            self.assertEqual(eventos[0]["motivos"], ["tamanho_excedido"])
            self.assertEqual(eventos[0]["sha256_texto"], hashlib.sha256(grande).hexdigest())
            self.assertNotIn("aviso_grande", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
