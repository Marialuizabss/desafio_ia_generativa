"""Compara duas configurações do adaptador LLM (RF21)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.provider_adapter import consultar_llm


def main():
    instrucoes = (
        "Você é um assistente administrativo. "
        "Responda em português, de forma objetiva. "
        "Não invente prazos ou informações."
    )

    pergunta = (
        "Um cidadão pergunta qual é o prazo para apresentar "
        "documentos, mas nenhum prazo foi informado. "
        "Como você deve responder?"
    )

    resultados = {
        "rf": "RF21",
        "data_execucao": datetime.now(timezone.utc).isoformat(),
        "pergunta": pergunta,
        "configuracoes": {},
    }

    for nome in ("principal", "alternativa"):
        print(f"\nExecutando configuração: {nome}")

        resposta, auditoria = consultar_llm(
            instrucoes=instrucoes,
            entrada=pergunta,
            nome_configuracao=nome,
        )

        resultados["configuracoes"][nome] = {
            "resposta": resposta,
            "auditoria": auditoria,
        }

        print(f"Resposta: {resposta}")
        print(f"Tokens: {auditoria['tokens_total']}")
        print(f"Tempo: {auditoria['tempo_resposta_segundos']} s")

    destino = Path("resultados/metricas/rf21_comparacao.json")
    destino.parent.mkdir(parents=True, exist_ok=True)

    destino.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nResultados salvos em: {destino}")


if __name__ == "__main__":
    main()
