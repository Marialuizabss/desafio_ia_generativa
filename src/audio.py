from pathlib import Path
from datetime import datetime
from time import perf_counter
import json
import re

from dotenv import load_dotenv
from openai import BadRequestError, NotFoundError, OpenAI, OpenAIError

try:
    from configuracao import CAMINHOS, CUSTOS, MODELOS, PARAMETROS_GERAIS
except ImportError:
    from src.configuracao import CAMINHOS, CUSTOS, MODELOS, PARAMETROS_GERAIS

try:
    from erros_api import mensagem_de_falha
except ImportError:
    from src.erros_api import mensagem_de_falha

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

MODELO = MODELOS["transcricao"]
IDIOMA = PARAMETROS_GERAIS["idioma"]
TIMEOUT_SEGUNDOS = float(PARAMETROS_GERAIS["timeout_segundos"])

# RF07: voz da minuta aprovada. O tts-1-hd não aceita instruções e só é usado
# se a chave não tiver acesso ao modelo principal.
MODELO_VOZ = MODELOS["voz"]
MODELO_VOZ_ALTERNATIVO = MODELOS["voz_alternativo"]
VOZ = PARAMETROS_GERAIS["voz"]
INSTRUCOES_VOZ = PARAMETROS_GERAIS["instrucoes_voz"]
CUSTO_VOZ_USD_POR_MINUTO = CUSTOS["voz_por_minuto"]
AVISO_NAO_LOCALIZADO = (
    "Atenção: esta minuta contém campos não localizados. "
    "Confira as informações antes de prosseguir."
)
_MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def duracao_do_audio(caminho) -> float | None:
    """Duração em segundos, lida do cabeçalho do arquivo (RF06).

    Não chama a API. Devolve None quando o formato não é reconhecido
    (por exemplo, webm) ou o arquivo não pode ser lido.
    """
    try:
        from mutagen import File as ArquivoDeAudio

        arquivo = ArquivoDeAudio(str(caminho))
        if arquivo is None or arquivo.info is None:
            return None
        return round(float(arquivo.info.length), 2)
    except Exception:
        return None


