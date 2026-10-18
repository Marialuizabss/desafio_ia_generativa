"""RF11 — registro estruturado das execuções e das decisões humanas.

Cada evento vira uma linha JSON em resultados/logs/execucoes.jsonl. Nada é
sobrescrito: a execução do fluxo e as decisões humanas sobre ela ficam em
linhas separadas, ligadas pelo identificador da execução.

Nenhuma credencial é gravada: campos com nome de segredo são descartados e
qualquer valor com formato de chave de API é mascarado.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_REGISTRO = BASE_DIR / "resultados" / "logs" / "execucoes.jsonl"

DECISOES = ("aprovado", "aprovado_com_revisao", "rejeitado", "nova_geracao")
APROVACOES = ("aprovado", "aprovado_com_revisao")

_CHAVE_API = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_NOME_SECRETO = re.compile(r"api_?key|secret|senha|password|authorization", re.IGNORECASE)


def _agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _limpar(valor):
    if isinstance(valor, dict):
        return {
            chave: _limpar(item)
            for chave, item in valor.items()
            if not _NOME_SECRETO.search(str(chave))
        }
    if isinstance(valor, list):
        return [_limpar(item) for item in valor]
    if isinstance(valor, str):
        return _CHAVE_API.sub("[CREDENCIAL REMOVIDA]", valor)
    return valor


def _gravar(evento: dict) -> dict:
    evento = _limpar(evento)
    ARQUIVO_REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with ARQUIVO_REGISTRO.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return evento


def registrar_execucao(dados: dict) -> str:
    """Grava uma execução do fluxo e devolve o identificador gerado."""
    id_execucao = str(uuid4())
    _gravar({"evento": "execucao", "id_execucao": id_execucao, "data_hora": _agora(), **dados})
    return id_execucao


def registrar_decisao(
    id_execucao: str,
    decisao: str,
    justificativa: str = "",
    revisor: str = "",
    conferencia_dados_criticos: bool | None = None,
    arquivo_preservado: str = "",
    arquivo_minuta: str = "",
    arquivo_pdf: str = "",
    cargo_setor: str = "",
    dados_conferidos: list[str] | None = None,
) -> dict:
    """Grava a decisão humana sobre uma execução já registrada."""
    if not id_execucao:
        raise ValueError("A execução avaliada não foi identificada.")
    if decisao not in DECISOES:
        raise ValueError(f"Decisão desconhecida: {decisao}")
    justificativa = (justificativa or "").strip()
    if decisao not in APROVACOES and not justificativa:
        raise ValueError("Informe a justificativa para rejeitar ou gerar de novo.")
    revisor = (revisor or "").strip()
    if not revisor:
        raise ValueError("Informe o nome do revisor.")
    if decisao in APROVACOES and conferencia_dados_criticos is not True:
        raise ValueError("Confira nome, protocolo e datas antes de aprovar.")

    evento = {
        "evento": "decisao",
        "id_execucao": id_execucao,
        "data_hora": _agora(),
        "decisao": decisao,
        "justificativa": justificativa,
        "revisor": revisor,
        "conferencia_dados_criticos": conferencia_dados_criticos,
    }
    preservado = (arquivo_preservado or "").strip()
    if preservado:
        evento["arquivo_preservado"] = preservado
    minuta = (arquivo_minuta or "").strip()
    if minuta:
        evento["arquivo_minuta"] = minuta
    pdf = (arquivo_pdf or "").strip()
    if pdf:
        evento["arquivo_pdf"] = pdf
    cargo = (cargo_setor or "").strip()
    if cargo:
        evento["cargo_setor"] = cargo
    if dados_conferidos:
        evento["dados_conferidos"] = list(dados_conferidos)
    return _gravar(evento)


def registrar_revisao(
    id_execucao: str,
    campos_alterados: list[str],
    arquivo_revisao: str,
    dados_conferidos: list[str] | None = None,
) -> dict:
    """Grava que os campos foram revisados. Só os nomes: os valores ficam no arquivo.

    ``dados_conferidos`` registra os dados críticos que o servidor conferiu com o
    original antes de a minuta ser montada (áudio e imagem).
    """
    if not id_execucao:
        raise ValueError("A execução revisada não foi identificada.")
    evento = {
        "evento": "revisao_campos",
        "id_execucao": id_execucao,
        "data_hora": _agora(),
        "campos_alterados": list(campos_alterados),
        "arquivo_revisao": arquivo_revisao,
    }
    if dados_conferidos is not None:
        evento["dados_conferidos"] = list(dados_conferidos)
    return _gravar(evento)


def registrar_evento(evento: str, dados: dict) -> dict:
    """Grava um evento avulso (por exemplo, a geração e a revisão da peça do RF10)."""
    return _gravar({"evento": evento, "data_hora": _agora(), **dados})


def registrar_audio_minuta(id_execucao: str, dados: dict) -> dict:
    """Grava a geração do áudio da minuta aprovada (RF07), com sucesso ou erro."""
    if not id_execucao:
        raise ValueError("A execução do áudio não foi identificada.")
    return _gravar({"evento": "audio_minuta", "id_execucao": id_execucao, "data_hora": _agora(), **dados})


def ler_registro() -> list[dict]:
    """Todos os eventos, na ordem em que foram gravados."""
    if not ARQUIVO_REGISTRO.is_file():
        return []
    eventos = []
    for linha in ARQUIVO_REGISTRO.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            eventos.append(json.loads(linha))
    return eventos


def historico(id_execucao: str) -> dict:
    """A execução e as decisões tomadas sobre ela, para reconstruir a saída."""
    eventos = [e for e in ler_registro() if e.get("id_execucao") == id_execucao]
    execucao = next((e for e in eventos if e["evento"] == "execucao"), None)
    decisoes = [e for e in eventos if e["evento"] == "decisao"]
    revisoes = [e for e in eventos if e["evento"] == "revisao_campos"]
    return {"execucao": execucao, "revisoes": revisoes, "decisoes": decisoes}


def decisoes_ligadas(id_execucao: str) -> list[dict]:
    """Decisões sobre a execução e sobre os reaproveitamentos dela, em ordem."""
    eventos = ler_registro()
    ligados = {id_execucao} | {
        e["id_execucao"]
        for e in eventos
        if e.get("evento") == "execucao" and e.get("id_execucao_origem") == id_execucao
    }
    return [e for e in eventos if e.get("evento") == "decisao" and e.get("id_execucao") in ligados]
