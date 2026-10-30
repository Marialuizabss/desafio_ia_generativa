"""Painel das avaliações (RF22 e T13).

Os totais saem de ``agregar_painel``. A confiança fica no registro e não entra
na conta. Sem classificação, ou com filtro que não acha nada, o denominador é 0
e a mensagem é "sem dados".
"""

import json
from pathlib import Path

from src.sentimentos import POLARIDADES, agregar_painel

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_METRICAS = BASE_DIR / "resultados" / "metricas" / "rf22"
AVALIACOES = BASE_DIR / "dados" / "avaliacoes" / "avaliacoes.json"
AVALIACOES_DUPLICADAS = BASE_DIR / "dados" / "avaliacoes" / "avaliacoes_duplicadas.json"

CONJUNTOS = {
    "oficiais": AVALIACOES,
    "duplicadas": AVALIACOES_DUPLICADAS,
}


def carregar_ultima_execucao(pasta: Path = PASTA_METRICAS) -> tuple[dict | None, list[dict]]:
    """Prefere a execução real mais recente. A simulada só entra se não houver real."""
    if not pasta.is_dir():
        return None, []
    reais = []
    simuladas = []
    for caminho in pasta.iterdir():
        resumo_path = caminho / "resumo.json"
        if not caminho.is_dir() or not resumo_path.is_file():
            continue
        if caminho.name.endswith("_simulado"):
            simuladas.append(caminho)
        else:
            reais.append(caminho)
    escolhidas = sorted(reais or simuladas)
    if not escolhidas:
        return None, []
    pasta_escolhida = escolhidas[-1]
    resumo = json.loads((pasta_escolhida / "resumo.json").read_text(encoding="utf-8"))
    registros = []
    for arquivo in sorted(pasta_escolhida.glob("AV*.json")):
        registros.append(json.loads(arquivo.read_text(encoding="utf-8")))
    resumo["pasta"] = pasta_escolhida.name
    return resumo, registros


def ler_avaliacoes(conjunto: str = "oficiais") -> list[dict]:
    caminho = CONJUNTOS.get(conjunto)
    if caminho is None or not caminho.is_file():
        return []
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return list(dados.get("avaliacoes") or [])


def montar_visao(
    classificacoes: list[dict],
    avaliacoes: list[dict],
    filtro: dict | None = None,
) -> dict:
    """Junta canal e data da avaliação com a polaridade classificada e agrega."""
    por_id = {item["id"]: item for item in classificacoes}
    registros = []
    for avaliacao in avaliacoes:
        classe = por_id.get(avaliacao["id"], {})
        polaridade = classe.get("polaridade")
        rejeitada = bool(classe.get("rejeitada")) or polaridade not in POLARIDADES
        registros.append({
            "id": avaliacao["id"],
            "canal": avaliacao.get("canal"),
            "data": avaliacao.get("data"),
            "polaridade": None if rejeitada else polaridade,
            "revisao": bool(classe.get("revisao")),
            "rejeitada": rejeitada,
            "confianca": classe.get("confianca"),
        })
    return agregar_painel(registros, filtro)
