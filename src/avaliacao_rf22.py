"""RF22 — execução das 12 avaliações, painel e acurácia da polaridade.

Uso:
  python -m src.avaliacao_rf22 --simulado   sem API: resposta montada do gabarito
  python -m src.avaliacao_rf22 --todos      chamada real pela configuração principal

Cada execução cria resultados/metricas/rf22/execucao_<data>/ com um JSON por avaliação,
o painel (painel_rf22.md) e o resumo. A execução simulada fica marcada como tal.
A confiança não entra nos percentuais.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from audit import registrar_evento
except ImportError:
    from src.audit import registrar_evento

from src.sentimentos import (
    POLARIDADES, ROTULO_CONFIANCA, VERSAO_ESQUEMA, agregar_painel, arquivo_do_prompt,
    classificar_avaliacao, fracao, saida_de_gabarito, versao_do_prompt, chamar_principal,
)

BASE_DIR = Path(__file__).resolve().parent.parent
AVALIACOES = BASE_DIR / "dados" / "avaliacoes" / "avaliacoes.json"
GABARITO = BASE_DIR / "dados" / "gabaritos" / "gabarito_avaliacoes.json"
PASTA_SAIDA = BASE_DIR / "resultados" / "metricas" / "rf22"


def ler_json(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def salvar_json(caminho: Path, dados) -> None:
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relativo(caminho: Path) -> str:
    try:
        return Path(caminho).relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(caminho)


def chamar_simulado(item: dict):
    """Responde com a situação que as regras convertem no rótulo do gabarito, sem API."""

    def chamar(_instrucoes, _entrada):
        return json.dumps(saida_de_gabarito(item), ensure_ascii=False), {"modo": "simulado", "simulado": True}

    return chamar


def avaliar_uma(avaliacao: dict, item: dict, modo: str) -> dict:
    chamar = chamar_simulado(item) if modo == "simulado" else chamar_principal
    base = {"id": avaliacao["id"], "modo": modo, "canal": avaliacao["canal"], "data": avaliacao["data"]}
    try:
        classificacao = classificar_avaliacao(avaliacao["texto"], avaliacao["id"], chamar)
    except ValueError as erro:
        return {
            **base,
            "erro": str(erro),
            "polaridade": None,
            "revisao": True,
            "rejeitada": True,
            "acerto_polaridade": False,
            "polaridade_esperada": item["polaridade_esperada"],
            "revisao_esperada": item["revisao_esperada"],
        }

    registro = {
        **base,
        **classificacao.para_dict(),
        "polaridade_esperada": item["polaridade_esperada"],
        "revisao_esperada": item["revisao_esperada"],
        "acerto_polaridade": classificacao.polaridade == item["polaridade_esperada"],
        "acerto_revisao": classificacao.revisao == item["revisao_esperada"],
    }
    if modo == "real":
        registrar_evento("classificacao_rf22", {
            "id": avaliacao["id"],
            "versao_prompt": classificacao.versao_prompt,
            "polaridade": classificacao.polaridade,
            "revisao": classificacao.revisao,
            "rejeitada": classificacao.rejeitada,
            "chamadas": classificacao.chamadas,
        })
    return registro


def registro_do_painel(registro: dict) -> dict:
    """O que o painel lê. A confiança vai junto para ficar claro que a conta não a usa."""
    return {
        "id": registro["id"],
        "canal": registro.get("canal"),
        "data": registro.get("data"),
        "polaridade": registro.get("polaridade"),
        "revisao": registro.get("revisao"),
        "rejeitada": registro.get("rejeitada"),
        "confianca": registro.get("confianca"),
    }


def criar_pasta(modo: str) -> Path:
    nome = datetime.now().strftime("execucao_%Y%m%d_%H%M%S") + ("_simulado" if modo == "simulado" else "")
    pasta = PASTA_SAIDA / nome
    pasta.mkdir(parents=True, exist_ok=False)
    return pasta


def executar(modo: str, ids: list[str] | None = None) -> Path:
    entrada = ler_json(AVALIACOES)["avaliacoes"]
    rotulos = {item["id"]: item for item in ler_json(GABARITO)["avaliacoes"]}
    if ids:
        entrada = [avaliacao for avaliacao in entrada if avaliacao["id"] in ids]
    pasta = criar_pasta(modo)

    registros = []
    for avaliacao in entrada:
        registro = avaliar_uma(avaliacao, rotulos[avaliacao["id"]], modo)
        registros.append(registro)
        salvar_json(pasta / f"{avaliacao['id']}.json", registro)

    acertos = sum(registro.get("acerto_polaridade") is True for registro in registros)
    revisoes = sum(registro.get("acerto_revisao") is True for registro in registros)
    custos = [
        chamada.get("custo_estimado_usd")
        for registro in registros
        for chamada in registro.get("chamadas", [])
    ]
    custos_validos = [custo for custo in custos if isinstance(custo, (int, float))]
    painel = agregar_painel([registro_do_painel(registro) for registro in registros])
    resumo = {
        "experimento": "RF22 — polaridade das avaliações e painel (T13)",
        "modo": modo,
        "chamou_api": modo == "real",
        "simulado": modo == "simulado",
        "executado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "arquivo_prompt": arquivo_do_prompt(),
        "versao_prompt": versao_do_prompt(),
        "versao_esquema": VERSAO_ESQUEMA,
        "rotulo_confianca": ROTULO_CONFIANCA,
        "acuracia_polaridade": fracao(acertos, len(registros)),
        "concordancia_revisao": fracao(revisoes, len(registros)),
        "custo_estimado_usd": round(sum(custos_validos), 6) if custos_validos else None,
        "painel": painel,
    }
    salvar_json(pasta / "resumo.json", resumo)
    (pasta / "painel_rf22.md").write_text(texto_painel(resumo, registros), encoding="utf-8")
    return pasta


def _percentual(valor) -> str:
    return "—" if valor is None else f"{valor}%"


def texto_painel(resumo: dict, registros: list[dict]) -> str:
    aviso = (
        "**SIMULADO** — resposta montada do gabarito, sem chamar a API"
        if resumo["modo"] == "simulado"
        else "**Real** — chamada ao modelo pela configuração principal"
    )
    painel = resumo["painel"]
    linhas = [
        "# RF22 — Polaridade e painel",
        "",
        f"- Modo: {aviso}",
        f"- Executado em: {resumo['executado_em']}",
        f"- Prompt: `prompts/desafio2/{resumo['arquivo_prompt']}` (versão `{resumo['versao_prompt']}`) · esquema `{resumo['versao_esquema']}`",
        f"- Confiança: {resumo['rotulo_confianca']}. Não entra no percentual.",
        f"- Custo estimado: {'—' if resumo['custo_estimado_usd'] is None else f'US$ {resumo['custo_estimado_usd']}'}",
        "",
        "## Painel",
        "",
        f"- Registros lidos: {painel['registros']} · únicos: {painel['unicos']} · duplicados: {', '.join(painel['duplicados']) or '—'}",
        f"- Denominador (classificadas): {painel['denominador']}",
        f"- Rejeitadas (fora dos totais): {painel['rejeitadas']}",
        f"- Revisão: {painel['revisao']}",
        f"- Mensagem: {painel['mensagem'] or '—'}",
        "",
        "| Polaridade | Total | Fração | Percentual |",
        "|---|---:|---|---:|",
    ]
    for polaridade in POLARIDADES:
        fracao_texto = painel["fracoes"][polaridade] or "—"
        linhas.append(
            f"| {polaridade} | {painel['totais'][polaridade]} | {fracao_texto} | {_percentual(painel['percentuais'][polaridade])} |"
        )
    acuracia = resumo["acuracia_polaridade"]
    revisao = resumo["concordancia_revisao"]
    linhas += [
        "",
        "## Acurácia",
        "",
        f"- Polaridade: {acuracia['numerador']}/{acuracia['denominador']} ({_percentual(acuracia['percentual'])})",
        f"- Revisão: {revisao['numerador']}/{revisao['denominador']} ({_percentual(revisao['percentual'])})",
        "",
        "| Avaliação | Esperada → obtida | Revisão | Confiança |",
        "|---|---|---|---:|",
    ]
    for registro in registros:
        if registro.get("erro"):
            linhas.append(f"| {registro['id']} | **erro:** {registro['erro']} | revisar | — |")
            continue
        marca = "acerto" if registro["acerto_polaridade"] else "erro"
        confianca = "—" if registro.get("confianca") is None else registro["confianca"]
        linhas.append(
            f"| {registro['id']} | {registro['polaridade_esperada']} → {registro['polaridade']} ({marca}) | "
            f"{'sim' if registro['revisao'] else 'não'} | {confianca} |"
        )
    return "\n".join(linhas) + "\n"


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RF22: polaridade das avaliações e painel.")
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--simulado", action="store_true", help="sem API, resposta montada do gabarito")
    modo.add_argument("--todos", action="store_true", help="chamada real pela configuração principal")
    parser.add_argument("--ids", nargs="+", help="só estas avaliações, por exemplo AV01 AV10")
    args = parser.parse_args(argumentos)

    pasta = executar("simulado" if args.simulado else "real", args.ids)
    print((pasta / "painel_rf22.md").read_text(encoding="utf-8"))
    print(f"Resultados em {_relativo(pasta)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
