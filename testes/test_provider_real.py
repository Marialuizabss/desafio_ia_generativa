"""Teste real do adaptador RF21."""

import json

from src.provider_adapter import consultar_llm


def main():
    resposta, auditoria = consultar_llm(
        instrucoes=(
            "Você é um assistente administrativo. "
            "Responda em português, de forma objetiva. "
            "Não invente informações."
        ),
        entrada=(
            "Um cidadão pergunta qual é o prazo para apresentar "
            "documentos, mas nenhum prazo foi informado. "
            "Como você deve responder?"
        ),
        nome_configuracao="principal",
    )

    print("\n=== RESPOSTA DO MODELO ===")
    print(resposta)

    print("\n=== AUDITORIA RF21 ===")
    print(json.dumps(auditoria, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
