"""Indexação do acervo e exclusão de documentos do índice (RF17 e RF24).

Uso (na raiz do projeto):

    python -m src.indexar                    indexa o acervo (idempotente)
    python -m src.indexar --status           mostra o que está no índice
    python -m src.indexar --excluir ACV-09 --motivo "retenção encerrada"
    python -m src.indexar --restaurar ACV-09

Reindexar o mesmo acervo não duplica: um documento só é regravado quando muda
o hash ou o texto dos seus chunks. A troca do modelo de embeddings é detectada
e exige `--recriar`. Documento excluído fica registrado em
`dados/acervo/exclusoes.json` e a indexação o pula até ser restaurado.

Os parâmetros de chunking padrão (800 caracteres, sobreposição 100) são os da
configuração escolhida no RF18.
"""

import argparse
import json
import sys
from pathlib import Path

from src.ingestion import (
    carregar_catalogo,
    carregar_exclusoes,
    gerar_chunks_documento,
    registrar_exclusao,
    remover_exclusao,
    validar_documentos,
)
from src.vector_store import (
    DESCRICOES_SITUACAO,
    NOME_COLECAO,
    PASTA_INDICE,
    calcular_versao_indice,
    carregar_modelo_embeddings,
    conferir_indice,
    excluir_documento,
    indexar_documento,
    listar_documentos_indexados,
    obter_colecao,
)

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

TAMANHO_PADRAO = 800
SOBREPOSICAO_PADRAO = 100

# Pastas com resultados derivados do acervo (respostas, trechos recuperados,
# métricas). Servem só para avisar o que cita um documento excluído.
PASTAS_DERIVADOS = ("dados/resultados", "resultados/metricas", "resultados/rag")


def indexar_acervo(
    modelo,
    colecao,
    catalogo=None,
    tamanho=TAMANHO_PADRAO,
    sobreposicao=SOBREPOSICAO_PADRAO,
    exclusoes=None,
):
    """Indexa todos os documentos válidos do catálogo. Devolve um relatório.

    Documento excluído (RF24) é pulado e, se ainda tiver trechos no índice, eles saem.
    """

    catalogo = catalogo or carregar_catalogo()
    exclusoes = carregar_exclusoes() if exclusoes is None else exclusoes
    validacao = {r["doc_id"]: r["status"] for r in validar_documentos(catalogo)}

    relatorio = []

    for documento in catalogo["documentos"]:
        if documento["doc_id"] in exclusoes:
            excluir_documento(colecao, documento["doc_id"])
            relatorio.append({
                "doc_id": documento["doc_id"],
                "status": "excluido",
                "chunks": 0,
                "motivo": exclusoes[documento["doc_id"]].get("motivo", ""),
            })
            continue

        status_arquivo = validacao[documento["doc_id"]]

        if status_arquivo != "valido":
            # Arquivo ausente ou alterado fora do catálogo: não indexa.
            relatorio.append({
                "doc_id": documento["doc_id"],
                "status": status_arquivo,
                "chunks": 0,
            })
            continue

        chunks = gerar_chunks_documento(
            documento, tamanho=tamanho, sobreposicao=sobreposicao
        )
        relatorio.append(indexar_documento(documento, chunks, modelo, colecao))

    return relatorio


def localizar_derivados(doc_id, raiz=RAIZ_PROJETO):
    """Arquivos de resultados que citam o documento (para revisão/limpeza)."""

    encontrados = []

    for pasta in PASTAS_DERIVADOS:
        base = Path(raiz) / pasta

        if not base.is_dir():
            continue

        for caminho in sorted(base.rglob("*")):
            if caminho.suffix not in (".json", ".md"):
                continue

            try:
                texto = caminho.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            if doc_id in texto:
                encontrados.append(caminho.relative_to(raiz).as_posix())
    return encontrados


