"""Traduz falhas da API da OpenAI em mensagens claras em português (RF04).

As mensagens nunca citam a chave nem trechos dela: podem ser mostradas na interface
e gravadas no registro sem expor credenciais.
"""

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)


def mensagem_de_falha(erro: Exception, servico: str) -> str:
    """Mensagem em português para a falha ao usar `servico` (ex.: "a transcrição do áudio")."""
    if isinstance(erro, (AuthenticationError, PermissionDeniedError)):
        return (
            f"Não foi possível fazer {servico}: a chave de acesso não foi aceita. "
            "Confira o arquivo .env."
        )
    if isinstance(erro, RateLimitError):
        return (
            f"Não foi possível fazer {servico}: o limite de uso da conta foi atingido. "
            "Aguarde um pouco e tente de novo."
        )
    if isinstance(erro, APITimeoutError):
        return (
            f"Não foi possível fazer {servico}: o serviço demorou demais para responder. "
            "Tente de novo."
        )
    if isinstance(erro, APIConnectionError):
        return (
            f"Não foi possível fazer {servico}: falha de conexão com o serviço. "
            "Confira a internet e tente de novo."
        )
    if isinstance(erro, NotFoundError):
        return (
            f"Não foi possível fazer {servico}: o modelo configurado não está disponível "
            "para esta conta. Confira o arquivo config.json."
        )
    if isinstance(erro, BadRequestError):
        return (
            f"Não foi possível fazer {servico}: o serviço recusou o arquivo ou o texto enviado. "
            "Confira o formato e o tamanho."
        )
    if isinstance(erro, APIStatusError):
        return (
            f"Não foi possível fazer {servico}: o serviço respondeu com erro "
            f"({erro.status_code}). Tente de novo em instantes."
        )
    if isinstance(erro, OpenAIError):
        texto = str(erro).casefold()
        if "api_key" in texto or "credential" in texto:
            return (
                f"Não foi possível fazer {servico}: a chave de acesso não foi encontrada. "
                "Confira o arquivo .env."
            )
    return f"Não foi possível fazer {servico}. Tente de novo."