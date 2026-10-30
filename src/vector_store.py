"""Índice vetorial persistente do acervo (RF17) e exclusão de documentos (RF24).

Cada coleção guarda, nos próprios metadados, o modelo de embeddings e a dimensão
com que foi criada. Abrir a coleção com outro modelo é um erro explícito
(`IndiceDesatualizadoError`): vetores de modelos diferentes não são comparáveis,
então a troca de modelo exige reindexação.
"""

import hashlib
from pathlib import Path

import chromadb


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_INDICE = RAIZ_PROJETO / "dados" / "indice_vetorial"

NOME_COLECAO = "acervo_ficdev"
MODELO_EMBEDDINGS = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
DIMENSAO_EMBEDDINGS = 384


class IndiceDesatualizadoError(RuntimeError):
    """O índice foi criado com outro modelo ou dimensão de embeddings."""


def carregar_modelo_embeddings():
    # Importação tardia: os testes e a exclusão não precisam do modelo.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELO_EMBEDDINGS)


def obter_colecao(
    pasta=None,
    nome=NOME_COLECAO,
    modelo_embeddings=MODELO_EMBEDDINGS,
    dimensao=DIMENSAO_EMBEDDINGS,
):
    """Abre (ou cria) a coleção e confere modelo e dimensão de embeddings."""

    cliente = chromadb.PersistentClient(
        path=str(pasta or PASTA_INDICE)
    )

    metadados = {
        "hnsw:space": "cosine",
        "modelo_embeddings": modelo_embeddings,
        "dimensao": int(dimensao),
    }

    colecao = cliente.get_or_create_collection(
        name=nome,
        metadata=metadados,
    )

    existente = colecao.metadata or {}
    modelo_gravado = existente.get("modelo_embeddings")

    if modelo_gravado is None:
        # Índice criado antes do registro do modelo: grava agora, desde que
        # os vetores existentes tenham a dimensão esperada.
        if colecao.count() > 0:
            amostra = colecao.get(limit=1, include=["embeddings"])
            if len(amostra["embeddings"][0]) != int(dimensao):
                raise IndiceDesatualizadoError(
                    "O índice tem vetores de outra dimensão; reindexe."
                )
        # A função de distância (cosseno) é preservada pelo Chroma.
        colecao.modify(metadata={
            "modelo_embeddings": modelo_embeddings,
            "dimensao": int(dimensao),
        })
        return colecao

    if (
        modelo_gravado != modelo_embeddings
        or int(existente.get("dimensao", -1)) != int(dimensao)
    ):
        raise IndiceDesatualizadoError(
            f"O índice foi criado com '{modelo_gravado}' "
            f"(dimensão {existente.get('dimensao')}), mas a execução usa "
            f"'{modelo_embeddings}' (dimensão {dimensao}). "
            "Reindexe o acervo com o modelo atual."
        )

    return colecao


def preparar_metadados(chunk):
    return {
        "doc_id": chunk["doc_id"],
        "titulo": chunk["titulo"],
        "versao": str(chunk["versao"]),
        "sha256": chunk["sha256"],
        "pagina": chunk["pagina"] if chunk["pagina"] is not None else 0,
        "secao": chunk["secao"] if chunk["secao"] is not None else "",
    }


