"""Reavalia os elementos esperados de resultados já gravados, com o gabarito atual.

Não chama a API: usa as respostas que estão nos arquivos. Mostra, por pergunta,
o resultado gravado (gabarito da época) e o resultado com o gabarito atual.

Uso: python -m src.reavaliar_elementos PASTA [PASTA ...]
"""

import json
import sys
from pathlib import Path

from src.avaliacao_rag import _contem_todos, carregar_itens


def _arquivos(pasta):
    pasta = Path(pasta)
    rodadas = sorted(pasta.glob("rodada_*/resultados_rag.json"))

    return rodadas or [pasta / "resultados_rag.json"]


def main(pastas):
    itens = {i["id"]: i for i in carregar_itens() if i["tipo"] == "respondivel"}

    for pasta in pastas:
        print(f"\n{pasta}")

        for arquivo in _arquivos(pasta):
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            modelo = next(
                (a["auditoria"].get("modelo") for a in dados["avaliacoes"] if a["auditoria"].get("modelo")),
                "?",
            )
            linhas = []

            for a in dados["avaliacoes"]:
                if a["id"] not in itens:
                    continue

                antes = a["verificacoes"].get("elementos_na_resposta")
                depois = _contem_todos(a["resposta"], itens[a["id"]]["elementos_esperados"])
                linhas.append(f"{a['id']}: {antes} -> {depois}")

            print(f"  {arquivo.parent.name} ({modelo}): " + " | ".join(linhas))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))