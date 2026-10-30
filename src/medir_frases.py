import re

from src.avaliacao_rf18 import (
    CONFIGURACOES,
    carregar_perguntas_respondiveis,
    trecho_e_referencia,
)
from src.ingestion import carregar_catalogo, gerar_chunks_documento
from src.vector_store import carregar_modelo_embeddings

modelo = carregar_modelo_embeddings()
tokenizador = modelo.tokenizer
limite = modelo.max_seq_length
documentos = {d["doc_id"]: d for d in carregar_catalogo()["documentos"]}
perguntas = carregar_perguntas_respondiveis()

for nome, parametros in CONFIGURACOES.items():
    print(f"\n== {nome}")

    for pergunta in perguntas:
        for ref in pergunta["referencias"]:
            chunks = gerar_chunks_documento(documentos[ref["doc_id"]], **parametros)

            for c in chunks:
                if not trecho_e_referencia(c["doc_id"], c["pagina"], c["texto"], ref):
                    continue

                limpo = re.sub(r"\s+", " ", c["texto"])
                alvo = re.sub(r"\s+", " ", ref["frase"])
                achado = re.search(re.escape(alvo), limpo, re.IGNORECASE)

                if not achado:
                    continue

                ate_o_fim = len(tokenizador(limpo[: achado.end()])["input_ids"])
                situacao = "dentro" if ate_o_fim <= limite else "FORA do limite"
                print(f"{pergunta['id']}: {c['chunk_id']} — a frase termina no token {ate_o_fim} ({situacao})")