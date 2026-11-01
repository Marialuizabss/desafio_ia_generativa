"""T15 — um caso de texto e um de áudio já transcrito, até a minuta.

A leitura do áudio não é refeita: o enunciado manda reaproveitar a transcrição do
Desafio 1. A análise usa o contrato atual (RF14/RF15). A minuta leva os fatos da
ficha e não preenche documento, prazo ou local, porque esta regressão não consulta
o acervo. Os dois casos ficam encaminhados à revisão humana. Nada é enviado.

Esta passagem não grava decisão. Não há operador na tela, então o log não recebe
``revisar`` nem nome de revisor. A transcrição do CASO-05 repete o turno
("noturno noturno"); essa pendência sai no registro do caso.

Uso:
  python -m src.regressao_t15
"""

import json
from datetime import datetime
from pathlib import Path

from src.audit import registrar_execucao
from src.consulta_acervo import classificar_ficha, minuta_do_atendimento
from src.nlp import analisar_solicitacao

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_SAIDA = BASE_DIR / "resultados" / "metricas" / "t15"

CASOS = (
    {
        "id": "CASO-04",
        "modalidade": "texto",
        "origem": "dados/originais/entrada_texto.txt",
        "texto": None,
    },
    {
        "id": "CASO-05",
        "modalidade": "audio",
        "origem": "dados/processados/transcricao_entrada_audio.txt",
        "texto": None,
    },
)

MOTIVO_ENCAMINHAMENTO = (
    "Regressão T15: a minuta foi montada com os fatos da solicitação. "
    "Documento, prazo e local não foram preenchidos porque esta passagem não consultou o acervo. "
    "O caso fica encaminhado à revisão humana e nada é enviado. "
    "Nenhuma decisão foi registrada: não há operador nesta passagem."
)

def pendencias_do_caso(caso_id: str, texto: str, minuta: str) -> list[str]:
    """Pendência conhecida da transcrição reaproveitada. Não é uma decisão."""
    if caso_id != "CASO-05" or "noturno noturno" not in (texto or "").casefold():
        return []
    frases = [
        "Pendente: a transcrição reaproveitada do CASO-05 repete o turno ('noturno noturno').",
    ]
    if "noturno noturno" in (minuta or "").casefold():
        frases.append("A minuta reproduz essa duplicidade.")
    if "Início do curso: não localizado" in (minuta or ""):
        frases.append("O início do curso sai como 'não localizado'.")
    frases.append("A revisão humana ainda não foi feita.")
    return [" ".join(frases)]


def ler_casos() -> list[dict]:
    casos = []
    for caso in CASOS:
        caminho = BASE_DIR / caso["origem"]
        casos.append({**caso, "texto": caminho.read_text(encoding="utf-8")})
    return casos


def montar_caso(caso: dict, analise) -> dict:
    """Ficha e minuta, sem gravar decisão. O destino é a revisão humana."""
    ficha = classificar_ficha(analise.validacao, analise.guardrail)
    minuta = minuta_do_atendimento(ficha, None)
    return {
        "id": caso["id"],
        "modalidade": caso["modalidade"],
        "origem": caso["origem"],
        "decisao_ficha": ficha.get("tipo"),
        "encaminhamento": "revisar",
        "decisao_humana": None,
        "minuta_pronta": minuta["pronta"],
        "minuta": minuta["texto"],
        "motivos": ficha.get("motivos") or [],
        "motivo_encaminhamento": MOTIVO_ENCAMINHAMENTO,
        "pendencias": pendencias_do_caso(caso["id"], caso["texto"], minuta["texto"]),
        "enviada": False,
    }


def executar(chamar=None) -> Path:
    pasta = PASTA_SAIDA / datetime.now().strftime("execucao_%Y%m%d_%H%M%S")
    pasta.mkdir(parents=True)
    registros = []
    for caso in ler_casos():
        analise = analisar_solicitacao(caso["texto"], caso["origem"], chamar)
        registro = montar_caso(caso, analise)
        id_execucao = registrar_execucao({
            "origem": "t15",
            "caso": caso["id"],
            "modalidade": caso["modalidade"],
            "arquivo_origem": caso["origem"],
            "decisao_ficha": registro["decisao_ficha"],
            "encaminhamento": registro["encaminhamento"],
            "decisao_humana": None,
            "pendencias": registro["pendencias"],
        })
        registro["id_execucao"] = id_execucao
        registros.append(registro)
        (pasta / f"{caso['id']}.md").write_text(registro["minuta"] + "\n", encoding="utf-8")
        salvo = {chave: valor for chave, valor in registro.items() if chave != "minuta"}
        (pasta / f"{caso['id']}.json").write_text(
            json.dumps(salvo, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    resumo = {
        "experimento": "T15 — regressão de texto e áudio até minuta e revisão",
        "executado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "casos": [registro["id"] for registro in registros],
        "encaminhamento": {registro["id"]: registro["encaminhamento"] for registro in registros},
        "decisao_humana": None,
        "pendencias": {
            registro["id"]: registro["pendencias"]
            for registro in registros
            if registro["pendencias"]
        },
        "minutas_montadas": sum(registro["minuta_pronta"] for registro in registros),
        "enviadas": 0,
    }
    (pasta / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return pasta


def main() -> int:
    pasta = executar()
    print(f"Regressão em {pasta.relative_to(BASE_DIR).as_posix()}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
