"""Indexação do acervo e exclusão de documentos do índice (RF17 e RF24).

Uso (na raiz do projeto):

    python -m src.indexar                    indexa o acervo (idempotente)
    python -m src.indexar --status           mostra o que está no índice
    python -m src.indexar --excluir ACV-09   remove um documento do índice

Reindexar o mesmo acervo não duplica: um documento só é regravado quando muda
o hash ou o texto dos seus chunks. A troca do modelo de embeddings é detectada
e exige `--recriar`.

Os parâmetros de chunking padrão (800 caracteres, sobreposição 100) são os da
configuração escolhida no RF18.
"""

import argparse
import json
import sys
from pathlib import Path

from src.ingestion import (
    carregar_catalogo,
    gerar_chunks_documento,
    validar_documentos,
)
from src.vector_store import (
    NOME_COLECAO,
    PASTA_INDICE,
    calcular_versao_indice,
    carregar_modelo_embeddings,
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
PASTAS_DERIVADOS = ("dados/resultados", "resultados/metricas")


def indexar_acervo(
    modelo,
    colecao,
    catalogo=None,
    tamanho=TAMANHO_PADRAO,
    sobreposicao=SOBREPOSICAO_PADRAO,
):
    """Indexa todos os documentos válidos do catálogo. Devolve um relatório."""

    catalogo = catalogo or carregar_catalogo()
    validacao = {r["doc_id"]: r["status"] for r in validar_documentos(catalogo)}

    relatorio = []

    for documento in catalogo["documentos"]:
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


def excluir_e_registrar(colecao, doc_id, motivo="", raiz=RAIZ_PROJETO):
    """Exclui o documento do índice, avisa os derivados e grava a auditoria."""

    from src.audit import registrar_evento

    resultado = excluir_documento(colecao, doc_id)
    resultado["derivados_a_revisar"] = localizar_derivados(doc_id, raiz)
    resultado["versao_indice_apos"] = calcular_versao_indice(colecao)

    registrar_evento("exclusao_documento", {
        "doc_id": doc_id,
        "chunks_removidos": resultado["chunks_removidos"],
        "status": resultado["status"],
        "motivo": (motivo or "").strip(),
        "derivados_a_revisar": resultado["derivados_a_revisar"],
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
    parser.add_argument("--motivo", default="")
    parser.add_argument("--recriar", action="store_true",
                        help="apaga a coleção e indexa do zero (troca de modelo)")
    parser.add_argument("--tamanho", type=int, default=TAMANHO_PADRAO)
    parser.add_argument("--sobreposicao", type=int, default=SOBREPOSICAO_PADRAO)
    parser.add_argument("--pasta", default=str(PASTA_INDICE))
    args = parser.parse_args(argv)

    if args.recriar:
        _recriar_colecao(args.pasta)

    colecao = obter_colecao(pasta=args.pasta)

    if args.status:
        saida = {
            "pasta": args.pasta,
            "colecao": colecao.name,
            "modelo_embeddings": (colecao.metadata or {}).get("modelo_embeddings"),
            "dimensao": (colecao.metadata or {}).get("dimensao"),
            "versao_indice": calcular_versao_indice(colecao),
            "total_chunks": colecao.count(),
            "documentos": listar_documentos_indexados(colecao),
        }
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0

    if args.excluir:
        resultado = excluir_e_registrar(colecao, args.excluir, args.motivo)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print(
            "\nAtenção: reindexar traz o documento de volta enquanto ele "
            "constar em dados/acervo/acervo.json."
        )
        return 0 if resultado["status"] == "excluido" else 1

    print("Carregando modelo de embeddings...")
    modelo = carregar_modelo_embeddings()

    relatorio = indexar_acervo(
        modelo, colecao,
        tamanho=args.tamanho, sobreposicao=args.sobreposicao,
    )

    for item in relatorio:
        print(f"{item['doc_id']}: {item['status']} ({item['chunks']} chunks)")

    print(f"\nTotal no índice: {colecao.count()} chunks")
    print(f"Versão do índice: {calcular_versao_indice(colecao)}")

    problemas = [r for r in relatorio if r["status"] not in ("indexado", "sem_alteracoes")]
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())