def excluir_e_registrar(
    colecao, doc_id, motivo="", raiz=RAIZ_PROJETO, responsavel="terminal", catalogo=None
):
    """Exclui o documento do índice, registra a exclusão, avisa os derivados e audita.

    O registro em `exclusoes.json` faz a exclusão durar: a indexação pula o documento
    até ele ser restaurado. Sem motivo, ou fora do catálogo, nada é excluído.
    """

    from src.audit import registrar_evento

    motivo = (motivo or "").strip()

    if not motivo:
        raise ValueError("Informe o motivo da exclusão.")

    catalogo = catalogo or carregar_catalogo()

    if doc_id not in {documento["doc_id"] for documento in catalogo["documentos"]}:
        raise ValueError(f"{doc_id} não está no catálogo do acervo.")

    anterior = carregar_exclusoes().get(doc_id)

    if anterior:
        raise ValueError(
            f"{doc_id} já está excluído desde {anterior['data'][:10]} "
            f"(motivo: {anterior['motivo']})."
        )

    resultado = excluir_documento(colecao, doc_id)
    resultado["derivados_a_revisar"] = localizar_derivados(doc_id, raiz)
    resultado["versao_indice_apos"] = calcular_versao_indice(colecao)
    resultado["registro"] = registrar_exclusao(doc_id, motivo, responsavel)

    registrar_evento("exclusao_documento", {
        "doc_id": doc_id,
        "chunks_removidos": resultado["chunks_removidos"],
        "status": resultado["status"],
        "motivo": motivo,
        "responsavel": responsavel,
        "derivados_a_revisar": resultado["derivados_a_revisar"],
        "versao_indice_apos": resultado["versao_indice_apos"],
    })

    return resultado


def restaurar_e_registrar(
    colecao, doc_id, modelo, responsavel="terminal", catalogo=None,
    tamanho=TAMANHO_PADRAO, sobreposicao=SOBREPOSICAO_PADRAO,
):
    """Tira o documento do registro de exclusões, reindexa só ele e audita.

    Indexa antes de apagar o registro: se a indexação falhar, o documento continua
    excluído, e não pendente.
    """

    from src.audit import registrar_evento

    exclusao = carregar_exclusoes().get(doc_id)

    if not exclusao:
        raise ValueError(f"{doc_id} não está excluído.")

    catalogo = catalogo or carregar_catalogo()
    documento = next(
        (item for item in catalogo["documentos"] if item["doc_id"] == doc_id), None
    )

    if documento is None:
        raise ValueError(f"{doc_id} não está no catálogo do acervo.")

    status_arquivo = next(
        r["status"] for r in validar_documentos(catalogo) if r["doc_id"] == doc_id
    )

    if status_arquivo != "valido":
        raise ValueError(
            f"O arquivo de {doc_id} não confere com o catálogo ({status_arquivo}). "
            "Restauração cancelada."
        )

    chunks = gerar_chunks_documento(documento, tamanho=tamanho, sobreposicao=sobreposicao)
    resultado = indexar_documento(documento, chunks, modelo, colecao)
    remover_exclusao(doc_id)
    resultado["versao_indice_apos"] = calcular_versao_indice(colecao)

    registrar_evento("restauracao_documento", {
        "doc_id": doc_id,
        "chunks": resultado["chunks"],
        "responsavel": responsavel,
        "motivo_da_exclusao": exclusao.get("motivo", ""),
        "excluido_em": exclusao.get("data", ""),
        "versao_indice_apos": resultado["versao_indice_apos"],
    })

    return resultado


