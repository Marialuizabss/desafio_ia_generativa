
"""Adaptador de provedor de LLM para o Desafio 02 (RF21)."""

from dataclasses import dataclass
from src.configuracao import CONFIG
from time import perf_counter
from openai import OpenAI, OpenAIError
from src.llm_client import _custo_estimado, _mensagem_de_falha

@dataclass(frozen=True)
class ConfiguracaoLLM:
    """Representa uma configuração de execução do modelo."""

    provedor: str
    modelo: str
    temperatura: float | None
    timeout_segundos: float
    max_retries: int


def carregar_configuracao_llm(nome: str = "principal") -> ConfiguracaoLLM:
    """Carrega uma configuração do adaptador definida no config.json."""

    adaptador = CONFIG["adaptador_llm"]
    configuracoes = adaptador["configuracoes"]

    if nome not in configuracoes:
        raise ValueError(f"Configuração LLM desconhecida: {nome}")

    dados = configuracoes[nome]

    return ConfiguracaoLLM(
        provedor=adaptador["provedor"],
        modelo=dados["modelo"],
        temperatura=dados.get("temperatura"),
        timeout_segundos=float(adaptador["timeout_segundos"]),
        max_retries=int(adaptador["max_retries"]),
    )

def consultar_llm(instrucoes: str,entrada: str,nome_configuracao: str = "principal",) -> tuple[str, dict]:
    """Consulta o modelo e retorna a resposta e os metadados de auditoria."""

    config = carregar_configuracao_llm(nome_configuracao)

    if config.provedor != "openai":
        raise ValueError(f"Provedor não suportado: {config.provedor}")

    if not instrucoes.strip() or not entrada.strip():
        raise ValueError("Instruções e entrada não podem estar vazias.")

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

    inicio = perf_counter()

    try:
        resposta = cliente.responses.create(**parametros)
    except OpenAIError as erro:
        raise ValueError(_mensagem_de_falha(erro)) from erro

    duracao = round(perf_counter() - inicio, 3)

    texto = (resposta.output_text or "").strip()

    if not texto:
        raise ValueError("O modelo retornou uma resposta vazia.")

    uso = getattr(resposta, "usage", None)

    tokens_entrada = getattr(uso, "input_tokens", None)
    tokens_saida = getattr(uso, "output_tokens", None)

    custo_estimado, _ = _custo_estimado(
        config.modelo,
        tokens_entrada,
        tokens_saida,
    )

    auditoria = {
        "provedor": config.provedor,
        "modelo": config.modelo,
        "configuracao": nome_configuracao,
        "temperatura": config.temperatura,
        "tempo_resposta_segundos": duracao,
        "tokens_entrada": getattr(uso, "input_tokens", None),
        "tokens_saida": getattr(uso, "output_tokens", None),
        "tokens_total": getattr(uso, "total_tokens", None),
        "custo_estimado_usd": custo_estimado,
        "status": "sucesso",
    }

    return texto, auditoria

