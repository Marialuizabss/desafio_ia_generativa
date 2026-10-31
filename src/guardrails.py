"""RF16 — validação de entrada, moderação e teto de chamadas.

A decisão é por regras, sem chamada extra ao modelo. Segredo bloqueia antes
da API. Instrução na fala do usuário segue para revisão e o atendimento
continua. O texto do acervo não é ordem: os padrões daqui são os que o RAG
usa para tirar o trecho do contexto.

O teto vale só enquanto ``com_orcamento`` está aberto (análise da solicitação
e geração do RAG). Fora dele, a chamada não é contada.
"""

import hashlib
import re
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from src.audit import registrar_evento
from src.configuracao import CONFIG

PERMITIR = "permitir"
BLOQUEAR = "bloquear"
REVISAR = "revisar"

ORIGEM_ANALISE = "analise"
ORIGEM_RAG = "rag"

MOTIVO_VAZIO = "entrada_vazia"
MOTIVO_TIPO = "tipo_nao_aceito"
MOTIVO_TAMANHO = "tamanho_excedido"
MOTIVO_TEXTO_LONGO = "texto_longo"
MOTIVO_SEGREDO = "pedido_segredo"
MOTIVO_INJECAO = "instrucao_na_entrada"
MOTIVO_SAIDA = "saida_com_segredo"
MOTIVO_TETO_CHAMADAS = "teto_chamadas"
MOTIVO_TETO_TOKENS = "teto_tokens"

EXTENSOES = {
    "texto": {".txt"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".webm"},
    "imagem": {".png", ".jpg", ".jpeg", ".webp", ".pdf"},
}

# Instruções dirigidas ao assistente dentro de um documento do acervo.
PADROES_INJECAO_DOCUMENTO = {
    "desconsiderar_regras": re.compile(r"desconsider\w* (todas )?as (regras|instrucoes)"),
    "ignorar_regras": re.compile(r"ignor\w* (todas )?as (regras|instrucoes)"),
    "ignore_previous": re.compile(r"ignore (all |any |the )?(previous|prior|above) (instructions|rules)"),
    "nota_ao_assistente": re.compile(r"nota ao assistente"),
    "pedir_segredo": re.compile(
        r"(liste|revele|mostre|informe|envie)\b.{0,80}"
        r"(variaveis? de ambiente|chave (da )?api|openai_api_key|arquivo \.env)"
    ),
    "envio_automatico": re.compile(r"envie a resposta automaticamente"),
}

_PADROES_SEGREDO = {
    "arquivo_env": re.compile(r"arquivo\s+\.env|(?<![\w.])\.env\b"),
    "chave_api": re.compile(r"openai_api_key|chave (da |de )?api"),
    "variaveis_ambiente": re.compile(r"variaveis de ambiente"),
}

_PADROES_INJECAO_USUARIO = {
    "ignorar_instrucoes": re.compile(
        r"ignor\w* (todas |all )?(as )?(instrucoes|regras|previous|prior)"
    ),
    "ignore_previous": re.compile(
        r"ignore (all |any |the )?(previous|prior|above) (instructions|rules)"
    ),
    "atualizacao_de_instrucoes": re.compile(r"atualizacao das instrucoes do sistema"),
    "quebra_delimitador": re.compile(r"</\s*solicitacao\s*>"),
}

_CHAVE_API = re.compile(r"sk-[A-Za-z0-9_-]{8,}")


class OrcamentoEstourado(Exception):
    """A próxima chamada passaria do teto de chamadas ou de tokens."""

    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


@dataclass(frozen=True)
class DecisaoGuardrail:
    """Decisão da moderação. ``motivos`` são códigos, nunca o trecho casado."""

    decisao: str
    motivos: tuple[str, ...] = ()
    alerta: bool = False


@dataclass
class _Orcamento:
    origem: str
    max_chamadas: int
    max_tokens: int
    chamadas: int = 0
    tokens: int = 0


_orcamento_atual: ContextVar[_Orcamento | None] = ContextVar("orcamento_guardrail", default=None)


def _sem_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", re.sub(r"\s+", " ", texto or "").casefold())
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))


def _limites() -> dict:
    return CONFIG["guardrails"]


def _parametros() -> dict:
    return CONFIG["parametros"]


def instrucoes_no_documento(texto: str) -> list[str]:
    """Nomes dos padrões de instrução ao assistente encontrados num trecho do acervo."""

    normalizado = _sem_acentos(texto)
    return [
        nome for nome, padrao in PADROES_INJECAO_DOCUMENTO.items() if padrao.search(normalizado)
    ]


