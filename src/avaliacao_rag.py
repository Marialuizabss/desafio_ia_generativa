"""RF19 e RF23 — executa as oito perguntas do RAG e confere o resultado com o gabarito.

Para cada pergunta de `dados/originais/perguntas_rag.json` chama `responder_rf19` e
compara com `dados/gabaritos/gabarito_rag.json`, elaborado antes das chamadas:

  - respondível: status `fundamentada`, os elementos esperados na resposta, nenhum
    valor proibido, cada citação presente no trecho recuperado e ao menos uma
    citação na página de referência do gabarito;
  - sem resposta: status `sem_evidencia` e decisão `revisar` (abstenção);
  - contraditória: status `conflito`, decisão `revisar`, as duas datas divergentes
    apresentadas e os dois documentos citados.

A conferência é automática e não substitui a leitura humana: confirme em cada
resposta se as afirmações realmente decorrem dos trechos citados.

Uso:

    python -m src.avaliacao_rag              executa as 8 perguntas (chama a API)
    python -m src.avaliacao_rag --top-k 10
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
ARQ_PERGUNTAS = RAIZ_PROJETO / "dados" / "originais" / "perguntas_rag.json"
ARQ_GABARITO = RAIZ_PROJETO / "dados" / "gabaritos" / "gabarito_rag.json"
PASTA_SAIDA = RAIZ_PROJETO / "resultados" / "rag"

TOP_K_PADRAO = 15


def _normalizar(texto):
    return re.sub(r"\s+", " ", texto or "").strip().casefold()


def _alternativas(elemento):
    """Um elemento esperado é um texto ou uma lista de textos equivalentes."""
    return elemento if isinstance(elemento, list) else [elemento]


def carregar_itens(arq_perguntas=ARQ_PERGUNTAS, arq_gabarito=ARQ_GABARITO):
    perguntas = {
        p["id"]: p["pergunta"]
        for p in json.loads(arq_perguntas.read_text(encoding="utf-8"))["perguntas"]
    }
    itens = json.loads(arq_gabarito.read_text(encoding="utf-8"))["itens"]

    return [{**item, "pergunta": perguntas[item["id"]]} for item in itens]


def _contem_todos(texto, elementos):
    texto = _normalizar(texto)

    return all(
        any(_normalizar(alt) in texto for alt in _alternativas(elemento))
        for elemento in elementos
    )


def _segmentos(trecho_citado):
    """Fragmentos literais de uma citação; '...' marca partes puladas."""

    partes = re.split(r"\.{3,}|…", trecho_citado or "")
    segmentos = [p.strip(" \t\r\n:;,-") for p in partes]

    return [s for s in segmentos if len(s) >= 4] or [(trecho_citado or "").strip()]


def _citacoes_rastreaveis(fontes):
    """Cada fragmento citado precisa estar no trecho recuperado de onde veio."""

    return bool(fontes) and all(
        bool(_normalizar(f.get("trecho_citado")))
        and all(
            _normalizar(s) in _normalizar(f.get("trecho"))
            for s in _segmentos(f.get("trecho_citado"))
        )
        for f in fontes
    )


def _citou_pagina_de_referencia(fontes, referencias):
    return any(
        f.get("doc_id") == ref["doc_id"]
        and (ref.get("pagina") is None or f.get("pagina") == ref["pagina"])
        for f in fontes
        for ref in referencias
    )


def avaliar_item(item, resultado):
    """Confere o resultado de uma pergunta com o gabarito. Não chama a API."""

    fontes = resultado.get("fontes") or []
    resposta = resultado.get("resposta") or ""
    justificativa = resultado.get("justificativa") or ""
    status = resultado.get("status")
    decisao = resultado.get("decisao")

    verificacoes = {
        "status_correto": status == item["status_esperado"],
    }

    if item["tipo"] == "respondivel":
        # Trecho do acervo com instrução ao assistente: o caso vai para revisão por
        # segurança, e isso não é erro da resposta (o alerta fica registrado).
        verificacoes["decisao_correta"] = decisao != "revisar" or bool(resultado.get("alertas"))
        verificacoes["elementos_na_resposta"] = _contem_todos(
            resposta, item["elementos_esperados"]
        )
        verificacoes["sem_valor_proibido"] = not any(
            _normalizar(p) in _normalizar(resposta) for p in item["nao_pode_conter"]
        )
        verificacoes["citacoes_rastreaveis"] = _citacoes_rastreaveis(fontes)
        verificacoes["cita_pagina_de_referencia"] = _citou_pagina_de_referencia(
            fontes, item["referencias"]
        )

    elif item["tipo"] == "sem_resposta":
        verificacoes["decisao_correta"] = decisao == "revisar"

    else:  # contraditoria
        verificacoes["decisao_correta"] = decisao == "revisar"
        texto = " ".join(
            [resposta, justificativa] + [f.get("trecho_citado") or "" for f in fontes]
        )
        verificacoes["divergencia_apresentada"] = _contem_todos(
            texto, item["elementos_esperados"]
        )
        verificacoes["cita_os_dois_documentos"] = {
            ref["doc_id"] for ref in item["referencias"]
        } <= {f.get("doc_id") for f in fontes}

    return {
        "id": item["id"],
        "tipo": item["tipo"],
        "pergunta": item["pergunta"],
        "status_esperado": item["status_esperado"],
        "status_obtido": status,
        "decisao_obtida": decisao,
        "alertas": len(resultado.get("alertas") or []),
        "verificacoes": verificacoes,
        "aprovado": all(verificacoes.values()),
        "resposta": resposta,
        "justificativa": justificativa,
        "fontes": [
            {
                "chunk_id": f.get("chunk_id"),
                "doc_id": f.get("doc_id"),
                "versao": f.get("versao"),
                "pagina": f.get("pagina"),
                "secao": f.get("secao"),
                "trecho_citado": f.get("trecho_citado"),
            }
            for f in fontes
        ],
        "auditoria": {
            chave: (resultado.get("auditoria") or {}).get(chave)
            for chave in (
                "configuracao", "modelo", "simulado", "tempo_resposta_segundos",
                "tokens_entrada", "tokens_saida", "tokens_total", "custo_estimado_usd",
            )
        },
    }


def resumir(avaliacoes):
    """Métricas com numerador e denominador."""

    def contar(tipo, campo=None):
        grupo = [a for a in avaliacoes if a["tipo"] == tipo]
        if campo is None:
            return sum(a["aprovado"] for a in grupo), len(grupo)
        return sum(a["verificacoes"].get(campo, False) for a in grupo), len(grupo)

    custos = [
        a["auditoria"]["custo_estimado_usd"]
        for a in avaliacoes
        if a["auditoria"].get("custo_estimado_usd") is not None
    ]
    tokens = [
        a["auditoria"]["tokens_total"]
        for a in avaliacoes
        if a["auditoria"].get("tokens_total") is not None
    ]

    def par(valor):
        return {"numerador": valor[0], "denominador": valor[1]}

    return {
        "status_correto": par((
            sum(a["verificacoes"]["status_correto"] for a in avaliacoes),
            len(avaliacoes),
        )),
        "respondiveis_aprovadas": par(contar("respondivel")),
        "abstencao_correta_sem_resposta": par(contar("sem_resposta")),
        "conflito_tratado": par(contar("contraditoria")),
        "tokens_total": sum(tokens) if tokens else None,
        "custo_estimado_usd": round(sum(custos), 6) if custos else None,
        "observacao_metricas": (
            None if tokens else "O provedor não informou tokens nesta execução."
        ),
    }


def executar(responder, itens=None, top_k=TOP_K_PADRAO, nome_configuracao=None):
    """Roda as perguntas e devolve (avaliações, resumo). `responder` é injetável."""

    itens = itens or carregar_itens()
    avaliacoes = []

    for item in itens:
        try:
            if nome_configuracao:
                resultado = responder(
                    item["pergunta"], top_k=top_k, nome_configuracao=nome_configuracao
                )
            else:
                resultado = responder(item["pergunta"], top_k=top_k)
        except Exception as erro:  # a avaliação continua nas demais perguntas
            avaliacao = avaliar_item(item, {"status": None, "decisao": None})
            avaliacao["erro_execucao"] = f"{type(erro).__name__}: {erro}"
            avaliacao["aprovado"] = False
            avaliacoes.append(avaliacao)
            continue

        avaliacoes.append(avaliar_item(item, resultado))

    return avaliacoes, resumir(avaliacoes)


def gerar_relatorio_md(dados):
    resumo = dados["resumo"]

    def fracao(chave):
        v = resumo[chave]
        return f"{v['numerador']}/{v['denominador']}"

    linhas = [
        "# RAG — oito perguntas de avaliação (RF19 e RF23)",
        "",
        f"Execução: {dados['data_hora']}  ",
        f"top-k: {dados['top_k']}  ",
        f"Configuração de geração: {dados['configuracao']}",
        "",
        "A conferência é automática. Confirme manualmente se cada afirmação decorre dos trechos citados.",
        "",
        "## Métricas",
        "",
        "| Métrica | Resultado |",
        "|---|---:|",
        f"| Status igual ao esperado | {fracao('status_correto')} |",
        f"| Respondíveis aprovadas (status, elementos, citações verificadas) | {fracao('respondiveis_aprovadas')} |",
        f"| Abstenção correta nas perguntas sem resposta | {fracao('abstencao_correta_sem_resposta')} |",
        f"| Caso contraditório tratado (registrado à parte) | {fracao('conflito_tratado')} |",
        f"| Tokens | {resumo['tokens_total'] if resumo['tokens_total'] is not None else 'indisponível'} |",
        f"| Custo estimado (US$) | {resumo['custo_estimado_usd'] if resumo['custo_estimado_usd'] is not None else 'indisponível'} |",
        "",
        "## Por pergunta",
        "",
        "| Pergunta | Tipo | Esperado | Obtido | Aprovada | Alertas | Verificações que falharam |",
        "|---|---|---|---|---|---:|---|",
    ]

    for a in dados["avaliacoes"]:
        falhas = [k for k, v in a["verificacoes"].items() if not v]
        if a.get("erro_execucao"):
            falhas.append("erro_execucao")
        linhas.append(
            f"| {a['id']} | {a['tipo']} | {a['status_esperado']} | {a['status_obtido']} | "
            f"{'sim' if a['aprovado'] else 'nao'} | {a.get('alertas', 0)} | {', '.join(falhas) or '-'} |"
        )

    linhas += ["", "## Respostas e fontes", ""]

    for a in dados["avaliacoes"]:
        linhas += [f"### {a['id']} — {a['pergunta']}", "",
                   f"Status: **{a['status_obtido']}** · decisão: **{a['decisao_obtida']}**", ""]

        if a.get("erro_execucao"):
            linhas += [f"Erro: {a['erro_execucao']}", ""]

        linhas += [f"Resposta: {a['resposta'] or '(vazia)'}", ""]

        if a["justificativa"]:
            linhas += [f"Justificativa: {a['justificativa']}", ""]

        for f in a["fontes"]:
            local = f"página {f['pagina']}" if f["pagina"] else f"seção {f['secao'] or '-'}"
            linhas.append(
                f"- `{f['chunk_id']}` — {f['doc_id']} ({f['versao']}), {local}: "
                f"«{(f['trecho_citado'] or '')[:200]}»"
            )

        linhas.append("")

    return "\n".join(linhas)


def consolidar(rodadas):
    """Junta várias execuções das mesmas perguntas. `rodadas` = lista de listas de avaliações."""

    total = len(rodadas)
    perguntas = []

    for indice, base in enumerate(rodadas[0]):
        itens = [rodada[indice] for rodada in rodadas]
        falhas = {}

        for a in itens:
            for chave, ok in a["verificacoes"].items():
                if not ok:
                    falhas[chave] = falhas.get(chave, 0) + 1

            if a.get("erro_execucao"):
                falhas["erro_execucao"] = falhas.get("erro_execucao", 0) + 1

        perguntas.append({
            "id": base["id"],
            "tipo": base["tipo"],
            "status_esperado": base["status_esperado"],
            "execucoes": total,
            "aprovadas": sum(a["aprovado"] for a in itens),
            "status_correto": sum(a["verificacoes"]["status_correto"] for a in itens),
            "status_obtidos": [a["status_obtido"] for a in itens],
            "falhas_por_verificacao": falhas,
        })

    return {
        "rodadas": total,
        "perguntas": perguntas,
        "aprovacoes_por_rodada": [sum(a["aprovado"] for a in r) for r in rodadas],
        "status_correto_por_rodada": [
            sum(a["verificacoes"]["status_correto"] for a in r) for r in rodadas
        ],
    }


def gerar_relatorio_repeticoes_md(consolidado, top_k):
    total = consolidado["rodadas"]
    linhas = [
        f"# RAG — {total} execuções das oito perguntas (RF19 e RF23)",
        "",
        f"top-k: {top_k}. Cada linha mostra em quantas das {total} execuções a pergunta foi aprovada.",
        "O modelo responde de forma diferente a cada chamada, então uma execução isolada engana.",
        "",
        "| Pergunta | Tipo | Esperado | Aprovada em | Status correto em | Status obtidos | Falhas mais comuns |",
        "|---|---|---|---:|---:|---|---|",
    ]

    for q in consolidado["perguntas"]:
        comuns = ", ".join(
            f"{k} ({v}x)" for k, v in sorted(q["falhas_por_verificacao"].items(), key=lambda kv: -kv[1])
        ) or "-"
        linhas.append(
            f"| {q['id']} | {q['tipo']} | {q['status_esperado']} | {q['aprovadas']}/{total} | "
            f"{q['status_correto']}/{total} | {', '.join(str(s) for s in q['status_obtidos'])} | {comuns} |"
        )

    linhas += [
        "",
        f"Aprovadas por rodada (de 8): {consolidado['aprovacoes_por_rodada']}  ",
        f"Status correto por rodada (de 8): {consolidado['status_correto_por_rodada']}",
        "",
    ]

    return "\n".join(linhas)


def _gravar_execucao(destino, dados):
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "resultados_rag.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destino / "relatorio_rag.md").write_text(gerar_relatorio_md(dados), encoding="utf-8")


def _imprimir_resumo(avaliacoes, resumo):
    for a in avaliacoes:
        falhas = [k for k, v in a["verificacoes"].items() if not v]
        print(f"{a['id']} ({a['tipo']}): esperado {a['status_esperado']}, "
              f"obtido {a['status_obtido']} -> {'OK' if a['aprovado'] else 'FALHA ' + str(falhas)}")

    for chave, rotulo in (
        ("status_correto", "Status correto"),
        ("respondiveis_aprovadas", "Respondiveis aprovadas"),
        ("abstencao_correta_sem_resposta", "Abstencao correta"),
        ("conflito_tratado", "Conflito tratado"),
    ):
        print(f"{rotulo}: {resumo[chave]['numerador']}/{resumo[chave]['denominador']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--top-k", type=int, default=TOP_K_PADRAO)
    parser.add_argument("--configuracao", default="principal",
                        help="configuração de geração do config.json (adaptador_llm)")
    parser.add_argument("--repeticoes", type=int, default=1,
                        help="roda as perguntas N vezes e mostra em quantas cada uma passa")
    args = parser.parse_args(argv)

    if args.repeticoes < 1:
        parser.error("--repeticoes deve ser pelo menos 1")

    from src.rf19_complemento import responder_rf19

    raiz = PASTA_SAIDA / f"execucao_{datetime.now():%Y%m%d_%H%M%S}"
    rodadas = []

    for numero in range(1, args.repeticoes + 1):
        avaliacoes, resumo = executar(
            responder_rf19, top_k=args.top_k,
            nome_configuracao=None if args.configuracao == "principal" else args.configuracao,
        )
        rodadas.append(avaliacoes)

        dados = {
            "rf": "RF19/RF23",
            "data_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
            "top_k": args.top_k,
            "configuracao": args.configuracao,
            "resumo": resumo,
            "avaliacoes": avaliacoes,
        }

        destino = raiz if args.repeticoes == 1 else raiz / f"rodada_{numero}"
        _gravar_execucao(destino, dados)

        if args.repeticoes > 1:
            print(f"\n=== Rodada {numero} de {args.repeticoes} ===")

        _imprimir_resumo(avaliacoes, resumo)

    if args.repeticoes > 1:
        consolidado = consolidar(rodadas)
        (raiz / "consolidado.json").write_text(
            json.dumps(consolidado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        relatorio = gerar_relatorio_repeticoes_md(consolidado, args.top_k)
        (raiz / "consolidado.md").write_text(relatorio, encoding="utf-8")

        print("\n=== Consolidado ===")
        for q in consolidado["perguntas"]:
            print(f"{q['id']} ({q['tipo']}): aprovada em {q['aprovadas']}/{q['execucoes']}, "
                  f"status correto em {q['status_correto']}/{q['execucoes']}")

    print(f"\nResultados em: {raiz}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())