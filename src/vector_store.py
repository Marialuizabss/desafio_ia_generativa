"""Índice vetorial persistente do acervo (RF17) e exclusão de documentos (RF24).

Cada coleção guarda, nos próprios metadados, o modelo de embeddings e a dimensão
com que foi criada. Abrir a coleção com outro modelo é um erro explícito
(`IndiceDesatualizadoError`): vetores de modelos diferentes não são comparáveis,
então a troca de modelo exige reindexação.
"""

import hashlib
import threading
from pathlib import Path

import chromadb


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PASTA_INDICE = RAIZ_PROJETO / "dados" / "indice_vetorial"

NOME_COLECAO = "acervo_ficdev"
MODELO_EMBEDDINGS = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
DIMENSAO_EMBEDDINGS = 384

# O Chroma guarda o sistema em cache antes de terminar de iniciá-lo. Duas aberturas
# ao mesmo tempo (duas consultas na interface) pegavam o índice pela metade.
_TRAVA_ABERTURA = threading.Lock()


class IndiceDesatualizadoError(RuntimeError):
    """O índice foi criado com outro modelo ou dimensão de embeddings."""


class IndiceIncompletoError(IndiceDesatualizadoError):
    """O índice não confere com o catálogo. A mensagem diz o que falta e o que fazer."""


# Situações da conferência que impedem a consulta: resposta sem um retificador, ou com
# texto antigo, parece fundamentada e está errada.
PENDENCIAS_DE_INDEXAR = ("nao_indexado", "desatualizado")
PENDENCIAS_DE_REMOVER = ("fora_do_catalogo", "excluido_no_indice")

DESCRICOES_SITUACAO = {
    "indexado": "indexado",
    "nao_indexado": "não indexado",
    "desatualizado": "desatualizado (o documento mudou depois da indexação)",
    "excluido": "excluído do índice",
    "fora_do_catalogo": "está no índice, mas não no catálogo",
    "excluido_no_indice": "foi excluído, mas continua no índice",
}

ACAO_INDEXAR = (
    'vá à tela Acervo e clique em "Indexar selecionados" '
    "(os documentos pendentes já vêm marcados)"
)


_MODELO = None
_TRAVA_MODELO = threading.Lock()


class _ModeloCompartilhado:
    """O mesmo modelo para todas as consultas do processo.

    `encode` é serializado: o tokenizador não aceita duas threads ao mesmo tempo (duas
    consultas simultâneas na interface). O resto (tokenizer, max_seq_length) é repassado.
    """

    def __init__(self, modelo):
        self._modelo = modelo
        self._trava = threading.Lock()

    def encode(self, *args, **kwargs):
        with self._trava:
            return self._modelo.encode(*args, **kwargs)

    def __getattr__(self, nome):
        return getattr(self._modelo, nome)


def _criar_modelo():
    # Importação tardia: os testes e a exclusão não precisam do modelo.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELO_EMBEDDINGS)


def modelo_carregado():
    """O modelo já está na memória: a próxima consulta não espera a carga."""

    return _MODELO is not None


def carregar_modelo_embeddings():
    """Carrega o modelo uma vez por processo; as consultas seguintes o reaproveitam."""

    global _MODELO

    with _TRAVA_MODELO:
        if _MODELO is None:
            _MODELO = _ModeloCompartilhado(_criar_modelo())
        return _MODELO


def obter_colecao(
    pasta=None,
    nome=NOME_COLECAO,
    modelo_embeddings=MODELO_EMBEDDINGS,
    dimensao=DIMENSAO_EMBEDDINGS,
):
    """Abre (ou cria) a coleção e confere modelo e dimensão de embeddings.

    Uma abertura por vez: quem chega depois espera e reaproveita o índice já aberto.
    """

    with _TRAVA_ABERTURA:
        return _abrir_colecao(pasta, nome, modelo_embeddings, dimensao)


def obter_colecao_se_existir(pasta=None):
    """Abre o índice só se a pasta existir: conferir não deixa uma pasta vazia para trás."""

    pasta = Path(pasta or PASTA_INDICE)
    return obter_colecao(pasta=pasta) if pasta.is_dir() else None


def _abrir_colecao(pasta, nome, modelo_embeddings, dimensao):
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


def conferir_indice(catalogo, colecao, excluidos=()):
    """Compara o catálogo com o índice, documento por documento (doc_id e hash).

    `colecao` None é índice inexistente. `excluidos` são os documentos tirados do
    índice de propósito (RF24): fora do índice, não são pendência.
    """

    no_indice = {
        item["doc_id"]: item
        for item in (listar_documentos_indexados(colecao) if colecao is not None else [])
    }
    excluidos = set(excluidos)
    documentos = []

    for documento in catalogo["documentos"]:
        doc_id = documento["doc_id"]
        item = no_indice.pop(doc_id, None)

        if doc_id in excluidos:
            situacao = "excluido" if item is None else "excluido_no_indice"
        elif item is None:
            situacao = "nao_indexado"
        elif item["sha256"] != documento["sha256"]:
            situacao = "desatualizado"
        else:
            situacao = "indexado"

        documentos.append({
            "doc_id": doc_id,
            "situacao": situacao,
            "chunks": item["chunks"] if item else 0,
        })

    for doc_id, item in sorted(no_indice.items()):
        documentos.append({
            "doc_id": doc_id,
            "situacao": "fora_do_catalogo",
            "chunks": item["chunks"],
        })

    pendencias = [
        documento for documento in documentos
        if documento["situacao"] in PENDENCIAS_DE_INDEXAR + PENDENCIAS_DE_REMOVER
    ]

    return {
        "documentos": documentos,
        "pendencias": pendencias,
        "completo": not pendencias,
        "vazio": not any(documento["chunks"] for documento in documentos),
        "total_chunks": sum(documento["chunks"] for documento in documentos),
    }


def mensagem_de_pendencias(conferencia):
    """O motivo do bloqueio e o que fazer na interface. Vazio quando não há pendência."""

    if conferencia["completo"]:
        return ""

    if conferencia["vazio"]:
        return (
            "O índice está vazio: nenhum documento do acervo foi indexado. "
            f"Para consultar, {ACAO_INDEXAR}."
        )

    pendencias = conferencia["pendencias"]
    descricoes = "; ".join(
        f"{p['doc_id']} {DESCRICOES_SITUACAO[p['situacao']]}" for p in pendencias
    )
    a_remover = [p["doc_id"] for p in pendencias if p["situacao"] in PENDENCIAS_DE_REMOVER]
    remover = f'"Remover do índice" ao lado de {" e ".join(a_remover)}'

    if not a_remover:
        return f"O índice está incompleto: {descricoes}. Para consultar, {ACAO_INDEXAR}."

    if len(a_remover) == len(pendencias):
        return (
            f"O índice tem documento que não deveria estar nele: {descricoes}. "
            f"Para consultar, vá à tela Acervo e clique em {remover}."
        )

    return (
        f"O índice está incompleto: {descricoes}. "
        f"Para consultar, {ACAO_INDEXAR} e em {remover}."
    )


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