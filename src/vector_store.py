from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_INDICE = RAIZ_PROJETO / "dados" / "indice_vetorial"

NOME_COLECAO = "acervo_ficdev"
MODELO_EMBEDDINGS = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


def carregar_modelo_embeddings():
    return SentenceTransformer(MODELO_EMBEDDINGS)


def obter_colecao():
    cliente = chromadb.PersistentClient(
        path=str(PASTA_INDICE)
    )

    colecao = cliente.get_or_create_collection(
        name=NOME_COLECAO,
        metadata={"hnsw:space": "cosine"},
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
        encontrados.append({
            "chunk_id": chunk_id,
            "texto": resultados["documents"][0][indice],
            "metadados": resultados["metadatas"][0][indice],
            "distancia": resultados["distances"][0][indice],
        })

    return encontrados
