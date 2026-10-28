"""RF14 — comparação entre JSON só sintático e saída validada por esquema (teste T01).

Parte da extração correta do CASO-08 (montada a partir do gabarito) e gera versões
com um defeito cada. Para cada versão, mostra o que aceita só ``json.loads``, o que
aceita o esquema (Pydantic, modo estrito) e o que aceitam as regras de negócio.
Não chama a API: as saídas são escritas aqui, para isolar cada tipo de erro.

Uso: python -m src.experimento_rf14
"""

import json
from datetime import date, datetime
from pathlib import Path

try:
    from privacidade import minimizar_texto
    from schemas import (
        data_abertura_processo, esperado_do_gabarito, validar_com_correcao,
        validar_estrutura, validar_regras,
    )
except ImportError:
    from src.privacidade import minimizar_texto
    from src.schemas import (
        data_abertura_processo, esperado_do_gabarito, validar_com_correcao,
        validar_estrutura, validar_regras,
    )

BASE_DIR = Path(__file__).resolve().parent.parent
GABARITO = BASE_DIR / "dados" / "gabaritos" / "gabarito_caso08.json"
PASTA_SAIDA = BASE_DIR / "resultados" / "metricas"


def _versoes(base: dict) -> list[tuple[str, str, str]]:
    """(nome, defeito introduzido, saída do modelo simulada)."""

    def com(**mudancas):
        dados = json.loads(json.dumps(base))
        for chave, valor in mudancas.items():
            dados[chave] = valor
        return json.dumps(dados, ensure_ascii=False)

    sem_categoria = {chave: valor for chave, valor in base.items() if chave != "categoria"}
    completo = json.dumps(base, ensure_ascii=False)
    return [
        ("valida", "nenhum", completo),
        ("chave_extra", "chave \"prioridade\" fora do contrato", com(prioridade="alta")),
        ("tipo_incorreto", "requer_revisao como texto (\"não\")", com(requer_revisao="não")),
        ("campo_obrigatorio_ausente", "sem a chave \"categoria\"", json.dumps(sem_categoria, ensure_ascii=False)),
        ("valor_fora_do_dominio", "categoria \"transferencia\", fora das seis", com(categoria="transferencia")),
        ("json_invalido", "resposta cortada no meio", completo[:-40]),
        ("data_impossivel", "data_solicitacao 31/02/2026", com(data_solicitacao="31/02/2026")),
        ("dado_nao_presente_no_original", "protocolo 2026-000999, que não está no texto", com(protocolo="2026-000999")),
    ]


def executar(hoje: date | None = None) -> dict:
    gabarito = json.loads(GABARITO.read_text(encoding="utf-8"))
    arquivo = gabarito["texto_entrada_rf15"]["arquivo"]
    texto = minimizar_texto((BASE_DIR / arquivo).read_text(encoding="utf-8"))
    data_minima = data_abertura_processo()
    hoje = hoje or date.today()

    linhas = []
    for nome, defeito, saida in _versoes(esperado_do_gabarito(gabarito)):
        try:
            json.loads(saida)
            sintatico = True
        except json.JSONDecodeError:
            sintatico = False
        solicitacao, erros = validar_estrutura(saida)
        regras = validar_regras(solicitacao, texto, data_minima, hoje) if solicitacao else None
        # O modelo simulado repete a mesma saída na correção: mostra o limite de uma nova tentativa
        resultado = validar_com_correcao(lambda _erros: saida, texto, arquivo, data_minima, hoje)
        linhas.append({
            "versao": nome,
            "defeito": defeito,
            "json_loads_aceita": sintatico,
            "esquema_aceita": solicitacao is not None,
            "regras_aceitam": None if regras is None else not regras,
            "erros": [f"{e.categoria}:{e.campo}" if e.campo else e.categoria for e in erros + (regras or [])],
            "tentativas": len(resultado.tentativas),
            "decisao": resultado.decisao,
            "minuta_bloqueada": resultado.minuta_bloqueada,
        })

    total = len(linhas)
    return {
        "experimento": "RF14 — JSON sintático × esquema × regras de negócio (T01)",
        "executado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "caso_base": gabarito["caso_id"],
        "entrada": arquivo,
        "data_minima": data_minima.isoformat() if data_minima else None,
        "chamou_api": False,
        "resumo": {
            "versoes": total,
            "json_loads_aceita": sum(l["json_loads_aceita"] for l in linhas),
            "esquema_aceita": sum(l["esquema_aceita"] for l in linhas),
            "regras_aceitam": sum(bool(l["regras_aceitam"]) for l in linhas),
        },
        "linhas": linhas,
    }


def _sim_nao(valor) -> str:
    return "—" if valor is None else ("sim" if valor else "**não**")


def para_markdown(resultado: dict) -> str:
    r = resultado["resumo"]
    linhas = [
        "# RF14 — JSON sintático × esquema × regras de negócio (T01)",
        "",
        f"- Executado em: {resultado['executado_em']}",
        f"- Caso base: {resultado['caso_base']} (`{resultado['entrada']}`), extração correta montada a partir do gabarito",
        f"- Data mínima da solicitação (abertura do processo, lida do acervo): {resultado['data_minima']}",
        "- Chamou a API: não — as saídas do modelo são simuladas para isolar cada tipo de erro",
        "",
        f"De {r['versoes']} versões, `json.loads` aceitou **{r['json_loads_aceita']}**, o esquema aceitou "
        f"**{r['esquema_aceita']}** e as regras de negócio aceitaram **{r['regras_aceitam']}**: "
        "JSON válido não garante esquema válido, e esquema válido não garante dado correto.",
        "",
        "| Versão | Defeito | `json.loads` | Esquema | Regras | Erros classificados | Tentativas | Decisão | Minuta |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for l in resultado["linhas"]:
        linhas.append(
            f"| {l['versao']} | {l['defeito']} | {_sim_nao(l['json_loads_aceita'])} | {_sim_nao(l['esquema_aceita'])} "
            f"| {_sim_nao(l['regras_aceitam'])} | {', '.join(f'`{e}`' for e in l['erros']) or '—'} | {l['tentativas']} "
            f"| {l['decisao']} | {'bloqueada' if l['minuta_bloqueada'] else 'liberada'} |"
        )
    linhas += [
        "",
        "Erro de sintaxe ou de esquema gera uma nova tentativa (2 no total); como a saída simulada repete o erro,",
        "a versão é rejeitada. Regra de negócio violada não gera nova tentativa: o caso vai para revisão.",
        "Nos dois casos a minuta fica bloqueada.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    resultado = executar()
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    (PASTA_SAIDA / "rf14_comparacao.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PASTA_SAIDA / "rf14_comparacao.md").write_text(para_markdown(resultado), encoding="utf-8")
    print(para_markdown(resultado))
    print(f"Resultados em {PASTA_SAIDA.relative_to(BASE_DIR)}/rf14_comparacao.(json|md)")


if __name__ == "__main__":
    main()
