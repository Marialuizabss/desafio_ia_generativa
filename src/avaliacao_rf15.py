"""RF15 — execução nos casos com gabarito, matriz do T03 e conferência humana.

Uso:
  python -m src.avaliacao_rf15 --simulado          sem API: resposta montada do gabarito
  python -m src.avaliacao_rf15 --todos             chamada real ao modelo (usa a chave do .env)
  python -m src.avaliacao_rf15 --consolidar PASTA  métricas finais depois da conferência humana

Cada execução cria resultados/metricas/rf15/execucao_<data>/ com um JSON por caso, a matriz
(matriz_rf15.md), as métricas preliminares (resumo.json) e o modelo de conferência
(conferencia_rf15.json), que a revisora preenche antes de consolidar. Execução simulada
fica marcada como tal em todos os arquivos (seção 12 do enunciado).
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from audit import registrar_evento
    from nlp import (
        DECISOES_DA_CONFERENCIA, agregar, analisar_solicitacao, arquivo_do_prompt,
        comparar_com_gabarito, consolidar, itens_para_conferencia, versao_do_prompt,
    )
    from schemas import VERSAO_ESQUEMA, esperado_do_gabarito
except ImportError:
    from src.audit import registrar_evento
    from src.nlp import (
        DECISOES_DA_CONFERENCIA, agregar, analisar_solicitacao, arquivo_do_prompt,
        comparar_com_gabarito, consolidar, itens_para_conferencia, versao_do_prompt,
    )
    from src.schemas import VERSAO_ESQUEMA, esperado_do_gabarito

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_GABARITOS = BASE_DIR / "dados" / "gabaritos"
PASTA_SAIDA = BASE_DIR / "resultados" / "metricas" / "rf15"

# Seção 7 de documentacao/desafio-2/contratos_dados.md
GABARITOS = {
    "CASO-01": "gabarito_caso01.json",
    "CASO-04": "gabarito_entrada_texto.json",
    "CASO-05": "gabarito_entrada_audio.json",
    "CASO-06": "gabarito_entrada_pdf-imagem.json",
    "CASO-02": "gabarito_caso02.json",
    "CASO-07": "gabarito_caso07.json",
    "CASO-08": "gabarito_caso08.json",
}


def ler_json(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def salvar_json(caminho: Path, dados) -> None:
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def texto_do_caso(gabarito: dict) -> tuple[str, str]:
    """Texto reaproveitado do caso (antes da minimização) e o arquivo de origem."""
    entrada = gabarito["texto_entrada_rf15"]
    caminho = BASE_DIR / entrada["arquivo"]
    if entrada["campo"]:
        return ler_json(caminho)[entrada["campo"]], entrada["arquivo"]
    return caminho.read_text(encoding="utf-8"), entrada["arquivo"]


def chamar_simulado(gabarito: dict):
    """Responde com a extração correta montada do gabarito, sem chamar a API."""
    def chamar(_instrucoes, _entrada, _esquema):
        return json.dumps(esperado_do_gabarito(gabarito), ensure_ascii=False), {"modo": "simulado"}
    return chamar


def avaliar_caso(caso: str, gabarito: dict, modo: str, hoje: date | None = None) -> dict:
    texto, arquivo = texto_do_caso(gabarito)
    base = {"caso": caso, "modo": modo, "tipo_caso": gabarito["tipo_caso"], "arquivo": arquivo}
    try:
        analise = analisar_solicitacao(
            texto, arquivo, chamar_simulado(gabarito) if modo == "simulado" else None, hoje=hoje
        )
    except ValueError as erro:
        return {**base, "erro": str(erro)}

    validacao = analise.validacao
    registro = {
        **base,
        "arquivo_prompt": arquivo_do_prompt(),
        "versao_prompt": analise.versao_prompt,
        "versao_esquema": VERSAO_ESQUEMA,
        "chamadas": analise.chamadas,
        "validacao": {**validacao.para_registro(), "motivos": validacao.motivos},
        "saida_validada": validacao.solicitacao.model_dump() if validacao.solicitacao else None,
        "saidas_brutas": validacao.saidas,
        "comparacao": comparar_com_gabarito(validacao.solicitacao, gabarito, analise.texto_minimizado),
    }
    if modo == "real":
        # RF11: sem o texto da solicitação nem a saída do modelo
        registrar_evento("analise_rf15", {
            "caso": caso,
            "versao_prompt": analise.versao_prompt,
            "chamadas": analise.chamadas,
            "validacao": validacao.para_registro(),
            "categoria": registro["saida_validada"]["categoria"] if registro["saida_validada"] else None,
        })
    return registro


def criar_pasta(modo: str) -> Path:
    nome = datetime.now().strftime("execucao_%Y%m%d_%H%M%S") + ("_simulado" if modo == "simulado" else "")
    pasta = PASTA_SAIDA / nome
    pasta.mkdir(parents=True, exist_ok=False)
    return pasta


def executar(modo: str, casos: list[str] | None = None, hoje: date | None = None) -> Path:
    casos = casos or list(GABARITOS)
    gabaritos = {caso: ler_json(PASTA_GABARITOS / GABARITOS[caso]) for caso in casos}
    pasta = criar_pasta(modo)

    registros = {}
    for caso, gabarito in gabaritos.items():
        registros[caso] = avaliar_caso(caso, gabarito, modo, hoje)
        salvar_json(pasta / f"{caso}.json", registros[caso])

    comparacoes = {caso: r["comparacao"] for caso, r in registros.items() if "comparacao" in r}
    custos = [c.get("custo_estimado_usd") for r in registros.values() for c in r.get("chamadas", [])]
    resumo = {
        "experimento": "RF15 — resumo, categoria e entidades comparados com o gabarito (T03)",
        "modo": modo,
        "chamou_api": modo == "real",
        "executado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "arquivo_prompt": arquivo_do_prompt(),
        "versao_prompt": versao_do_prompt(),
        "versao_esquema": VERSAO_ESQUEMA,
        "casos": casos,
        "casos_com_erro": {caso: r["erro"] for caso, r in registros.items() if "erro" in r},
        "custo_estimado_usd": round(sum(c for c in custos if c), 6) if any(custos) else None,
        "metricas_preliminares": agregar(comparacoes, {c: gabaritos[c] for c in comparacoes}),
    }
    salvar_json(pasta / "resumo.json", resumo)
    salvar_json(pasta / "conferencia_rf15.json", {
        "instrucoes": "Preencha 'decisao' de cada item com uma das 'opcoes' e, se quiser, a 'observacao'. "
                      "Depois rode: python -m src.avaliacao_rf15 --consolidar " + _relativo(pasta),
        "revisora": "",
        "itens": itens_para_conferencia(comparacoes),
    })
    (pasta / "matriz_rf15.md").write_text(matriz(resumo, registros), encoding="utf-8")
    return pasta


def consolidar_pasta(pasta: Path) -> dict:
    pasta = Path(pasta)
    resumo = ler_json(pasta / "resumo.json")
    conferencia = ler_json(pasta / "conferencia_rf15.json")
    final = consolidar(resumo["metricas_preliminares"], conferencia["itens"])
    final["conferencia_humana"]["revisora"] = conferencia.get("revisora", "")
    final["modo"] = resumo["modo"]
    salvar_json(pasta / "metricas_rf15.json", final)
    (pasta / "metricas_rf15.md").write_text(texto_metricas(final, conferencia["itens"]), encoding="utf-8")
    return final


# ---------------------------------------------------------------- relatórios

def _relativo(caminho: Path) -> str:
    try:
        return Path(caminho).relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(caminho)


def _fracao(f: dict) -> str:
    percentual = "—" if f["percentual"] is None else f"{f['percentual']}%"
    return f"{f['numerador']}/{f['denominador']} ({percentual})"


def matriz(resumo: dict, registros: dict) -> str:
    aviso = "**SIMULADO** — resposta montada do gabarito, sem chamar a API" if resumo["modo"] == "simulado" \
        else "**Real** — chamada ao modelo"
    m = resumo["metricas_preliminares"]
    linhas = [
        "# RF15 — Matriz do T03 (resumo, categoria e entidades)",
        "",
        f"- Modo: {aviso}",
        f"- Executado em: {resumo['executado_em']}",
        f"- Prompt: `prompts/desafio2/{resumo['arquivo_prompt']}` (versão `{resumo['versao_prompt']}`) · versão do esquema: `{resumo['versao_esquema']}`",
        f"- Custo estimado: {'—' if resumo['custo_estimado_usd'] is None else f'US$ {resumo['custo_estimado_usd']}'}",
        "",
        "| Caso | Tipo | Categoria (esperada → obtida) | Entidades: acertos · omissões · extras do texto · incorretas | Fatos no resumo (automático) · a conferir | Sem suporte no resumo | RF14 | Tempo (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for caso, r in registros.items():
        if "erro" in r:
            linhas.append(f"| {caso} | {r['tipo_caso']} | **erro:** {r['erro']} | | | | | |")
            continue
        c, e = r["comparacao"], r["comparacao"]["entidades"]
        esperadas = len(e["acertos"]) + len(e["omissoes"]) + len(e["parecidas"])
        categoria = f"{c['categoria']['esperada']} → {c['categoria']['obtida']} {'✅' if c['categoria']['acerto'] else '❌'}"
        fatos = len(c["fatos"]["preservados"]) + len(c["fatos"]["a_conferir"])
        tempo = sum(ch.get("tempo_resposta_segundos") or 0 for ch in r["chamadas"])
        linhas.append(
            f"| {caso} | {r['tipo_caso']} | {categoria} | {len(e['acertos'])}/{esperadas} · {len(e['omissoes'])} · "
            f"{len(e['extras_no_texto'])} · {len(e['incorretas'])} | {len(c['fatos']['preservados'])}/{fatos} · "
            f"{len(c['fatos']['a_conferir'])} | {', '.join(c['sem_suporte']) or '—'} | {r['validacao']['decisao']} | "
            f"{tempo or '—'} |"
        )
    linhas += [
        "",
        "## Métricas preliminares (antes da conferência humana)",
        "",
        f"- Acurácia da categoria: {_fracao(m['acuracia_categoria'])}; só os seis casos do enunciado: {_fracao(m['acuracia_categoria_seis_do_enunciado'])}",
        f"- Entidades esperadas encontradas: {_fracao(m['entidades_acertos'])}; omissões: {m['entidades_omissoes']}; "
        f"parecidas a conferir: {m['entidades_parecidas_a_conferir']}; extras do texto (aceitas): {m['entidades_extras_no_texto']}; "
        f"incorretas: {m['entidades_incorretas']}; inferidas a conferir: {m['entidades_inferidas_a_conferir']}",
        f"- Fatos essenciais encontrados no resumo automaticamente: {_fracao(m['fatos_preservados_automatico'])}; a conferir: {m['fatos_a_conferir']}",
        f"- Dados do resumo sem suporte no texto: {m['resumo_sem_suporte']}",
        f"- Saídas rejeitadas pelo RF14: {_fracao(m['rejeitadas'])}",
        "",
        "Os itens \"a conferir\" estão em `conferencia_rf15.json`; depois de preenchidos, `--consolidar` gera `metricas_rf15.md`.",
    ]
    return "\n".join(linhas) + "\n"


def texto_metricas(final: dict, itens: list[dict]) -> str:
    linhas = [
        "# RF15 — Métricas finais (depois da conferência humana)",
        "",
        f"- Modo: {final['modo']} · itens conferidos: {final['conferencia_humana']['itens']} · revisora: {final['conferencia_humana'].get('revisora') or '—'}",
        f"- Acurácia da categoria: {_fracao(final['acuracia_categoria'])}; seis do enunciado: {_fracao(final['acuracia_categoria_seis_do_enunciado'])}",
        f"- Entidades esperadas encontradas: {_fracao(final['entidades_acertos'])}; omissões: {final['entidades_omissoes']}; incorretas: {final['entidades_incorretas']}",
        f"- Fatos essenciais preservados no resumo: {_fracao(final['fatos_preservados'])}; omitidos: {final['fatos_omitidos']}",
        f"- Fatos sem suporte (resumo, inferidas sem suporte e entidades incorretas): {final['fatos_sem_suporte']}",
        f"- Saídas rejeitadas pelo RF14: {_fracao(final['rejeitadas'])}",
        "",
        "## Erros e correções registrados na conferência",
        "",
        "| Caso | Tipo | Item | Decisão | Observação |",
        "|---|---|---|---|---|",
    ]
    linhas += [f"| {i['caso']} | {i['tipo']} | {i['descricao']} | {i['decisao']} | {i['observacao'] or '—'} |" for i in itens]
    if not itens:
        linhas.append("| — | — | Nenhum item precisou de conferência | — | — |")
    return "\n".join(linhas) + "\n"


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RF15: avaliação de resumo, categoria e entidades.")
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--simulado", action="store_true", help="sem API, resposta montada do gabarito")
    modo.add_argument("--todos", action="store_true", help="chamada real ao modelo")
    modo.add_argument("--consolidar", metavar="PASTA", help="métricas finais depois da conferência")
    parser.add_argument("--casos", nargs="+", choices=list(GABARITOS), help="só estes casos")
    args = parser.parse_args(argumentos)

    if args.consolidar:
        try:
            final = consolidar_pasta(BASE_DIR / args.consolidar if not Path(args.consolidar).is_absolute() else Path(args.consolidar))
        except ValueError as erro:
            print(erro)
            return 1
        print(f"Métricas finais: acurácia da categoria {_fracao(final['acuracia_categoria'])}.")
        return 0

    pasta = executar("simulado" if args.simulado else "real", args.casos)
    print((pasta / "matriz_rf15.md").read_text(encoding="utf-8"))
    print(f"Resultados em {_relativo(pasta)}/")
    print("Opções da conferência:", {tipo: list(opcoes) for tipo, opcoes in DECISOES_DA_CONFERENCIA.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
