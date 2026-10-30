from src.avaliacao_rf18 import CONFIGURACOES
from src.ingestion import carregar_catalogo, gerar_chunks_documento
from src.vector_store import carregar_modelo_embeddings

modelo = carregar_modelo_embeddings()
tokenizador = modelo.tokenizer
documentos = carregar_catalogo()["documentos"]

for nome, parametros in CONFIGURACOES.items():
    chunks = [
        c for d in documentos for c in gerar_chunks_documento(d, **parametros)
    ]
    tamanhos = [len(tokenizador(c["texto"])["input_ids"]) for c in chunks]
    acima = sum(t > modelo.max_seq_length for t in tamanhos)

    print(
        f"{nome}: {len(chunks)} chunks; "
        f"{acima} acima de {modelo.max_seq_length} tokens "
        f"({acima / len(chunks):.0%}); média {sum(tamanhos) / len(tamanhos):.0f} tokens"
    )