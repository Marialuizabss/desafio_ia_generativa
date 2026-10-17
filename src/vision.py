
import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def extrair_ficha():
    entrada = BASE_DIR / "dados" / "processados" / "entrada_rf08_pagina1.png"
    saida = BASE_DIR / "dados" / "saida" / "extracao_rf08.json"

    if not entrada.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {entrada}")

    imagem_base64 = base64.b64encode(entrada.read_bytes()).decode("ascii")

    prompt = """
    Analise a imagem de uma ficha de matrícula digitalizada.

    Extraia os seguintes campos:
    codigo, nome, data_nascimento, cpf, rg, naturalidade,
    nome_mae, nome_pai, curso, eixo_tecnologico,
    carga_horaria, turno, email, data_matricula.

    Regras:
    - Use somente informações visíveis na imagem.
    - Não complete dados com informações de outros documentos.
    - Se um campo estiver vazio ou ilegível, retorne null.
    - Preserve os valores como aparecem no documento.
    - Não invente informações.
    - Retorne exclusivamente um objeto JSON válido.
    """

    client = OpenAI(timeout=120.0, max_retries=2)

    print("Iniciando análise da ficha de matrícula...")

    resposta = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{imagem_base64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    conteudo = resposta.choices[0].message.content

    if not conteudo:
        raise ValueError("A API retornou uma resposta vazia.")

    dados = json.loads(conteudo)

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Extração concluída: {saida}")


if __name__ == "__main__":
    extrair_ficha()