def _recriar_colecao(pasta):
    import chromadb

    cliente = chromadb.PersistentClient(path=str(pasta))

    try:
        cliente.delete_collection(NOME_COLECAO)
    except Exception:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--excluir", metavar="DOC_ID")
    parser.add_argument("--motivo", default="", help="obrigatório com --excluir")
    parser.add_argument("--restaurar", metavar="DOC_ID")
    parser.add_argument("--responsavel", default="terminal")
    parser.add_argument("--recriar", action="store_true",
                        help="apaga a coleção e indexa do zero (troca de modelo)")
    parser.add_argument("--tamanho", type=int, default=TAMANHO_PADRAO)
    parser.add_argument("--sobreposicao", type=int, default=SOBREPOSICAO_PADRAO)
    parser.add_argument("--pasta", default=str(PASTA_INDICE))
    args = parser.parse_args(argv)

    if args.excluir and not args.motivo.strip():
        parser.error('--excluir exige --motivo, por exemplo: --motivo "retenção encerrada"')

    if args.recriar:
        _recriar_colecao(args.pasta)

    colecao = obter_colecao(pasta=args.pasta)
    exclusoes = carregar_exclusoes()

    if args.status:
        saida = {
            "pasta": args.pasta,
            "colecao": colecao.name,
            "modelo_embeddings": (colecao.metadata or {}).get("modelo_embeddings"),
            "dimensao": (colecao.metadata or {}).get("dimensao"),
            "versao_indice": calcular_versao_indice(colecao),
            "total_chunks": colecao.count(),
            "documentos": listar_documentos_indexados(colecao),
            "conferencia": conferir_indice(carregar_catalogo(), colecao, exclusoes),
            "exclusoes": list(exclusoes.values()),
        }
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0

    if args.excluir:
        try:
            resultado = excluir_e_registrar(
                colecao, args.excluir, args.motivo, responsavel=args.responsavel
            )
        except ValueError as erro:
            print(f"Exclusão não feita: {erro}")
            return 1
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print(
            f"\n{args.excluir} fica fora do índice até ser restaurado. Para trazer de volta: "
            f"python -m src.indexar --restaurar {args.excluir}"
        )
        return 0

    print("Carregando modelo de embeddings...")
    modelo = carregar_modelo_embeddings()

    if args.restaurar:
        try:
            resultado = restaurar_e_registrar(
                colecao, args.restaurar, modelo, responsavel=args.responsavel,
                tamanho=args.tamanho, sobreposicao=args.sobreposicao,
            )
        except ValueError as erro:
            print(f"Restauração não feita: {erro}")
            return 1
        print(f"{args.restaurar}: restaurado ({resultado['chunks']} chunks)")
        print(f"Total no índice: {colecao.count()} chunks")
        imprimir_conferencia(conferir_indice(carregar_catalogo(), colecao, carregar_exclusoes()))
        return 0

    relatorio = indexar_acervo(
        modelo, colecao,
        tamanho=args.tamanho, sobreposicao=args.sobreposicao, exclusoes=exclusoes,
    )

    for item in relatorio:
        if item["status"] == "excluido":
            print(f"{item['doc_id']}: excluído ({item['motivo']}), não indexado")
        else:
            print(f"{item['doc_id']}: {item['status']} ({item['chunks']} chunks)")

    print(f"\nTotal no índice: {colecao.count()} chunks")
    print(f"Versão do índice: {calcular_versao_indice(colecao)}")

    conferencia = conferir_indice(carregar_catalogo(), colecao, exclusoes)
    imprimir_conferencia(conferencia)

    problemas = [
        r for r in relatorio if r["status"] not in ("indexado", "sem_alteracoes", "excluido")
    ]
    return 1 if problemas or not conferencia["completo"] else 0


def imprimir_conferencia(conferencia):
    """Resumo da conferência catálogo × índice para quem está no terminal."""

    if conferencia["completo"]:
        indexados = sum(d["situacao"] == "indexado" for d in conferencia["documentos"])
        excluidos = sum(d["situacao"] == "excluido" for d in conferencia["documentos"])
        extra = f", {excluidos} excluído(s)" if excluidos else ""
        print(f"Conferência: índice completo ({indexados} documentos indexados{extra}).")
        return

    print("Conferência: o índice não confere com o catálogo. A consulta fica bloqueada.")
    for pendencia in conferencia["pendencias"]:
        print(f"  {pendencia['doc_id']}: {DESCRICOES_SITUACAO[pendencia['situacao']]}")
    print("Rode `python -m src.indexar` de novo depois de corrigir o arquivo ou o catálogo; "
          "para documento fora do catálogo, `python -m src.indexar --recriar`.")


if __name__ == "__main__":
    sys.exit(main())