def transcrever_audio(caminho, destino_texto=None, idioma=None):
    entrada = Path(caminho)
    if not entrada.is_absolute():
        entrada = BASE_DIR / entrada
    pasta_saida = BASE_DIR / CAMINHOS["processados"]
    pasta_logs = BASE_DIR / CAMINHOS["logs"]

    if not entrada.is_file():
        raise FileNotFoundError(f"Áudio não encontrado: {entrada}")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_logs.mkdir(parents=True, exist_ok=True)

    inicio = perf_counter()
    data_execucao = datetime.now().astimezone().isoformat()

    try:
        client = OpenAI(timeout=TIMEOUT_SEGUNDOS, max_retries=2)

        print("Iniciando transcrição...")

        with entrada.open("rb") as arquivo:
            resultado = client.audio.transcriptions.create(
                model=MODELO,
                file=arquivo,
                language=idioma or IDIOMA,
            )

        texto = resultado.text.strip()

        if not texto:
            raise ValueError("A API retornou uma transcrição vazia.")

        duracao = round(perf_counter() - inicio, 2)

        if destino_texto is None:
            caminho_texto = pasta_saida / "transcricao_rf06.txt"
        else:
            caminho_texto = Path(destino_texto)
            if not caminho_texto.is_absolute():
                caminho_texto = BASE_DIR / caminho_texto
            caminho_texto.parent.mkdir(parents=True, exist_ok=True)

        caminho_texto.write_text(texto, encoding="utf-8")

        if destino_texto is None:
            caminho_meta = pasta_logs / "metadados_rf06.json"
            metadados = {
                "requisito": "RF06",
                "arquivo_entrada": entrada.name,
                "modelo": MODELO,
                "idioma": idioma or IDIOMA,
                "duracao_audio_segundos": duracao_do_audio(entrada),
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
            print(f"Metadados salvos em: {caminho_meta}")

        print(f"Transcrição salva em: {caminho_texto}")
        print(f"Tempo de execução: {duracao} segundos")
        return texto

    except OpenAIError as erro:
        print(f"Erro na transcrição: {type(erro).__name__}")
        raise ValueError(mensagem_de_falha(erro, "a transcrição do áudio")) from erro
    except Exception as erro:
        print(f"Erro na transcrição: {type(erro).__name__}")
        raise


def preparar_texto_para_fala(minuta: str) -> str:
    """Ajusta a forma da minuta aprovada para a voz, sem acrescentar conteúdo.

    Tira o marcador do brasão e a formatação, lê o protocolo por partes, escreve
    as datas por extenso e põe o aviso de campos não localizados no início.
    """
    linhas = []
    for linha in (minuta or "").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("[CABEÇALHO COM BRASÃO"):
            linhas.append("")
            continue
        texto = re.sub(r"\*\*(.+?)\*\*", r"\1.", texto)
        texto = re.sub(r"^\*(.+)\*$", r"\1", texto)
        texto = re.sub(r"^-\s+", "", texto)
        texto = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", _data_por_extenso, texto)
        texto = re.sub(r"\b(\d{4})-(\d{6})\b", _protocolo_por_partes, texto)
        texto = texto.replace("Prezado(a)", "Prezado ou prezada").replace("O(a) solicitante", "O solicitante")
        if texto[-1] not in ".,:;!?":
            texto += "."
        linhas.append(texto)
    falado = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    if falado and "não localizado" in falado.casefold():
        falado = f"{AVISO_NAO_LOCALIZADO}\n\n{falado}"
    return falado


def _data_por_extenso(encontrado) -> str:
    dia, mes, ano = int(encontrado.group(1)), int(encontrado.group(2)), encontrado.group(3)
    if not 1 <= mes <= 12:
        return encontrado.group(0)
    return f"{'1º' if dia == 1 else dia} de {_MESES[mes - 1]} de {ano}"


def _protocolo_por_partes(encontrado) -> str:
    return f"{encontrado.group(1)}, traço, {' '.join(encontrado.group(2))}"


def sintetizar_minuta(minuta: str, destino: Path) -> dict:
    """Gera o mp3 da minuta aprovada e guarda ao lado o texto exato enviado à voz."""
    texto = preparar_texto_para_fala(minuta)
    if not texto:
        raise ValueError("A minuta aprovada está vazia.")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto_falado = destino.with_name(f"{destino.stem}_texto_falado.txt")

    inicio = perf_counter()
    try:
        cliente = OpenAI(timeout=TIMEOUT_SEGUNDOS, max_retries=2)
        try:
            _falar(cliente, MODELO_VOZ, texto, destino, INSTRUCOES_VOZ)
            modelo, instrucoes = MODELO_VOZ, INSTRUCOES_VOZ
        except (NotFoundError, BadRequestError):
            # Chave sem acesso ao modelo com instruções: usa o anterior e registra
            _falar(cliente, MODELO_VOZ_ALTERNATIVO, texto, destino, None)
            modelo, instrucoes = MODELO_VOZ_ALTERNATIVO, None
    except OpenAIError as erro:
        raise ValueError(mensagem_de_falha(erro, "a geração da voz")) from erro
    texto_falado.write_text(texto + "\n", encoding="utf-8")

    duracao = duracao_do_audio(destino)
    return {
        "arquivo_audio": destino,
        "arquivo_texto_falado": texto_falado,
        "modelo": modelo,
        "voz": VOZ,
        "instrucoes": instrucoes,
        "instrucoes_aplicadas": instrucoes is not None,
        "duracao_audio_segundos": duracao,
        "tempo_geracao_segundos": round(perf_counter() - inicio, 2),
        "custo_estimado_usd": round(duracao / 60 * CUSTO_VOZ_USD_POR_MINUTO, 6) if duracao else None,
    }


def _falar(cliente, modelo: str, texto: str, destino: Path, instrucoes: str | None) -> None:
    extras = {"instructions": instrucoes} if instrucoes else {}
    with cliente.audio.speech.with_streaming_response.create(
        model=modelo,
        voice=VOZ,
        input=texto,
        response_format="mp3",
        **extras,
    ) as resposta:
        resposta.stream_to_file(destino)


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
    transcrever_audio(BASE_DIR / "dados" / "originais" / "entrada_audio.mp3")