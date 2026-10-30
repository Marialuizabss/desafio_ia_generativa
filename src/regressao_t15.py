"""T15 — um caso de texto e um de áudio já transcrito, até a minuta e a revisão.

A leitura do áudio não é refeita: o enunciado manda reaproveitar a transcrição do
Desafio 1. A análise usa o contrato atual (RF14/RF15). A minuta leva os fatos da
ficha e não preenche documento, prazo ou local, porque esta regressão não consulta
o acervo. Os dois casos seguem para revisão. Nada é enviado.

Uso:
  python -m src.regressao_t15
"""

import json
from datetime import datetime
from pathlib import Path

from src.audit import registrar_decisao, registrar_execucao
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

JUSTIFICATIVA = (
    "Regressão T15: a minuta foi montada com os fatos da solicitação. "
    "Documento, prazo e local não foram preenchidos porque esta passagem não consultou o acervo. "
    "O caso segue para revisão e nada é enviado."
)


def ler_casos() -> list[dict]:
    casos = []
    for caso in CASOS:
        caminho = BASE_DIR / caso["origem"]
        casos.append({**caso, "texto": caminho.read_text(encoding="utf-8")})
    return casos


def montar_caso(caso: dict, analise) -> dict:
    """Ficha, minuta e estado, sem gravar log. A revisão é o destino dos dois casos."""
    ficha = classificar_ficha(analise.validacao, analise.guardrail)
    minuta = minuta_do_atendimento(ficha, None)
    return {
        "id": caso["id"],
        "modalidade": caso["modalidade"],
        "origem": caso["origem"],
        "decisao_ficha": ficha.get("tipo"),
        "estado": "revisar",
        "minuta_pronta": minuta["pronta"],
        "minuta": minuta["texto"],
        "motivos": ficha.get("motivos") or [],
        "justificativa_revisao": JUSTIFICATIVA,
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
        })
        registrar_decisao(
            id_execucao,
            "revisar",
            justificativa=JUSTIFICATIVA,
            revisor="Felipe Ferreira Aguiar",
            cargo_setor="Regressão T15",
        )
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
        "estados": {registro["id"]: registro["estado"] for registro in registros},
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
