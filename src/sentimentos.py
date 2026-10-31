"""RF22 — polaridade da avaliação de atendimento e painel.

O modelo propõe a situação e a polaridade. As regras de mensagem mista, ironia, falta de
contexto e instrução no texto são aplicadas aqui, depois da validação. A confiança fica
registrada como estimativa não calibrada: não escolhe rótulo e não entra no percentual.

Este módulo não decide sozinho qual provedor chamar. ``classificar_avaliacao`` recebe o
chamador; a execução real usa ``consultar_llm`` (RF21).
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_PROMPT = BASE_DIR / "prompts" / "desafio2" / "sentimento_v1.md"
CAMINHO_GABARITO = BASE_DIR / "dados" / "gabaritos" / "gabarito_avaliacoes.json"

VERSAO_ESQUEMA = "1.0"
ROTULO_CONFIANCA = "estimativa não calibrada"
POLARIDADES = ("positiva", "negativa", "neutra", "indeterminada")
POLARIDADES_CLARAS = ("positiva", "negativa", "neutra")
SITUACOES = ("clara", "mista", "ironia_comprovada", "ironia_possivel", "falta_de_contexto")

# A barra invertida depois de "<" impede que o texto abra ou feche a delimitação (como no RF03)
_MARCA_AVALIACAO = re.compile(r"<(?=\s*/?\s*avalia[cç][aã]o\b)", re.IGNORECASE)
_INSTRUCAO = re.compile(
    r"ignore as regras|classifique esta avalia[cç][aã]o como",
    re.IGNORECASE,
)

MOTIVO_DA_SITUACAO = {
    "mista": "Mensagem mista, sem lado predominante.",
    "ironia_comprovada": "Ironia desmentida por um fato do próprio texto.",
    "ironia_possivel": "Ironia possível, não comprovável pelo texto.",
    "falta_de_contexto": "Falta contexto no texto para definir a polaridade.",
}

CATEGORIA_DO_ERRO = {
    "extra_forbidden": "chave_extra",
    "missing": "campo_obrigatorio_ausente",
    "literal_error": "valor_fora_do_dominio",
}


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SaidaSentimento(_Modelo):
    """O que o modelo devolve. A polaridade final pode ser outra, pelas regras do código."""

    situacao: Literal["clara", "mista", "ironia_comprovada", "ironia_possivel", "falta_de_contexto"]
    polaridade: Literal["positiva", "negativa", "neutra", "indeterminada"]
    justificativa: str
    confianca: float | int
    contem_instrucao: bool

    @field_validator("justificativa")
    @classmethod
    def justificativa_preenchida(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("A justificativa não pode ser vazia.")
        return valor

    @field_validator("confianca")
    @classmethod
    def confianca_entre_zero_e_um(cls, valor: float | int) -> float:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError("A confiança precisa ser um número de 0 a 1.")
        numero = float(valor)
        if not 0 <= numero <= 1:
            raise ValueError("A confiança precisa estar entre 0 e 1.")
        return numero


@dataclass
class ErroValidacao:
    camada: Literal["sintaxe", "esquema", "regra"]
    categoria: str
    campo: str
    mensagem: str


@dataclass
class Classificacao:
    polaridade: str | None
    situacao: str | None
    justificativa: str
    confianca: float | None
    rotulo_confianca: str
    contem_instrucao: bool
    revisao: bool
    motivos_revisao: list[str]
    rejeitada: bool
    termo_proibido: str | None
    versao_prompt: str
    arquivo_prompt: str
    chamadas: list[dict] = field(default_factory=list)
    tentativas: list[dict] = field(default_factory=list)

    def para_dict(self) -> dict:
        return {
            "polaridade": self.polaridade,
            "situacao": self.situacao,
            "justificativa": self.justificativa,
            "confianca": self.confianca,
            "rotulo_confianca": self.rotulo_confianca,
            "contem_instrucao": self.contem_instrucao,
            "revisao": self.revisao,
            "motivos_revisao": list(self.motivos_revisao),
            "rejeitada": self.rejeitada,
            "termo_proibido": self.termo_proibido,
            "versao_esquema": VERSAO_ESQUEMA,
            "versao_prompt": self.versao_prompt,
            "arquivo_prompt": self.arquivo_prompt,
            "chamadas": self.chamadas,
            "tentativas": self.tentativas,
        }


def carregar_prompt() -> str:
    return CAMINHO_PROMPT.read_text(encoding="utf-8").strip()


def arquivo_do_prompt() -> str:
    return CAMINHO_PROMPT.name


def versao_do_prompt() -> str:
    """Muda quando muda o prompt ou o esquema da saída."""
    conteudo = carregar_prompt() + json.dumps(SaidaSentimento.model_json_schema(), sort_keys=True)
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:12]


def termos_proibidos(caminho: Path | None = None) -> list[str]:
    """Radicais que a justificativa não pode atribuir a quem escreveu (gabarito, seção 6)."""
    dados = json.loads((caminho or CAMINHO_GABARITO).read_text(encoding="utf-8"))
    return list(dados["termos_proibidos_na_justificativa"])


def embrulhar_avaliacao(texto: str, identificador: str) -> str:
    corpo = _MARCA_AVALIACAO.sub(r"<\\", texto)
    origem = (
        identificador.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
    )
    return f'<avaliacao id="{origem}">\n{corpo}\n</avaliacao>'


def texto_tem_instrucao(texto: str) -> bool:
    return _INSTRUCAO.search(texto) is not None


def montar_entrada(texto: str, identificador: str, erros: list[ErroValidacao] | None = None) -> str:
    entrada = embrulhar_avaliacao(texto, identificador)
    if erros:
        lista = "\n".join(
            f"- {erro.categoria} em {erro.campo or 'JSON'}: {erro.mensagem}" for erro in erros
        )
        entrada += (
            "\n\n# Correção\nA resposta anterior foi rejeitada. "
            f"Corrija estes erros e responda de novo só com o JSON:\n{lista}"
        )
    return entrada


def _termo_proibido(justificativa: str, termos: list[str]) -> str | None:
    texto = justificativa.casefold()
    for termo in termos:
        if termo.casefold() in texto:
            return termo
    return None


def validar_estrutura(bruto: str) -> tuple[SaidaSentimento | None, list[ErroValidacao]]:
    try:
        dados = json.loads(bruto)
    except (json.JSONDecodeError, TypeError) as erro:
        return None, [ErroValidacao("sintaxe", "json_invalido", "", f"Não é JSON: {erro}")]
    if not isinstance(dados, dict):
        return None, [ErroValidacao("sintaxe", "json_invalido", "", "O JSON precisa ser um objeto.")]
    try:
        return SaidaSentimento.model_validate_json(json.dumps(dados)), []
    except ValidationError as erro:
        return None, [
            ErroValidacao(
                "esquema",
                CATEGORIA_DO_ERRO.get(detalhe["type"], "tipo_incorreto"),
                ".".join(str(parte) for parte in detalhe["loc"]),
                detalhe["msg"],
            )
            for detalhe in erro.errors()
        ]


def erros_de_conteudo(saida: SaidaSentimento, termos: list[str]) -> list[ErroValidacao]:
    """O que ainda admite uma correção: justificativa proibida ou polaridade incompatível."""
    erros = []
    termo = _termo_proibido(saida.justificativa, termos)
    if termo:
        erros.append(ErroValidacao(
            "regra", "justificativa_proibida", "justificativa",
            f"A justificativa contém o radical proibido '{termo}'.",
        ))
    if saida.situacao == "clara" and saida.polaridade not in POLARIDADES_CLARAS:
        erros.append(ErroValidacao(
            "regra", "polaridade_incompativel", "polaridade",
            "Situação clara exige polaridade positiva, negativa ou neutra.",
        ))
    return erros


def aplicar_regras(saida: SaidaSentimento, texto: str, termos: list[str]) -> dict:
    """Polaridade e revisão finais. A proposta do modelo não prevalece sobre a tabela do RF22."""
    termo = _termo_proibido(saida.justificativa, termos)
    contem = bool(saida.contem_instrucao) or texto_tem_instrucao(texto)
    motivos = []

    if saida.situacao == "clara" and saida.polaridade in POLARIDADES_CLARAS:
        polaridade = saida.polaridade
    elif saida.situacao == "ironia_comprovada":
        polaridade = "negativa"
        motivos.append(MOTIVO_DA_SITUACAO["ironia_comprovada"])
    elif saida.situacao == "clara":
        polaridade = "indeterminada"
        motivos.append("A situação clara veio com polaridade indeterminada.")
    else:
        polaridade = "indeterminada"
        motivos.append(MOTIVO_DA_SITUACAO[saida.situacao])

    if contem:
        motivos.append("O texto traz uma instrução ao classificador.")
    if termo:
        motivos.append(f"Justificativa com termo proibido: {termo}.")

    return {
        "polaridade": polaridade,
        "situacao": saida.situacao,
        "justificativa": saida.justificativa,
        "confianca": float(saida.confianca),
        "contem_instrucao": contem,
        "revisao": bool(motivos),
        "motivos_revisao": motivos,
        "termo_proibido": termo,
    }


def _chamar_ate_uma_correcao(chamar, instrucoes, texto, identificador, termos):
    """No máximo duas chamadas. A segunda só acontece se a primeira saiu inválida."""
    chamadas: list[dict] = []
    tentativas: list[dict] = []
    erros: list[ErroValidacao] = []
    saida: SaidaSentimento | None = None
    for numero in (1, 2):
        bruto, auditoria = chamar(instrucoes, montar_entrada(texto, identificador, erros or None))
        chamadas.append(auditoria)
        candidato, erros_estrutura = validar_estrutura(bruto)
        if candidato is not None:
            saida = candidato
        erros_regra = erros_de_conteudo(candidato, termos) if candidato is not None else []
        erros = erros_estrutura or erros_regra
        tentativas.append({
            "numero": numero,
            "erros": [
                {"camada": erro.camada, "categoria": erro.categoria, "campo": erro.campo, "mensagem": erro.mensagem}
                for erro in erros
            ],
        })
        if not erros:
            break
    return saida, chamadas, tentativas, erros


def classificar_avaliacao(
    texto: str,
    identificador: str,
    chamar: Callable[[str, str], tuple[str, dict]] | None = None,
    termos: list[str] | None = None,
) -> Classificacao:
    """Delimita o texto, chama o modelo e aplica as regras. No máximo uma correção.

    ``chamar(instrucoes, entrada)`` devolve (texto, dados da chamada). Sem ``chamar``,
    usa a configuração ``principal`` do adaptador. As chamadas entram no teto da
    análise (duas chamadas e o limite de tokens): a segunda é a correção.
    """

    from src.guardrails import ORIGEM_ANALISE, OrcamentoEstourado, com_orcamento

    chamar = chamar or chamar_principal
    termos = termos_proibidos() if termos is None else termos
    instrucoes = carregar_prompt()
    chamadas: list[dict] = []
    tentativas: list[dict] = []
    erros: list[ErroValidacao] = []
    saida: SaidaSentimento | None = None

    try:
        with com_orcamento(ORIGEM_ANALISE):
            saida, chamadas, tentativas, erros = _chamar_ate_uma_correcao(
                chamar, instrucoes, texto, identificador, termos,
            )
    except OrcamentoEstourado as erro:
        return Classificacao(
            polaridade=None, situacao=None, justificativa="", confianca=None,
            contem_instrucao=texto_tem_instrucao(texto), revisao=True,
            motivos_revisao=[f"Teto do atendimento: {erro.motivo}."],
            rejeitada=True, termo_proibido=None,
            versao_prompt=versao_do_prompt(), arquivo_prompt=arquivo_do_prompt(),
            chamadas=chamadas, tentativas=tentativas, rotulo_confianca=ROTULO_CONFIANCA,
        )

    base = {
        "versao_prompt": versao_do_prompt(),
        "arquivo_prompt": arquivo_do_prompt(),
        "chamadas": chamadas,
        "tentativas": tentativas,
        "rotulo_confianca": ROTULO_CONFIANCA,
    }
    if saida is None:
        return Classificacao(
            polaridade=None, situacao=None, justificativa="", confianca=None,
            contem_instrucao=texto_tem_instrucao(texto), revisao=True,
            motivos_revisao=["Saída rejeitada depois de uma correção."],
            rejeitada=True, termo_proibido=None, **base,
        )

    decisao = aplicar_regras(saida, texto, termos)
    if erros:
        decisao["revisao"] = True
    return Classificacao(rejeitada=False, **decisao, **base)


def chamar_principal(instrucoes: str, entrada: str) -> tuple[str, dict]:
    """Configuração real do adaptador. A simulada do RAG não classifica sentimento."""
    from src.provider_adapter import consultar_llm
    return consultar_llm(instrucoes, entrada, nome_configuracao="principal")


def situacao_de_gabarito(item: dict) -> str:
    """Situação que faz as regras reproduzirem o rótulo esperado, na execução simulada."""
    if item["grupo"] != "ambigua_mista":
        return "clara"
    justificativa = item["justificativa"].casefold()
    if "falta de contexto" in justificativa:
        return "falta_de_contexto"
    if item["polaridade_esperada"] == "negativa" and "ironia" in justificativa:
        return "ironia_comprovada"
    if "não comprov" in justificativa or "nao comprov" in justificativa:
        return "ironia_possivel"
    return "mista"


def saida_de_gabarito(item: dict) -> dict:
    """JSON que o modo simulado devolve no lugar do modelo. A confiança é fixa de propósito."""
    return {
        "situacao": situacao_de_gabarito(item),
        "polaridade": item["polaridade_esperada"],
        "justificativa": item["justificativa"],
        "confianca": 0.5,
        "contem_instrucao": item["contem_instrucao"],
    }


def fracao(numerador: int, denominador: int) -> dict:
    """Numerador e denominador sempre visíveis; sem denominador, o percentual fica vazio."""
    return {
        "numerador": numerador,
        "denominador": denominador,
        "percentual": round(100 * numerador / denominador, 1) if denominador else None,
    }


def agregar_painel(registros: list[dict], filtro: dict | None = None) -> dict:
    """Totais pelo código. A confiança, se vier no registro, não entra na conta.

    Duplicata é o mesmo ``id``: conta uma vez e a repetição fica em ``duplicados``.
    Classificação rejeitada não entra nos totais de polaridade. Denominador 0 não divide.
    """

    selecionados = [
        registro for registro in registros
        if not filtro or all(registro.get(chave) == valor for chave, valor in filtro.items())
    ]
    vistos: set[str] = set()
    unicos: list[dict] = []
    duplicados: list[str] = []
    for registro in selecionados:
        if registro["id"] in vistos:
            duplicados.append(registro["id"])
            continue
        vistos.add(registro["id"])
        unicos.append(registro)

    classificados = [registro for registro in unicos if not registro.get("rejeitada")]
    rejeitadas = len(unicos) - len(classificados)
    totais = {polaridade: 0 for polaridade in POLARIDADES}
    for registro in classificados:
        totais[registro["polaridade"]] += 1
    denominador = len(classificados)
    return {
        "registros": len(selecionados),
        "unicos": len(unicos),
        "duplicados": duplicados,
        "totais": totais,
        "fracoes": {
            polaridade: None if denominador == 0 else f"{totais[polaridade]}/{denominador}"
            for polaridade in POLARIDADES
        },
        "percentuais": {
            polaridade: None if denominador == 0 else round(100 * totais[polaridade] / denominador, 1)
            for polaridade in POLARIDADES
        },
        "denominador": denominador,
        "rejeitadas": rejeitadas,
        "revisao": sum(bool(registro.get("revisao")) for registro in unicos),
        "mensagem": None if denominador else "sem dados",
    }
