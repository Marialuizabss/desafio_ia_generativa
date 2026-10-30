from src.ingestion import carregar_catalogo, gerar_chunks_documento
from src.vector_store import (carregar_modelo_embeddings,obter_colecao,indexar_documento,buscar_chunks,)

import chromadb
from src.vector_store import PASTA_INDICE

CONFIGURACOES = {
    "pequena": {"tamanho": 300, "sobreposicao": 50},
    "media": {"tamanho": 800, "sobreposicao": 100},
    "grande": {"tamanho": 1200, "sobreposicao": 200},
}

PERGUNTAS_AVALIACAO = [
    {
        "pergunta": "Quais faltas podem cancelar a matrícula?",
        "doc_id_esperado": "ACV-08",
        "secao_esperada": "1. Frequência nos primeiros dias de aula",
    },
    {
        "pergunta": "É permitido trancar a matrícula no primeiro semestre?",
        "doc_id_esperado": "ACV-08",
        "secao_esperada": "3. Trancamento de matrícula",
    },
    {
        "pergunta": "A pesquisa socioeconômica é obrigatória?",
        "doc_id_esperado": "ACV-09",
        "secao_esperada": "2. Aplicação da pesquisa",
    },
    {
        "pergunta": "Quais documentos são aceitos para justificar faltas?",
        "doc_id_esperado": "ACV-08",
        "secao_esperada": "2. Justificativa de faltas",
    },
    {
        "pergunta": "Como o estudante deve solicitar o trancamento da matrícula?",
        "doc_id_esperado": "ACV-08",
        "secao_esperada": "3. Trancamento de matrícula",
    },
]

def comparar_quantidade_chunks():
    catalogo = carregar_catalogo()
    documentos = catalogo["documentos"]

    for nome, parametros in CONFIGURACOES.items():
        total_chunks = 0

        for documento in documentos:
            chunks = gerar_chunks_documento(
                documento,
                tamanho=parametros["tamanho"],
                sobreposicao=parametros["sobreposicao"],
            )

            total_chunks += len(chunks)

        print(f"\nConfiguracao: {nome}")
        print(f"Tamanho: {parametros['tamanho']}")
        print(f"Sobreposicao: {parametros['sobreposicao']}")
        print(f"Total de chunks: {total_chunks}")

def calcular_hit(resultados, doc_id_esperado, secao_esperada):
    for resultado in resultados:
        metadados = resultado["metadados"]

        if (
            metadados["doc_id"] == doc_id_esperado
            and metadados["secao"] == secao_esperada
        ):
            return 1

    return 0

def criar_colecao_avaliacao(nome_configuracao):
    pasta_avaliacao = PASTA_INDICE.parent / "indice_avaliacao_rf18"

    cliente = chromadb.PersistentClient(
        path=str(pasta_avaliacao)
    )

    nome_colecao = f"avaliacao_{nome_configuracao}"

    colecao = cliente.get_or_create_collection(
        name=nome_colecao,
        metadata={"hnsw:space": "cosine"},
    )

    return colecao

def preparar_indice_avaliacao(nome, parametros, documentos, modelo):
    colecao = criar_colecao_avaliacao(nome)

    if colecao.count() > 0:
        colecao.delete(ids=colecao.get()["ids"])

    total_chunks = 0

    for documento in documentos:
        chunks = gerar_chunks_documento(
            documento,tamanho=parametros["tamanho"],
            sobreposicao=parametros["sobreposicao"],
        )

        indexar_documento( 
            documento, 
            chunks, 
            modelo,
            colecao,
        )

        total_chunks += len(chunks)

    print(f"{nome}: {total_chunks} chunks indexados")

    return colecao

def avaliar_recuperacao(colecao, modelo, top_k=5):
    acertos = 0

    for item in PERGUNTAS_AVALIACAO:
        resultados = buscar_chunks(
            item["pergunta"],
            modelo,
            colecao,
            top_k=top_k,
        )

        acertou = calcular_hit(
            resultados,
            item["doc_id_esperado"],
            item["secao_esperada"],
        )

        acertos += acertou

        print(f"\nPergunta: {item['pergunta']}")
        print(f"Hit@{top_k}: {acertou}")

    total = len(PERGUNTAS_AVALIACAO)
    taxa = acertos / total if total else 0

    print(f"\nResultado: {acertos}/{total}")
    print(f"Hit@{top_k} médio: {taxa:.2%}")

    return taxa

if __name__ == "__main__":
    catalogo = carregar_catalogo()
    documentos = catalogo["documentos"]

    print("Carregando modelo de embeddings...")
    modelo = carregar_modelo_embeddings()

    resultados = {}

    for nome, parametros in CONFIGURACOES.items():
        print(f"\n{'=' * 50}")
        print(f"CONFIGURACAO: {nome.upper()}")
        print(f"{'=' * 50}")

        colecao = preparar_indice_avaliacao(
            nome,
            parametros,
            documentos,
            modelo,
        )

        resultados[nome] = {}

        for k in [3, 5, 10]:
            print(f"\n--- Avaliacao Hit@{k} ---")

            taxa = avaliar_recuperacao(
                colecao,
                modelo,
                top_k=k,
            )

            resultados[nome][k] = taxa

    print(f"\n{'=' * 50}")
    print("RESUMO FINAL - RF18")
    print(f"{'=' * 50}")

    for nome, metricas in resultados.items():
        print(f"\nConfiguracao: {nome.upper()}")

        for k, taxa in metricas.items():
            print(f"Hit@{k}: {taxa:.2%}")