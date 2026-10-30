"""RF18 — avaliação de chunking e recuperação com as perguntas do gabarito.

Compara configurações de tamanho e sobreposição (em caracteres) com o mesmo
acervo, o mesmo modelo de embeddings, as mesmas perguntas e o mesmo top-k.

As perguntas são as respondíveis (P01 a P05) de `dados/originais/perguntas_rag.json`
e as referências vêm de `dados/gabaritos/gabarito_rag.json`, elaborado antes das
chamadas. Um trecho recuperado conta como referência quando:

  1. é do mesmo documento da referência;
  2. está na mesma página (quando o gabarito informa a página); e
  3. contém a frase de referência inteira (espaços normalizados, sem distinção
     de maiúsculas).

Acerto de recuperação = perguntas com ao menos um trecho de referência entre os
`k` primeiros resultados / total de perguntas respondíveis.

Uso:

    python -m src.avaliacao_rf18 --cobertura   confere só o chunking (sem embeddings)
    python -m src.avaliacao_rf18               avaliação completa (baixa o modelo)
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from src.indexar import indexar_acervo
from src.ingestion import carregar_catalogo, gerar_chunks_documento
from src.vector_store import (
    MODELO_EMBEDDINGS,
    buscar_chunks,
    carregar_modelo_embeddings,
    obter_colecao,
)

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
ARQ_PERGUNTAS = RAIZ_PROJETO / "dados" / "originais" / "perguntas_rag.json"
ARQ_GABARITO = RAIZ_PROJETO / "dados" / "gabaritos" / "gabarito_rag.json"
PASTA_INDICE_AVALIACAO = RAIZ_PROJETO / "dados" / "indice_avaliacao_rf18"
PASTA_SAIDA = RAIZ_PROJETO / "resultados" / "metricas" / "rf18"

UNIDADE = "caracteres"

CONFIGURACOES = {
    "pequena": {"tamanho": 300, "sobreposicao": 50},
    "media": {"tamanho": 800, "sobreposicao": 100},
    "grande": {"tamanho": 1200, "sobreposicao": 200},
}

VALORES_K = (3, 5, 10)


def _normalizar(texto):
    return re.sub(r"\s+", " ", texto).strip().casefold()


def carregar_perguntas_respondiveis(arq_perguntas=ARQ_PERGUNTAS, arq_gabarito=ARQ_GABARITO):
    """Junta pergunta e referências das perguntas do tipo `respondivel`."""

    perguntas = {
        p["id"]: p["pergunta"]
        for p in json.loads(arq_perguntas.read_text(encoding="utf-8"))["perguntas"]
    }
    itens = json.loads(arq_gabarito.read_text(encoding="utf-8"))["itens"]

    return [
        {
            "id": item["id"],
            "pergunta": perguntas[item["id"]],
            "referencias": item["referencias"],
        }
        for item in itens
        if item["tipo"] == "respondivel"
    ]


def trecho_e_referencia(doc_id, pagina, texto, referencia):
    """Regra de acerto: mesmo documento, mesma página e frase inteira no trecho."""

    if doc_id != referencia["doc_id"]:
        return False

    pagina_ref = referencia.get("pagina")

    if pagina_ref is not None and pagina != pagina_ref:
        return False

    return _normalizar(referencia["frase"]) in _normalizar(texto)


def posicao_da_primeira_referencia(resultados, referencias):
    """Posição (1 = primeiro) do primeiro trecho de referência, ou None."""

    for posicao, resultado in enumerate(resultados, start=1):
        meta = resultado["metadados"]
        pagina = meta["pagina"] or None

        if any(
            trecho_e_referencia(meta["doc_id"], pagina, resultado["texto"], ref)
            for ref in referencias
        ):
            return posicao

    return None


def cobertura_referencias(perguntas, catalogo=None, configuracoes=None):
    """Confere, sem embeddings, se cada frase de referência cabe num chunk.

    Se nenhuma configuração contém a frase inteira num chunk, o acerto daquela
    referência é impossível, e isso é um problema de chunking, não de busca.
    """

    catalogo = catalogo or carregar_catalogo()
    documentos = {d["doc_id"]: d for d in catalogo["documentos"]}
    configuracoes = configuracoes or CONFIGURACOES
    resultado = {}

    for nome, parametros in configuracoes.items():
        chunks_por_doc = {}
        linhas = []

        for pergunta in perguntas:
            for ref in pergunta["referencias"]:
                doc_id = ref["doc_id"]

                if doc_id not in chunks_por_doc:
                    chunks_por_doc[doc_id] = gerar_chunks_documento(
                        documentos[doc_id], **parametros
                    )

                contendo = [
                    c["chunk_id"]
                    for c in chunks_por_doc[doc_id]
                    if trecho_e_referencia(doc_id, c["pagina"], c["texto"], ref)
                ]
                linhas.append({
                    "pergunta": pergunta["id"],
                    "doc_id": doc_id,
                    "pagina": ref.get("pagina"),
                    "chunks_contendo_a_frase": contendo,
                    "coberta": bool(contendo),
                })

        resultado[nome] = {
            "referencias_cobertas": sum(l["coberta"] for l in linhas),
            "referencias_total": len(linhas),
            "detalhe": linhas,
        }

    return resultado


def avaliar_configuracao(nome, parametros, modelo, perguntas, pasta_indice, catalogo=None):
    """Indexa o acervo com a configuração e mede a recuperação de cada pergunta."""

    colecao = obter_colecao(pasta=pasta_indice, nome=f"rf18_{nome}")
    indexar_acervo(
        modelo, colecao, catalogo=catalogo,
        tamanho=parametros["tamanho"], sobreposicao=parametros["sobreposicao"],
    )

    k_maximo = max(VALORES_K)
    por_pergunta = []

    for pergunta in perguntas:
        resultados = buscar_chunks(pergunta["pergunta"], modelo, colecao, top_k=k_maximo)
        posicao = posicao_da_primeira_referencia(resultados, pergunta["referencias"])

        por_pergunta.append({
            "id": pergunta["id"],
            "pergunta": pergunta["pergunta"],
            "posicao_primeira_referencia": posicao,
            "distancia_cosseno_do_acerto": (
                round(resultados[posicao - 1]["distancia"], 4) if posicao else None
            ),
            "acerto_em_k": {str(k): bool(posicao and posicao <= k) for k in VALORES_K},
            "top_recuperados": [
                {
                    "posicao": i,
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["metadados"]["doc_id"],
                    "pagina": r["metadados"]["pagina"] or None,
                    "distancia_cosseno": round(r["distancia"], 4),
                }
                for i, r in enumerate(resultados[:5], start=1)
            ],
        })

    total = len(perguntas)
    taxas = {}

    for k in VALORES_K:
        acertos = sum(p["acerto_em_k"][str(k)] for p in por_pergunta)
        taxas[str(k)] = {
            "acertos": acertos,
            "perguntas": total,
            "taxa": round(acertos / total, 4) if total else 0.0,
        }

    return {
        "parametros": {**parametros, "unidade": UNIDADE},
        "total_chunks": colecao.count(),
        "acerto_de_recuperacao": taxas,
        "por_pergunta": por_pergunta,
    }


def gerar_relatorio_md(resultado):
    linhas = [
        "# RF18 — Chunking e recuperação",
        "",
        f"Execução: {resultado['data_hora']}  ",
        f"Modelo de embeddings: `{resultado['modelo_embeddings']}`  ",
        f"Unidade de tamanho e sobreposição: **{UNIDADE}**  ",
        "Distância: cosseno (menor = mais parecido; similaridade = 1 − distância).  ",
        f"Perguntas respondíveis: {', '.join(resultado['perguntas'])}",
        "",
        "## Parâmetros e acerto de recuperação",
        "",
        "| Configuração | Tamanho | Sobreposição | Chunks | " +
        " | ".join(f"Acerto@{k}" for k in VALORES_K) + " |",
        "|---|---:|---:|---:|" + "---:|" * len(VALORES_K),
    ]

    for nome, dados in resultado["configuracoes"].items():
        p = dados["parametros"]
        taxas = " | ".join(
            f"{dados['acerto_de_recuperacao'][str(k)]['acertos']}/"
            f"{dados['acerto_de_recuperacao'][str(k)]['perguntas']} "
            f"({dados['acerto_de_recuperacao'][str(k)]['taxa']:.0%})"
            for k in VALORES_K
        )
        linhas.append(
            f"| {nome} | {p['tamanho']} | {p['sobreposicao']} | {dados['total_chunks']} | {taxas} |"
        )

    linhas += ["", "## Posição do primeiro trecho de referência (— = fora do top-10)", ""]
    nomes = list(resultado["configuracoes"])
    linhas.append("| Pergunta | " + " | ".join(nomes) + " |")
    linhas.append("|---|" + "---:|" * len(nomes))

    for i, id_pergunta in enumerate(resultado["perguntas"]):
        celulas = []
        for nome in nomes:
            item = resultado["configuracoes"][nome]["por_pergunta"][i]
            celulas.append(str(item["posicao_primeira_referencia"] or "—"))
        linhas.append(f"| {id_pergunta} | " + " | ".join(celulas) + " |")

    linhas += ["", "## Cobertura das frases de referência pelos chunks", "",
               "| Configuração | Referências com a frase inteira num chunk |", "|---|---:|"]

    for nome, dados in resultado["cobertura"].items():
        linhas.append(
            f"| {nome} | {dados['referencias_cobertas']}/{dados['referencias_total']} |"
        )

    linhas += [
        "", "## Seleção e justificativa", "",
        "*A preencher pela equipe com base nas tabelas acima: a configuração escolhida, "
        "o porquê (resultado e preservação de contexto) e as falhas observadas.*", "",
    ]

    return "\n".join(linhas)


def executar(modelo, pasta_indice=PASTA_INDICE_AVALIACAO, pasta_saida=PASTA_SAIDA,
             configuracoes=None, catalogo=None, modelo_nome=MODELO_EMBEDDINGS):
    configuracoes = configuracoes or CONFIGURACOES
    perguntas = carregar_perguntas_respondiveis()

    resultado = {
        "rf": "RF18",
        "data_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
        "modelo_embeddings": modelo_nome,
        "perguntas": [p["id"] for p in perguntas],
        "cobertura": cobertura_referencias(perguntas, catalogo, configuracoes),
        "configuracoes": {
            nome: avaliar_configuracao(nome, parametros, modelo, perguntas, pasta_indice, catalogo)
            for nome, parametros in configuracoes.items()
        },
    }

    destino = Path(pasta_saida) / f"execucao_{datetime.now():%Y%m%d_%H%M%S}"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "resultados_rf18.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destino / "relatorio_rf18.md").write_text(gerar_relatorio_md(resultado), encoding="utf-8")

    return resultado, destino


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cobertura", action="store_true",
                        help="só confere o chunking, sem embeddings")
    args = parser.parse_args(argv)

    if args.cobertura:
        perguntas = carregar_perguntas_respondiveis()
        for nome, dados in cobertura_referencias(perguntas).items():
            print(f"{nome}: {dados['referencias_cobertas']}/{dados['referencias_total']} "
                  "referências cabem inteiras num chunk")
        return 0

    print("Carregando modelo de embeddings...")
    modelo = carregar_modelo_embeddings()
    resultado, destino = executar(modelo)

    for nome, dados in resultado["configuracoes"].items():
        taxas = ", ".join(
            f"Acerto@{k}: {dados['acerto_de_recuperacao'][str(k)]['acertos']}/"
            f"{dados['acerto_de_recuperacao'][str(k)]['perguntas']}"
            for k in VALORES_K
        )
        print(f"{nome} ({dados['total_chunks']} chunks) — {taxas}")

    print(f"\nResultados em: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())