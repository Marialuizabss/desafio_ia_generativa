
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
    entrada = BASE_DIR / "dados" / "originais" / "entrada_audio.mp3"
    pasta_saida = BASE_DIR / "dados" / "processados"
    pasta_logs = BASE_DIR / "resultados" / "logs"

    if not entrada.is_file():
        raise FileNotFoundError(f"Áudio não encontrado: {entrada}")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_logs.mkdir(parents=True, exist_ok=True)

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
        caminho_meta = pasta_logs / "metadados_rf06.json"

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


def gerar_audio():
    entrada = BASE_DIR / "resultados" / "minutas" / "texto_rf07.txt"
    saida = BASE_DIR / "resultados" / "audios" / "audio_rf07.mp3"

    if not entrada.is_file():
        raise FileNotFoundError(f"Texto não encontrado: {entrada}")

    texto = entrada.read_text(encoding="utf-8").strip()

    if not texto:
        raise ValueError("O texto para síntese de voz está vazio.")

    if "não localizado" in texto.casefold():
        aviso = (
            "Atenção: esta minuta contém campos não localizados. "
            "Confira as informações antes de prosseguir."
        )
        texto = f"{aviso}\n\n{texto}"

    saida.parent.mkdir(parents=True, exist_ok=True)

    print("Iniciando geração de áudio...")

    client = OpenAI(timeout=120.0, max_retries=2)

    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice="nova",
        input=texto,
        response_format="mp3",
    ) as resposta:
        resposta.stream_to_file(saida)

    print(f"Áudio gerado com sucesso: {saida}")


if __name__ == "__main__":
    transcrever_audio()