def avaliar_entrada(texto, origem: str) -> DecisaoGuardrail:
    """Classifica o texto do usuário: permitir, bloquear ou revisar.

    Segredo ganha da injeção. ``origem`` é ``analise`` ou ``rag`` e só
    identifica o fluxo; a regra é a mesma nos dois.
    """

    if origem not in (ORIGEM_ANALISE, ORIGEM_RAG):
        raise ValueError(f"Origem desconhecida: {origem}")
    if not isinstance(texto, str):
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TIPO,), True)
    if not texto.strip():
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_VAZIO,), True)
    if len(texto) > int(_parametros()["limite_texto_caracteres"]):
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TEXTO_LONGO,), True)

    normalizado = _sem_acentos(texto)
    if any(padrao.search(normalizado) for padrao in _PADROES_SEGREDO.values()):
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_SEGREDO,), True)
    if any(padrao.search(normalizado) for padrao in _PADROES_INJECAO_USUARIO.values()):
        return DecisaoGuardrail(REVISAR, (MOTIVO_INJECAO,), True)
    return DecisaoGuardrail(PERMITIR)


def validar_material(nome_arquivo: str, tamanho_bytes: int, modalidade: str) -> DecisaoGuardrail:
    """Confere extensão e tamanho de um arquivo antes de ele entrar no fluxo.

    Os limites são os de ``config.json`` (texto, áudio e imagem).
    """

    if modalidade not in EXTENSOES:
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TIPO,), True)
    if not isinstance(tamanho_bytes, int) or isinstance(tamanho_bytes, bool):
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TIPO,), True)
    if tamanho_bytes <= 0:
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_VAZIO,), True)

    sufixo = ""
    if isinstance(nome_arquivo, str) and "." in nome_arquivo:
        sufixo = "." + nome_arquivo.rsplit(".", 1)[-1].casefold()
    if sufixo not in EXTENSOES[modalidade]:
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TIPO,), True)

    chave = {
        "texto": "limite_arquivo_texto_mb",
        "audio": "limite_audio_mb",
        "imagem": "limite_imagem_mb",
    }[modalidade]
    limite = int(_parametros()[chave]) * 1024 * 1024
    if tamanho_bytes > limite:
        return DecisaoGuardrail(BLOQUEAR, (MOTIVO_TAMANHO,), True)
    return DecisaoGuardrail(PERMITIR)


def sanear_saida(texto: str) -> tuple[str, DecisaoGuardrail | None]:
    """Retira da resposta um valor no formato de chave de API.

    Se houver, o texto não volta e a decisão é bloquear. O motivo é um código.
    """

    if isinstance(texto, str) and _CHAVE_API.search(texto):
        return "", DecisaoGuardrail(BLOQUEAR, (MOTIVO_SAIDA,), True)
    return texto, None


def registrar_bloqueio(decisao: DecisaoGuardrail, origem: str, texto: str) -> dict:
    """Grava o bloqueio: códigos, origem e hash do texto. Sem o trecho e sem segredo."""

    bruto = texto if isinstance(texto, str) else ""
    return registrar_evento("bloqueio_guardrail", {
        "origem": origem,
        "decisao": BLOQUEAR,
        "motivos": list(decisao.motivos),
        "sha256_texto": hashlib.sha256(bruto.encode("utf-8")).hexdigest(),
    })


@contextmanager
def com_orcamento(origem: str, max_chamadas: int | None = None, max_tokens: int | None = None):
    """Abre o teto de um atendimento. Vale para as chamadas feitas dentro do bloco."""

    limites = _limites()
    if origem == ORIGEM_ANALISE:
        chamadas = limites["max_chamadas_analise"] if max_chamadas is None else max_chamadas
        tokens = limites["teto_analise"] if max_tokens is None else max_tokens
    elif origem == ORIGEM_RAG:
        chamadas = limites["max_chamadas_rag"] if max_chamadas is None else max_chamadas
        tokens = limites["teto_rag"] if max_tokens is None else max_tokens
    else:
        raise ValueError(f"Origem desconhecida: {origem}")

    estado = _Orcamento(origem, int(chamadas), int(tokens))
    marca = _orcamento_atual.set(estado)
    try:
        yield estado
    finally:
        _orcamento_atual.reset(marca)


def reservar_chamada() -> None:
    """Conta uma chamada lógica antes de falar com o provedor.

    Sem orçamento aberto, não faz nada. No limite, levanta ``OrcamentoEstourado``
    e a chamada não deve acontecer.
    """

    estado = _orcamento_atual.get()
    if estado is None:
        return
    if estado.chamadas >= estado.max_chamadas:
        raise OrcamentoEstourado(MOTIVO_TETO_CHAMADAS)
    if estado.tokens >= estado.max_tokens:
        raise OrcamentoEstourado(MOTIVO_TETO_TOKENS)
    estado.chamadas += 1


def contabilizar_tokens(tokens: int | None) -> None:
    """Soma os tokens informados pelo provedor. Ausência (resposta simulada) não soma."""

    estado = _orcamento_atual.get()
    if estado is None or not tokens:
        return
    estado.tokens += int(tokens)