def indexar_documento(documento, chunks, modelo, colecao):
    doc_id = documento["doc_id"]
    hash_atual = documento["sha256"]

    existentes = colecao.get(
        where={"doc_id": doc_id},
        include=["metadatas", "documents"],
    )

    hashes_existentes = {
        meta["sha256"] for meta in existentes["metadatas"]
    }

    textos_existentes = dict(
        zip(existentes["ids"], existentes["documents"])
    )

    textos_atuais = {
        chunk["chunk_id"]: chunk["texto"]
        for chunk in chunks
    }

    if (
        existentes["ids"]
        and hashes_existentes == {hash_atual}
        and set(existentes["ids"]) == set(textos_atuais)
        and textos_existentes == textos_atuais
    ):
        return {
            "doc_id": doc_id,
            "status": "sem_alteracoes",
            "chunks": len(chunks),
        }

    textos = [chunk["texto"] for chunk in chunks]
    embeddings = modelo.encode(textos).tolist()

    dimensao_registrada = (colecao.metadata or {}).get("dimensao")

    if (
        embeddings
        and dimensao_registrada is not None
        and len(embeddings[0]) != int(dimensao_registrada)
    ):
        raise IndiceDesatualizadoError(
            "A dimensão dos embeddings gerados difere da registrada no índice."
        )

    if existentes["ids"]:
        colecao.delete(ids=existentes["ids"])

    colecao.upsert(
        ids=[chunk["chunk_id"] for chunk in chunks],
        embeddings=embeddings,
        documents=textos,
        metadatas=[preparar_metadados(chunk) for chunk in chunks],
    )

    return {
        "doc_id": doc_id,
        "status": "indexado",
        "chunks": len(chunks),
    }


def buscar_chunks(pergunta, modelo, colecao, top_k=5):
    """Busca os `top_k` trechos mais próximos da pergunta.

    `distancia` é a distância cosseno (0 = mesma direção; quanto menor, mais
    parecido). A similaridade cosseno equivale a `1 - distancia`.
    """

    if not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    if top_k <= 0:
        raise ValueError("top_k deve ser positivo.")

    if colecao.count() == 0:
        return []

    vetor = modelo.encode([pergunta]).tolist()

    resultados = colecao.query(
        query_embeddings=vetor,
        n_results=min(top_k, colecao.count()),
        include=["documents", "metadatas", "distances"],
    )

    encontrados = []

    for indice, chunk_id in enumerate(resultados["ids"][0]):
        distancia = resultados["distances"][0][indice]
        encontrados.append({
            "chunk_id": chunk_id,
            "texto": resultados["documents"][0][indice],
            "metadados": resultados["metadatas"][0][indice],
            "distancia": distancia,
            "similaridade": round(1 - distancia, 6),
        })

    return encontrados


def listar_documentos_indexados(colecao):
    """Resume o que está no índice: documentos, versões, hashes e chunks."""

    dados = colecao.get(include=["metadatas"])
    resumo = {}

    for meta in dados["metadatas"]:
        item = resumo.setdefault(meta["doc_id"], {
            "doc_id": meta["doc_id"],
            "versao": meta["versao"],
            "sha256": meta["sha256"],
            "chunks": 0,
        })
        item["chunks"] += 1

    return [resumo[chave] for chave in sorted(resumo)]


def calcular_versao_indice(colecao):
    """Identificador estável do conteúdo do índice.

    Muda quando muda o modelo, um documento (hash) ou a quantidade de chunks
    de algum documento. Serve para a auditoria apontar qual índice respondeu.
    """

    metadados = colecao.metadata or {}
    partes = [
        str(metadados.get("modelo_embeddings")),
        str(metadados.get("dimensao")),
    ]

    for item in listar_documentos_indexados(colecao):
        partes.append(
            f"{item['doc_id']}:{item['versao']}:{item['sha256']}:{item['chunks']}"
        )

    resumo = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()

    return resumo[:12]


def excluir_documento(colecao, doc_id):
    """Remove do índice todos os vetores de um documento (RF24).

    Devolve a quantidade removida e confere, ao final, que nenhum trecho do
    documento restou.
    """

    existentes = colecao.get(where={"doc_id": doc_id})
    ids = existentes["ids"]

    if ids:
        colecao.delete(ids=ids)

    restantes = colecao.get(where={"doc_id": doc_id})["ids"]

    if restantes:
        raise RuntimeError(
            f"Falha ao excluir {doc_id}: {len(restantes)} trechos permaneceram."
        )

    return {
        "doc_id": doc_id,
        "chunks_removidos": len(ids),
        "status": "excluido" if ids else "nao_encontrado",
    }