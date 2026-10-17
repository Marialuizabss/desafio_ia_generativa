
from pathlib import Path
from datetime import datetime
from time import perf_counter
import json

from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MODELO = "gpt-4o-transcribe"
IDIOMA = "pt"


def transcrever_audio():
    entrada = BASE_DIR / "dados" / "entrada" / "entrada_audio.mp3"
    pasta_saida = BASE_DIR / "dados" / "saida"

    if not entrada.is_file():
        raise FileNotFoundError(f"Áudio não encontrado: {entrada}")

    pasta_saida.mkdir(parents=True, exist_ok=True)

    inicio = perf_counter()
    data_execucao = datetime.now().astimezone().isoformat()

    try:
        client = OpenAI(timeout=60.0, max_retries=2)

        print("Iniciando transcrição...")

        with entrada.open("rb") as arquivo:
            resultado = client.audio.transcriptions.create(
                model=MODELO,
                file=arquivo,
                language=IDIOMA,
            )

        texto = resultado.text.strip()

        if not texto:
            raise ValueError("A API retornou uma transcrição vazia.")

        duracao = round(perf_counter() - inicio, 2)

        caminho_texto = pasta_saida / "transcricao_rf06.txt"
        caminho_meta = pasta_saida / "metadados_rf06.json"

        caminho_texto.write_text(texto, encoding="utf-8")

        metadados = {
            "requisito": "RF06",
            "arquivo_entrada": entrada.name,
            "modelo": MODELO,
            "idioma": IDIOMA,
            "data_execucao": data_execucao,
            "tempo_execucao_segundos": duracao,
            "status": "sucesso",
            "revisao_humana": "pendente",
            "arquivo_saida": caminho_texto.name,
        }

        caminho_meta.write_text(
            json.dumps(metadados, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

        print(f"Transcrição salva em: {caminho_texto}")
        print(f"Metadados salvos em: {caminho_meta}")
        print(f"Tempo de execução: {duracao} segundos")

    except Exception as erro:
        print(f"Erro na transcrição: {type(erro).__name__}")
        raise


if __name__ == "__main__":
    transcrever_audio()
