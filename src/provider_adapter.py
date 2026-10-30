"""Adaptador de provedor de geração para o Desafio 02 (RF21).

A recuperação (índice vetorial) não depende deste módulo: trocar a configuração
de geração não reconstrói o índice. Cada configuração do `config.json`
(`adaptador_llm.configuracoes`) escolhe o provedor, o modelo e os parâmetros.

Provedores:
  - ``openai``: chamada real à API (Responses).
  - ``simulado``: não consulta nenhum modelo. Devolve sempre uma abstenção
    ("sem evidência") e se identifica como simulado na auditoria. Serve para
    demonstrar a troca de geração e a tolerância a falhas; **não** tem
    qualidade equivalente à de um modelo real.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from openai import OpenAI, OpenAIError

from src.configuracao import CONFIG
from src.llm_client import _custo_estimado, _mensagem_de_falha

PROVEDOR_OPENAI = "openai"
PROVEDOR_SIMULADO = "simulado"

RESPOSTA_SIMULADA = json.dumps(
    {
        "status": "sem_evidencia",
        "resposta": "",
        "justificativa": (
            "Resposta simulada: nenhum modelo foi consultado. "
            "O caso deve ser encaminhado à revisão humana."
        ),
        "citacoes": [],
        "chunk_ids": [],
    },
    ensure_ascii=False,
)


class ErroProvedor(ValueError):
    """Falha na chamada ao provedor, com a auditoria da tentativa.

    É um ``ValueError`` para manter compatibilidade com quem já tratava a
    mensagem de falha; ``auditoria`` traz status, erro e tempo medidos.
    """

    def __init__(self, mensagem: str, auditoria: dict):
        super().__init__(mensagem)
        self.auditoria = auditoria


@dataclass(frozen=True)
class ConfiguracaoLLM:
    """Representa uma configuração de execução do modelo."""

    provedor: str
    modelo: str
    temperatura: float | None
    timeout_segundos: float
    max_retries: int
    max_tokens_saida: int | None = None


def carregar_configuracao_llm(nome: str = "principal") -> ConfiguracaoLLM:
    """Carrega uma configuração do adaptador definida no config.json."""

    adaptador = CONFIG["adaptador_llm"]
    configuracoes = adaptador["configuracoes"]

    if nome not in configuracoes:
        raise ValueError(f"Configuração LLM desconhecida: {nome}")

    dados = configuracoes[nome]
    maximo = dados.get("max_tokens_saida")

    return ConfiguracaoLLM(
        provedor=dados.get("provedor", adaptador["provedor"]),
        modelo=dados["modelo"],
        temperatura=dados.get("temperatura"),
        timeout_segundos=float(adaptador["timeout_segundos"]),
        max_retries=int(adaptador["max_retries"]),
        max_tokens_saida=int(maximo) if maximo is not None else None,
    )


def _agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _chamar_openai(config: ConfiguracaoLLM, instrucoes: str, entrada: str):
    cliente = OpenAI(
        timeout=config.timeout_segundos,
        max_retries=config.max_retries,
    )

    parametros = {
        "model": config.modelo,
        "instructions": instrucoes,
        "input": entrada,
        "store": False,
    }

    if config.temperatura is not None:
        parametros["temperature"] = config.temperatura

    if config.max_tokens_saida is not None:
        parametros["max_output_tokens"] = config.max_tokens_saida

    try:
        resposta = cliente.responses.create(**parametros)
    except OpenAIError as erro:
        raise ValueError(_mensagem_de_falha(erro)) from erro

    texto = (resposta.output_text or "").strip()

    if not texto:
        raise ValueError("O modelo retornou uma resposta vazia.")

    uso = getattr(resposta, "usage", None)

    return texto, {
        "tokens_entrada": getattr(uso, "input_tokens", None),
        "tokens_saida": getattr(uso, "output_tokens", None),
        "tokens_total": getattr(uso, "total_tokens", None),
    }


def _chamar_simulado(config: ConfiguracaoLLM, instrucoes: str, entrada: str):
    return RESPOSTA_SIMULADA, {
        "tokens_entrada": None,
        "tokens_saida": None,
        "tokens_total": None,
    }


PROVEDORES = {
    PROVEDOR_OPENAI: _chamar_openai,
    PROVEDOR_SIMULADO: _chamar_simulado,
}


def _montar_auditoria(config, nome, inicio, duracao, status, uso=None, erro=None):
    uso = uso or {}
    simulado = config.provedor == PROVEDOR_SIMULADO

    custo, _ = _custo_estimado(
        config.modelo, uso.get("tokens_entrada"), uso.get("tokens_saida")
    )

    auditoria = {
        "provedor": config.provedor,
        "modelo": config.modelo,
        "configuracao": nome,
        "simulado": simulado,
        "temperatura": config.temperatura,
        "inicio": inicio,
        "fim": _agora(),
        "tempo_resposta_segundos": duracao,
        "tokens_entrada": uso.get("tokens_entrada"),
        "tokens_saida": uso.get("tokens_saida"),
        "tokens_total": uso.get("tokens_total"),
        "custo_estimado_usd": custo,
        "status": status,
        "erro": erro,
    }

    if uso.get("tokens_total") is None:
        auditoria["metricas_indisponiveis"] = (
            "Resposta simulada: sem consumo de tokens ou custo."
            if simulado
            else "O provedor não informou o consumo de tokens; só o tempo medido é válido."
        )

    return auditoria


def consultar_llm(
    instrucoes: str,
    entrada: str,
    nome_configuracao: str = "principal",
) -> tuple[str, dict]:
    """Consulta o modelo e retorna a resposta e os metadados de auditoria.

    Em caso de falha do provedor, levanta ``ErroProvedor`` com a auditoria da
    tentativa (status ``erro``, mensagem sem credenciais e tempo medido).
    """

    config = carregar_configuracao_llm(nome_configuracao)

    if config.provedor not in PROVEDORES:
        raise ValueError(f"Provedor não suportado: {config.provedor}")

    if not instrucoes.strip() or not entrada.strip():
        raise ValueError("Instruções e entrada não podem estar vazias.")

    inicio = _agora()
    marca = perf_counter()

    try:
        texto, uso = PROVEDORES[config.provedor](config, instrucoes, entrada)
    except Exception as erro:
        duracao = round(perf_counter() - marca, 3)

        if isinstance(erro, ValueError):
            mensagem = str(erro)
        else:
            # Só o tipo do erro: a mensagem original pode conter dados da requisição.
            mensagem = f"Falha inesperada no provedor ({type(erro).__name__})."

        raise ErroProvedor(
            mensagem,
            _montar_auditoria(config, nome_configuracao, inicio, duracao,
                              "erro", erro=mensagem),
        ) from erro

    duracao = round(perf_counter() - marca, 3)

    return texto, _montar_auditoria(
        config, nome_configuracao, inicio, duracao, "sucesso", uso=uso
    )
